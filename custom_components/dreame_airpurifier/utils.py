from __future__ import annotations

import json
from typing import Any


def parse_key(key: str) -> tuple[int, int]:
    siid, piid = key.split(".", 1)
    return int(siid), int(piid)


def parse_csv_keys(value: str) -> list[str]:
    if not value:
        return []
    keys = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parse_key(item)
        keys.append(item)
    return list(dict.fromkeys(keys))


def safe_json_loads(value: str, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def normalize_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def values_equal(left: Any, right: Any) -> bool:
    return normalize_value(left) == normalize_value(right)


def maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def coerce_option_value(value: str) -> Any:
    if value == "":
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered == "null":
            return None
        return value
