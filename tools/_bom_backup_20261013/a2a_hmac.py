#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A2A message authentication using HMAC-SHA3-512."""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone

VERSION = "a2a-hmac-sha3-512/v1"
DOMAIN_PREFIX = b"OpenPlanLink-A2A-HMAC-v1\x00"
DEFAULT_WINDOW = 300
KEY_BYTES = 64
TAGLESS_FIELDS = frozenset({
    "version",
    "key_id",
    "sender_id",
    "recipient_id",
    "timestamp",
    "nonce",
    "body_sha3_512",
})
FULL_FIELDS = TAGLESS_FIELDS | {"tag"}
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
LOWER_HEX_128 = re.compile(r"^[0-9a-f]{128}$")
NONCE_HEX = re.compile(r"^[0-9a-f]{32,256}$")
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def sha3_512_hex(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("正文必须是原始 bytes")
    return hashlib.sha3_512(data).hexdigest()


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_ts(value: str) -> datetime:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise ValueError("timestamp 必须是带显式时区的 RFC 3339")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp 缺少时区")
    return parsed


def _validate_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) != KEY_BYTES:
        raise ValueError(f"HMAC 密钥必须是 {KEY_BYTES} 字节")


def _validate_identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} 格式非法")


def _validate_tagless_envelope(envelope: dict) -> None:
    if not isinstance(envelope, dict) or set(envelope) != TAGLESS_FIELDS:
        raise ValueError("包络字段集合不匹配")
    if any(not isinstance(value, str) for value in envelope.values()):
        raise ValueError("包络字段必须全部为字符串")
    if envelope["version"] != VERSION:
        raise ValueError("version 不匹配")
    for field in ("key_id", "sender_id", "recipient_id"):
        _validate_identifier(envelope[field], field)
    parse_ts(envelope["timestamp"])
    if not NONCE_HEX.fullmatch(envelope["nonce"]):
        raise ValueError("nonce 必须是至少 128 位的小写十六进制")
    if not LOWER_HEX_128.fullmatch(envelope["body_sha3_512"]):
        raise ValueError("正文摘要格式非法")


def canonicalize_envelope(envelope: dict) -> bytes:
    _validate_tagless_envelope(envelope)
    return json.dumps(
        envelope,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def compute_tag(envelope_without_tag: dict, key: bytes) -> str:
    _validate_key(key)
    authenticated = DOMAIN_PREFIX + canonicalize_envelope(envelope_without_tag)
    return hmac.new(key, authenticated, hashlib.sha3_512).hexdigest()


class ReplayCache:
    def __init__(self, database_path):
        try:
            path = os.fspath(database_path)
        except TypeError as error:
            raise ValueError("nonce 缓存路径非法") from error
        if not isinstance(path, str) or not path or path == ":memory:" or path.startswith("file:"):
            raise ValueError("nonce 缓存必须使用持久 SQLite 文件")
        self._database_path = path
        connection = self._connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS replay_nonces "
                "(nonce TEXT PRIMARY KEY, expires_at REAL NOT NULL)"
            )
        finally:
            connection.close()

    def _connect(self):
        connection = sqlite3.connect(self._database_path, timeout=5, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def claim(self, nonce: str, checked_at: datetime, message_timestamp: datetime) -> bool:
        current = checked_at.timestamp()
        expires_at = message_timestamp.timestamp() + DEFAULT_WINDOW
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM replay_nonces WHERE expires_at < ?", (current,))
            cursor = connection.execute(
                "INSERT OR IGNORE INTO replay_nonces (nonce, expires_at) VALUES (?, ?)",
                (nonce, expires_at),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def build_envelope(
    sender_id: str,
    recipient_id: str,
    body: bytes,
    key: bytes,
    key_id: str,
    *,
    timestamp: str | None = None,
    nonce: str | None = None,
) -> dict:
    _validate_key(key)
    envelope = {
        "version": VERSION,
        "key_id": key_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "timestamp": timestamp or now_rfc3339(),
        "nonce": nonce or secrets.token_hex(16),
        "body_sha3_512": sha3_512_hex(body),
    }
    envelope["tag"] = compute_tag(envelope, key)
    return envelope


def verify_envelope(
    envelope: dict,
    key: bytes,
    key_id: str,
    sender_id: str,
    recipient_id: str,
    body: bytes,
    replay_cache: ReplayCache,
    *,
    now: datetime | None = None,
    window: int = DEFAULT_WINDOW,
):
    """Return ``(ok, reason)`` and reject every malformed or unverifiable input."""
    try:
        _validate_key(key)
        if not isinstance(body, bytes):
            raise ValueError("正文必须是原始 bytes")
        if not isinstance(envelope, dict) or set(envelope) != FULL_FIELDS:
            return False, "包络字段集合不匹配"
        if not isinstance(replay_cache, ReplayCache):
            return False, "nonce 缓存缺失"
        if window != DEFAULT_WINDOW or isinstance(window, bool):
            return False, "时间窗必须固定为 300 秒"
        if envelope.get("version") != VERSION:
            return False, "version 不匹配"
        if envelope.get("sender_id") != sender_id:
            return False, "发送方错配"
        if envelope.get("recipient_id") != recipient_id:
            return False, "接收方错配"
        if envelope.get("key_id") != key_id:
            return False, "错误 key_id"

        tagless = {field: envelope[field] for field in TAGLESS_FIELDS}
        _validate_tagless_envelope(tagless)
        tag = envelope["tag"]
        if not isinstance(tag, str) or not LOWER_HEX_128.fullmatch(tag):
            return False, "tag 格式非法"

        checked_at = now or datetime.now(timezone.utc)
        if checked_at.tzinfo is None or checked_at.utcoffset() is None:
            return False, "当前时间缺少时区"
        timestamp = parse_ts(envelope["timestamp"])
        if abs((checked_at - timestamp).total_seconds()) > window:
            return False, "时间窗超界"

        body_digest = sha3_512_hex(body)
        if not hmac.compare_digest(envelope["body_sha3_512"], body_digest):
            return False, "正文摘要不匹配"
        expected = compute_tag(tagless, key)
        if not hmac.compare_digest(expected, tag):
            return False, "tag 不匹配"
        try:
            claimed = replay_cache.claim(envelope["nonce"], checked_at, timestamp)
        except sqlite3.Error:
            return False, "nonce 缓存不可用"
        if not claimed:
            return False, "重复 nonce"
        return True, "ok"
    except (KeyError, TypeError, ValueError, OverflowError):
        return False, "包络格式非法"


def platform_supported() -> bool:
    try:
        return len(hashlib.sha3_512(b"x").digest()) == 64
    except Exception:
        return False
