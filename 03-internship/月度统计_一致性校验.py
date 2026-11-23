"""月度统计公开审阅稿。比较两份口径相同的 JSONL 汇总。

保留原脚本的行主键对齐、字段集合检查、逐字段比较和浮点容差。
默认主键对应流式分块脚本的输出，也可用 --key-column 指定本地字段。
"""

import argparse
import json
import math
from pathlib import Path


def load(path, key_columns):
    rows = {}
    with Path(path).open(encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if any(field not in row or row[field] is None for field in key_columns):
                raise ValueError(f"第 {line_number} 行缺少主键字段。")
            key = tuple(str(row[field]) for field in key_columns)
            if key in rows:
                raise ValueError(f"第 {line_number} 行出现重复主键。")
            rows[key] = row
    return rows


def close(a, b, tol):
    if isinstance(a, dict) and isinstance(b, dict):
        if a.get("type") != b.get("type"):
            return False
        a, b = a.get("value"), b.get("value")
    if (
        type(a) in (int, float) and type(b) in (int, float)
        and (isinstance(a, float) or isinstance(b, float))
    ):
        return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
    return a == b


def compare(reference, candidate, tolerance):
    missing_keys = sorted(reference.keys() - candidate.keys())
    extra_keys = sorted(candidate.keys() - reference.keys())
    field_issues = []
    for key in sorted(reference.keys() & candidate.keys()):
        a, b = reference[key], candidate[key]
        different = sorted(
            field for field in a.keys() & b.keys()
            if not close(a[field], b[field], tolerance)
        )
        missing = sorted(a.keys() - b.keys())
        extra = sorted(b.keys() - a.keys())
        if different or missing or extra:
            field_issues.append({
                "key": key,
                "missing_fields": missing,
                "extra_fields": extra,
                "different_fields": different,
            })
    return {
        "reference_rows": len(reference),
        "candidate_rows": len(candidate),
        "equal": not (missing_keys or extra_keys or field_issues),
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "field_issues": field_issues,
    }


def main():
    parser = argparse.ArgumentParser(description="对两份汇总逐行按主键、逐字段核对。")
    parser.add_argument("reference", type=Path, help="运行者提供的基准汇总 JSONL，替换 xxxx")
    parser.add_argument("candidate", type=Path, help="运行者提供的待校验汇总 JSONL，替换 xxxx")
    parser.add_argument("--key-column", action="append", help="主键列，可重复")
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    if any(path.name == "xxxx" or not path.is_file() for path in (args.reference, args.candidate)):
        parser.error("请将 xxxx 替换为已获准使用的两个本地汇总 JSONL 路径。")
    if args.key_column and any(name.strip() in ("", "xxxx") for name in args.key_column):
        parser.error("请将 xxxx 替换为输入文件中的主键列名。")
    if args.tolerance < 0 or not math.isfinite(args.tolerance):
        parser.error("容差应为有限非负数。")
    keys = args.key_column or ["stat_date", "province", "city", "group"]
    result = compare(load(args.reference, keys), load(args.candidate, keys), args.tolerance)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

