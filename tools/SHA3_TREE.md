# SHA3-512 Merkle 树与 HMAC 根认证

## 运行要求

- Node.js 20+，仅使用内置模块
- Git，用于取得已跟踪文件集合
- 64 字节随机 HMAC 密钥，以规范 Base64 注入 `OPL_A2A_HMAC_KEY_B64`
- 非秘密轮换标识，以 `OPL_A2A_HMAC_KEY_ID` 注入

## 使用

```bash
node tools/sha3-tree.mjs build
node tools/sha3-tree.mjs verify
node tools/sha3-tree.test.mjs
```

命令必须从 Git 仓库根目录运行。默认清单为 `attest-hmac-sha3-512.json`；该清单自身不进入树，其他 Git 已跟踪文件按 UTF-8 路径字节序排列。

## 字节契约

- 内容摘要：`SHA3-512(file_bytes)`
- 叶节点：`SHA3-512(0x00 || uint32be(path_len) || path_utf8 || uint64be(size) || content_digest)`
- 父节点：`SHA3-512(0x01 || left_digest || right_digest)`；奇数节点复制右项
- 根认证：`HMAC-SHA3-512(key, UTF8("OpenPlanLink-A2A-Merkle-v1\\0") || root_digest || uint64be(file_count) || uint16be(key_id_len) || key_id_utf8 || uint16be(generated_at_len) || generated_at_utf8)`
- 输入来源：直接读取 Git 暂存区 blob，不读取工作树文件，避免换行转换、路径竞态及暂存区偏差

密钥不得写入仓库、日志或命令行。不同信任域使用不同密钥；跨应用或厂商核验通过受控环境变量或 KMS 注入同一信任域密钥。算法不可用、密钥缺失、路径或 Git 索引不安全、摘要不一致时均 fail closed，禁止降级。
