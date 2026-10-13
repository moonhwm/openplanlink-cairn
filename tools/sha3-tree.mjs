#!/usr/bin/env node
import {
  closeSync,
  lstatSync,
  openSync,
  realpathSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { createHash, createHmac, randomUUID, timingSafeEqual } from "node:crypto";
import { execFileSync } from "node:child_process";
import { basename, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { TextDecoder } from "node:util";

const SCHEMA = "opl-hmac-sha3-512-tree/1";
const TREE_ALGORITHM = "sha3-512";
const MAC_ALGORITHM = "hmac-sha3-512";
const LEAF_ENCODING = "0x00 || uint32be(path_utf8_len) || path_utf8 || uint64be(size) || sha3_512(content)";
const NODE_ENCODING = "0x01 || left_digest || right_digest; duplicate odd right node";
const MAC_ENCODING = "UTF8(OpenPlanLink-A2A-Merkle-v1\\0) || root_digest || uint64be(file_count) || uint16be(key_id_utf8_len) || key_id_utf8 || uint16be(generated_at_utf8_len) || generated_at_utf8";
const DOMAIN = Buffer.from("OpenPlanLink-A2A-Merkle-v1\0", "utf8");
const OUTPUT_DEFAULT = "attest-hmac-sha3-512.json";
const HEX_512 = /^[0-9a-f]{128}$/;
const KEY_ID = /^[A-Za-z0-9._-]{1,64}$/;
const UTF8 = new TextDecoder("utf-8", { fatal: true });

function sha3(data) {
  return createHash("sha3-512").update(data).digest();
}

function uint16(value) {
  const out = Buffer.alloc(2);
  out.writeUInt16BE(value);
  return out;
}

function uint32(value) {
  const out = Buffer.alloc(4);
  out.writeUInt32BE(value);
  return out;
}

function uint64(value) {
  const out = Buffer.alloc(8);
  out.writeBigUInt64BE(BigInt(value));
  return out;
}

function normalizePath(filePath) {
  if (typeof filePath !== "string" || !filePath || filePath.startsWith("/") || filePath.includes("\0")) {
    throw new Error(`unsafe path: ${filePath}`);
  }
  const segments = filePath.split("/");
  if (segments.some((segment) => !segment || segment === "." || segment === "..")) {
    throw new Error(`unsafe path: ${filePath}`);
  }
  return filePath;
}

function comparePaths(left, right) {
  return Buffer.compare(Buffer.from(left, "utf8"), Buffer.from(right, "utf8"));
}

function leafFor(filePath, bytes) {
  const normalized = normalizePath(filePath);
  const pathBytes = Buffer.from(normalized, "utf8");
  const content = Buffer.from(bytes);
  const contentHash = sha3(content);
  const leafHash = sha3(Buffer.concat([
    Buffer.from([0]),
    uint32(pathBytes.length),
    pathBytes,
    uint64(content.length),
    contentHash,
  ]));
  return {
    path: normalized,
    size: content.length,
    content_sha3_512: contentHash.toString("hex"),
    leaf_sha3_512: leafHash.toString("hex"),
  };
}

function merkleRoot(entries) {
  if (entries.length === 0) throw new Error("cannot build an empty tree");
  let level = entries.map((entry) => Buffer.from(entry.leaf_sha3_512, "hex"));
  while (level.length > 1) {
    const next = [];
    for (let index = 0; index < level.length; index += 2) {
      const left = level[index];
      const right = level[index + 1] ?? left;
      next.push(sha3(Buffer.concat([Buffer.from([1]), left, right])));
    }
    level = next;
  }
  return level[0].toString("hex");
}

function authenticationInput(rootHash, fileCount, keyId, generatedAt) {
  const keyIdBytes = Buffer.from(keyId, "utf8");
  const generatedAtBytes = Buffer.from(generatedAt, "utf8");
  if (keyIdBytes.length > 0xffff || generatedAtBytes.length > 0xffff) {
    throw new Error("authenticated metadata is too long");
  }
  return Buffer.concat([
    DOMAIN,
    Buffer.from(rootHash, "hex"),
    uint64(fileCount),
    uint16(keyIdBytes.length),
    keyIdBytes,
    uint16(generatedAtBytes.length),
    generatedAtBytes,
  ]);
}

export function decodeKey(encoded) {
  if (typeof encoded !== "string" || encoded.length === 0) {
    throw new Error("OPL_A2A_HMAC_KEY_B64 is required");
  }
  const compact = encoded.trim();
  const key = Buffer.from(compact, "base64");
  if (key.toString("base64") !== compact || key.length !== 64) {
    throw new Error("OPL_A2A_HMAC_KEY_B64 must be canonical base64 for exactly 64 bytes");
  }
  return key;
}

function validateKeyId(keyId) {
  if (!KEY_ID.test(keyId ?? "")) throw new Error("OPL_A2A_HMAC_KEY_ID is required");
}

function validateGeneratedAt(generatedAt) {
  if (typeof generatedAt !== "string" || new Date(generatedAt).toISOString() !== generatedAt) {
    throw new Error("generated_at must be canonical UTC ISO-8601");
  }
}

export function buildManifest(fileInputs, key, keyId, generatedAt = new Date().toISOString()) {
  validateKeyId(keyId);
  validateGeneratedAt(generatedAt);
  if (!Buffer.isBuffer(key) || key.length !== 64) throw new Error("HMAC key must be 64 bytes");

  const sorted = fileInputs
    .map(({ path, bytes }) => ({ path: normalizePath(path), bytes: Buffer.from(bytes) }))
    .sort((left, right) => comparePaths(left.path, right.path));
  if (new Set(sorted.map(({ path }) => path)).size !== sorted.length) {
    throw new Error("duplicate file path");
  }

  const files = sorted.map(({ path, bytes }) => leafFor(path, bytes));
  const rootHash = merkleRoot(files);
  const tag = createHmac("sha3-512", key)
    .update(authenticationInput(rootHash, files.length, keyId, generatedAt))
    .digest("hex");

  return {
    schema: SCHEMA,
    generated_at: generatedAt,
    tree_algorithm: TREE_ALGORITHM,
    mac_algorithm: MAC_ALGORITHM,
    leaf_encoding: LEAF_ENCODING,
    node_encoding: NODE_ENCODING,
    mac_encoding: MAC_ENCODING,
    key_id: keyId,
    file_count: files.length,
    merkle_root_sha3_512: rootHash,
    hmac_sha3_512: tag,
    files,
  };
}

function validateManifest(manifest, expectedKeyId) {
  if (manifest?.schema !== SCHEMA) throw new Error("schema mismatch");
  if (manifest.tree_algorithm !== TREE_ALGORITHM || manifest.mac_algorithm !== MAC_ALGORITHM) {
    throw new Error("algorithm mismatch");
  }
  if (manifest.leaf_encoding !== LEAF_ENCODING
    || manifest.node_encoding !== NODE_ENCODING
    || manifest.mac_encoding !== MAC_ENCODING) {
    throw new Error("encoding contract mismatch");
  }
  validateKeyId(manifest.key_id);
  if (manifest.key_id !== expectedKeyId) throw new Error("key_id mismatch");
  validateGeneratedAt(manifest.generated_at);
  if (!Number.isSafeInteger(manifest.file_count) || manifest.file_count < 1) {
    throw new Error("invalid file_count");
  }
  if (!HEX_512.test(manifest.merkle_root_sha3_512) || !HEX_512.test(manifest.hmac_sha3_512)) {
    throw new Error("invalid digest encoding");
  }
  if (!Array.isArray(manifest.files) || manifest.files.length !== manifest.file_count) {
    throw new Error("file list mismatch");
  }
}

export function verifyManifest(manifest, fileInputs, key, expectedKeyId) {
  validateManifest(manifest, expectedKeyId);
  const actual = buildManifest(fileInputs, key, expectedKeyId, manifest.generated_at);
  const expectedTag = Buffer.from(manifest.hmac_sha3_512, "hex");
  const actualTag = Buffer.from(actual.hmac_sha3_512, "hex");
  const valid = actual.merkle_root_sha3_512 === manifest.merkle_root_sha3_512
    && actual.file_count === manifest.file_count
    && JSON.stringify(actual.files) === JSON.stringify(manifest.files)
    && timingSafeEqual(expectedTag, actualTag);
  if (!valid) throw new Error("tree or HMAC verification failed");
  return true;
}

function gitEnvironment() {
  const environment = { ...process.env };
  for (const name of Object.keys(environment)) {
    const normalized = name.toUpperCase();
    if (normalized === "OPL_A2A_HMAC_KEY_B64" || normalized === "OPL_A2A_HMAC_KEY_DPAPI_B64") {
      delete environment[name];
    }
  }
  return environment;
}

function runGit(root, args, options = {}) {
  return execFileSync("git", ["-C", root, ...args], {
    encoding: "buffer",
    env: gitEnvironment(),
    maxBuffer: 512 * 1024 * 1024,
    stdio: ["pipe", "pipe", "inherit"],
    ...options,
  });
}

function repositoryRoot(cwd) {
  const raw = UTF8.decode(runGit(cwd, ["rev-parse", "--show-toplevel"]));
  const root = raw.replace(/\r?\n$/, "");
  if (!root || /[\r\n]/.test(root)) throw new Error("invalid Git repository root");
  return realpathSync.native(root);
}

function samePath(left, right) {
  return process.platform === "win32"
    ? left.toLowerCase() === right.toLowerCase()
    : left === right;
}

function indexRecords(root) {
  const raw = runGit(root, ["ls-files", "--stage", "-z", "--cached"]);
  const records = [];
  for (const record of raw.subarray(0, raw.length - (raw.at(-1) === 0 ? 1 : 0)).toString("binary").split("\0")) {
    const bytes = Buffer.from(record, "binary");
    const tab = bytes.indexOf(9);
    if (tab < 0) throw new Error("invalid git index record");
    const [mode, objectId, stage] = bytes.subarray(0, tab).toString("ascii").split(" ");
    const pathBytes = bytes.subarray(tab + 1);
    let filePath;
    try {
      filePath = UTF8.decode(pathBytes);
    } catch {
      throw new Error("non-UTF-8 git paths are not supported");
    }
    if (!Buffer.from(filePath, "utf8").equals(pathBytes)) {
      throw new Error("git path is not canonical UTF-8");
    }
    normalizePath(filePath);
    if (stage !== "0") throw new Error(`unmerged index entry: ${filePath}`);
    if (mode !== "100644" && mode !== "100755") {
      throw new Error(`unsupported git mode ${mode}: ${filePath}`);
    }
    records.push({ path: filePath, objectId });
  }
  return records.sort((left, right) => comparePaths(left.path, right.path));
}

function readIndexBlobs(root, records) {
  const input = Buffer.from(`${records.map(({ objectId }) => objectId).join("\n")}\n`, "ascii");
  const output = runGit(root, ["cat-file", "--batch"], { input });
  let offset = 0;
  return records.map((record) => {
    const newline = output.indexOf(10, offset);
    if (newline < 0) throw new Error("truncated git cat-file header");
    const [objectId, type, sizeText] = output.subarray(offset, newline).toString("ascii").split(" ");
    const size = Number(sizeText);
    if (objectId !== record.objectId || type !== "blob" || !Number.isSafeInteger(size) || size < 0) {
      throw new Error(`invalid git blob response: ${record.path}`);
    }
    const start = newline + 1;
    const end = start + size;
    if (end >= output.length || output[end] !== 10) throw new Error(`truncated git blob: ${record.path}`);
    offset = end + 1;
    return { path: record.path, bytes: output.subarray(start, end) };
  });
}

function validateOutputIndexPath(records, outputName) {
  if (process.platform !== "win32") return;
  const conflict = records.find(({ path }) => (
    path.toLowerCase() === outputName.toLowerCase() && path !== outputName
  ));
  if (conflict) throw new Error(`manifest path case conflict: ${conflict.path}`);
}

function stagedFiles(root, records, outputName) {
  return readIndexBlobs(root, records.filter(({ path }) => path !== outputName));
}

function stagedManifest(root, records, outputName) {
  const record = records.find(({ path }) => path === outputName);
  if (!record) throw new Error(`manifest is not staged: ${outputName}`);
  const [{ bytes }] = readIndexBlobs(root, [record]);
  return JSON.parse(UTF8.decode(bytes));
}

function resolveOutput(root, argument) {
  const outputName = argument ?? OUTPUT_DEFAULT;
  if (basename(outputName) !== outputName || outputName === "." || outputName === "..") {
    throw new Error("manifest must be a file in the repository root");
  }
  const output = resolve(root, outputName);
  try {
    if (lstatSync(output).isSymbolicLink()) throw new Error("manifest must not be a symbolic link");
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
  return { output, outputName };
}

function writeManifest(outputPath, manifest) {
  const temporary = `${outputPath}.tmp-${randomUUID()}`;
  let descriptor;
  try {
    descriptor = openSync(temporary, "wx", 0o600);
    writeFileSync(descriptor, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    closeSync(descriptor);
    descriptor = undefined;
    renameSync(temporary, outputPath);
  } catch (error) {
    if (descriptor !== undefined) closeSync(descriptor);
    try {
      unlinkSync(temporary);
    } catch (cleanupError) {
      if (cleanupError?.code !== "ENOENT") throw cleanupError;
    }
    throw error;
  }
}

function usage() {
  console.error("usage: node tools/sha3-tree.mjs <build|verify> [root-manifest-name]");
}

function main() {
  const [command, manifestArgument] = process.argv.slice(2);
  if (command !== "build" && command !== "verify") {
    usage();
    process.exitCode = 2;
    return;
  }

  const cwd = realpathSync.native(process.cwd());
  const root = repositoryRoot(cwd);
  if (!samePath(cwd, root)) throw new Error("run from the Git repository root");
  const { output, outputName } = resolveOutput(root, manifestArgument);
  const key = decodeKey(process.env.OPL_A2A_HMAC_KEY_B64);
  const keyId = process.env.OPL_A2A_HMAC_KEY_ID;
  validateKeyId(keyId);
  const records = indexRecords(root);
  validateOutputIndexPath(records, outputName);
  const files = stagedFiles(root, records, outputName);

  if (command === "build") {
    const manifest = buildManifest(files, key, keyId);
    writeManifest(output, manifest);
    console.log(`built ${outputName} (${manifest.file_count} files)`);
    console.log(`merkle_root_sha3_512=${manifest.merkle_root_sha3_512}`);
    return;
  }

  const manifest = stagedManifest(root, records, outputName);
  verifyManifest(manifest, files, key, keyId);
  console.log(`verified ${outputName} (${manifest.file_count} files)`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    main();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
