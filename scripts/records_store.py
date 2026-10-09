#!/usr/bin/env python3
"""Validate and atomically update daily-records/data/records.json."""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODULES = {"thought", "sport", "book", "house"}
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})?$")
DATA_URI_RE = re.compile(r"^data:image/(jpeg|jpg);base64,([A-Za-z0-9+/=\s]+)$", re.I)


def signature(record: dict[str, Any]) -> tuple[Any, ...]:
    module = record.get("module")
    if module == "thought":
        return (module, record.get("time"), record.get("content"))
    if module == "sport":
        return (
            module,
            record.get("time"),
            record.get("sport"),
            json.dumps(record.get("parts", []), ensure_ascii=False, sort_keys=True),
            json.dumps(record.get("exercises", []), ensure_ascii=False, sort_keys=True),
            record.get("distance"),
            record.get("distUnit"),
            str(record.get("duration", "")),
            record.get("note", ""),
        )
    if module == "book":
        return (module, record.get("time"), record.get("book"), record.get("fromPage"), record.get("toPage"))
    if module == "house":
        return (module, record.get("community"), record.get("area"), record.get("totalPrice"), record.get("unitPrice"))
    return (module, record.get("id"))


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("顶层必须是 JSON 对象")

    errors: list[str] = []
    if payload.get("app") != "daily-records":
        errors.append("顶层 app 必须是 daily-records")
    if payload.get("source") != "github":
        errors.append("顶层 source 必须是 github")
    if not isinstance(payload.get("version"), int) or payload.get("version", 0) < 2:
        errors.append("顶层 version 必须是大于等于 2 的整数")
    exported_at = payload.get("exportedAt")
    if not isinstance(exported_at, str) or not exported_at.strip():
        errors.append("顶层 exportedAt 缺失")
    else:
        try:
            datetime.fromisoformat(exported_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("顶层 exportedAt 不是合法 ISO 时间")

    records = payload.get("records")
    if not isinstance(records, list):
        errors.append("顶层 records 必须是数组")
        records = []

    ids: set[str] = set()
    signatures: dict[tuple[Any, ...], str] = {}
    modules: Counter[str] = Counter()
    image_count = 0

    for index, record in enumerate(records):
        label = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label}: 必须是对象")
            continue

        record_id = record.get("id")
        module = record.get("module")
        record_time = record.get("time", "")

        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"{label}: id 缺失")
        elif record_id in ids:
            errors.append(f"{label}: id 重复 {record_id}")
        else:
            ids.add(record_id)

        if module not in MODULES:
            errors.append(f"{label}: module 非法 {module!r}")
            continue
        modules[module] += 1

        time_valid = isinstance(record_time, str) and bool(TIME_RE.fullmatch(record_time))
        if module != "house" and not time_valid:
            errors.append(f"{label}: time 格式非法 {record_time!r}")
        elif module == "house" and record_time and not time_valid:
            errors.append(f"{label}: time 格式非法 {record_time!r}")
        if record_time and time_valid:
            try:
                datetime.strptime(record_time[:10], "%Y-%m-%d")
            except ValueError:
                errors.append(f"{label}: 日期不存在 {record_time!r}")

        if module == "thought" and not str(record.get("content", "")).strip():
            errors.append(f"{label}: thought.content 为空")
        elif module == "sport":
            if not str(record.get("sport", "")).strip():
                errors.append(f"{label}: sport.sport 为空")
            if record.get("sport") == "健身" and not isinstance(record.get("exercises", []), list):
                errors.append(f"{label}: sport.exercises 必须是数组")
        elif module == "book" and not str(record.get("book", "")).strip():
            errors.append(f"{label}: book.book 为空")
        elif module == "house":
            if not str(record.get("community", "")).strip():
                errors.append(f"{label}: house.community 为空")
            images = record.get("images", [])
            if not isinstance(images, list):
                errors.append(f"{label}: house.images 必须是数组")
            else:
                for image_index, image in enumerate(images):
                    image_label = f"{label}.images[{image_index}]"
                    if not isinstance(image, dict) or not isinstance(image.get("src"), str):
                        errors.append(f"{image_label}: 必须是含 src 的对象")
                        continue
                    match = DATA_URI_RE.fullmatch(image["src"])
                    if not match:
                        errors.append(f"{image_label}: src 不是合法图片 data URI")
                        continue
                    try:
                        base64.b64decode(match.group(2), validate=True)
                    except Exception:
                        errors.append(f"{image_label}: base64 无法解码")
                        continue
                    image_count += 1

        sig = signature(record)
        if sig in signatures:
            errors.append(f"{label}: 与 {signatures[sig]} 内容签名重复")
        elif record_id:
            signatures[sig] = record_id

    if errors:
        preview = "\n".join(f"- {item}" for item in errors[:30])
        suffix = f"\n- 另有 {len(errors) - 30} 项" if len(errors) > 30 else ""
        raise ValueError(f"校验失败，共 {len(errors)} 项：\n{preview}{suffix}")

    return {
        "records": len(records),
        "modules": dict(sorted(modules.items())),
        "uniqueIds": len(ids),
        "images": image_count,
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
        temp_path = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def read_record(path_arg: str) -> dict[str, Any]:
    if path_arg == "-":
        record = json.load(sys.stdin)
    else:
        record = load_json(Path(path_arg))
    if not isinstance(record, dict):
        raise ValueError("待写入记录必须是 JSON 对象")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="data/records.json", help="records.json 路径")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="只校验，不改文件")
    upsert_parser = subparsers.add_parser("upsert", help="按 id 新增或更新一条记录")
    upsert_parser.add_argument("record", help="记录 JSON 文件；- 表示从 stdin 读取")
    delete_parser = subparsers.add_parser("delete", help="按 id 删除一条记录")
    delete_parser.add_argument("id")
    args = parser.parse_args()

    data_path = Path(args.file).resolve()
    lock_id = hashlib.sha256(str(data_path).encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"daily-records-{lock_id}.lock"

    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        payload = load_json(data_path)
        before = len(payload.get("records", [])) if isinstance(payload.get("records"), list) else 0
        action = "validate"

        if args.command == "upsert":
            record = read_record(args.record)
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id.strip():
                raise ValueError("upsert 记录必须有非空 id")
            records = payload.get("records")
            if not isinstance(records, list):
                raise ValueError("records.json 缺少 records 数组")
            index = next((i for i, item in enumerate(records) if isinstance(item, dict) and item.get("id") == record_id), None)
            if index is None:
                records.append(record)
                action = "insert"
            else:
                records[index] = record
                action = "update"
            payload["exportedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        elif args.command == "delete":
            records = payload.get("records")
            if not isinstance(records, list):
                raise ValueError("records.json 缺少 records 数组")
            kept = [item for item in records if not (isinstance(item, dict) and item.get("id") == args.id)]
            if len(kept) == len(records):
                raise ValueError(f"未找到 id={args.id}")
            payload["records"] = kept
            payload["exportedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            action = "delete"

        summary = validate_payload(payload)
        if args.command != "validate":
            atomic_write(data_path, payload)

    print(json.dumps({"ok": True, "action": action, "before": before, "after": summary["records"], **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
