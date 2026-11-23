"""月度统计公开审阅稿。原脚本采用逐行扫描、分组缓冲、块内聚合和跨块累加。

输入为已映射到公开字段的 JSONL。每条记录提供 stat_date、province、city、
record_id、groups（命中的类别列表）及待汇总的数值字段。输出为每组一行 JSONL。
类别归属和内部字段由输入方准备，交付模版的补齐与排版留在原项目。
"""

import argparse
import json
from pathlib import Path

import pandas as pd


KEYS = ["stat_date", "province", "city"]
RESERVED = {*KEYS, "record_id", "groups", "group", "record_count"}


def _to_num(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return 0.0 if pd.isna(value) else float(value)
    try:
        number = float(str(value).strip())
        return 0.0 if pd.isna(number) else number
    except ValueError:
        return 0.0


def _agg_chunk(rows, metrics):
    grouped = pd.DataFrame(rows).groupby(KEYS)
    sums = grouped[list(metrics)].sum()
    counts = grouped["record_id"].count().rename("record_count")
    return sums, counts


def _reduce_chunk(acc, part):
    if acc is None:
        return part
    return (
        acc[0].add(part[0], fill_value=0),
        acc[1].add(part[1], fill_value=0),
    )


def scan_files_chunked(file_paths, groups, metrics, chunk_size=100_000):
    """单次扫描每个文件，分别维护各类别缓冲区及中间聚合结果。"""
    groups = tuple(groups)
    metrics = tuple(metrics)
    if chunk_size < 1:
        raise ValueError("块大小至少为 1。")
    if not groups or len(set(groups)) != len(groups):
        raise ValueError("至少需要一个类别，类别名称不能重复。")
    if not metrics or len(set(metrics)) != len(metrics) or RESERVED.intersection(metrics):
        raise ValueError("请指定互不重复、且不与保留字段重名的数值指标。")
    buffers = {group: [] for group in groups}
    totals = dict.fromkeys(groups)

    def flush(group):
        if buffers[group]:
            totals[group] = _reduce_chunk(
                totals[group], _agg_chunk(buffers[group], metrics)
            )
            buffers[group].clear()

    for path in file_paths:
        with Path(path).open(encoding="utf-8-sig") as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                memberships = record.get("groups")
                if not isinstance(memberships, list):
                    raise ValueError(f"第 {line_number} 行缺少 groups 列表。")
                hits = [group for group in groups if group in memberships]
                if not hits:
                    continue
                if any(record.get(key) is None for key in KEYS):
                    raise ValueError(f"第 {line_number} 行缺少统计日期、省份或城市。")
                row = {key: record[key] for key in KEYS}
                row["stat_date"] = str(row["stat_date"])
                row["record_id"] = record.get("record_id")
                row.update((field, _to_num(record.get(field))) for field in metrics)
                for group in hits:
                    buffers[group].append(row)
                    if len(buffers[group]) >= chunk_size:
                        flush(group)

    for group in groups:
        flush(group)
    return totals


def records_for_export(totals):
    for group, total in totals.items():
        if total is None:
            continue
        sums, counts = total
        for row in sums.join(counts).sort_index().reset_index().to_dict("records"):
            row["group"] = group
            row["record_count"] = int(row["record_count"])
            yield row


def main():
    parser = argparse.ArgumentParser(description="流式生成分日期、地区和类别的统计汇总。")
    parser.add_argument("inputs", nargs="+", type=Path, help="运行者提供的 JSONL 路径，替换 xxxx")
    parser.add_argument("--group", action="append", required=True, help="运行者提供的汇总类别，可重复")
    parser.add_argument("--metric", action="append", required=True, help="运行者提供的求和字段名，可重复")
    parser.add_argument("--chunk-size", type=int, default=100_000)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if any(path.name == "xxxx" or not path.is_file() for path in args.inputs):
        parser.error("请将 xxxx 替换为已获准使用的本地明细 JSONL 路径。")
    if any(value.strip() in ("", "xxxx") for value in args.group + args.metric):
        parser.error("请将 xxxx 替换为输入文件中的类别和指标字段名。")
    if args.output.resolve() in {path.resolve() for path in args.inputs}:
        parser.error("输出路径需与输入文件不同。")
    totals = scan_files_chunked(args.inputs, args.group, args.metric, args.chunk_size)
    with args.output.open("w", encoding="utf-8") as target:
        for row in records_for_export(totals):
            target.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()

