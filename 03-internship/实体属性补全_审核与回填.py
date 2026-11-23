"""从待补 Excel 和已有的结构化抽取结果离线生成审核表及回填表。

提取结果为 JSON 数组，采用公开字段约定。运行者提供待补表、阶段一结果和列名。
保留原流程的分级、审核排序、证据保留和仅回填空值逻辑。
"""

import argparse
import json
from pathlib import Path

import pandas as pd


CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low_with_data": 2, "low": 3}
AUDIT_COLUMNS = [
    "entity", "context", "attribute_a", "attribute_b", "evidence_quote",
    "stage", "confidence",
]
FILLABLE_CONFIDENCE = {"high", "medium", "low_with_data"}


def is_empty(value):
    if value is None or pd.isna(value):
        return True
    text = str(value).strip()
    return text.lower() in ("", "nan", "none", "null", "-", "无")


def assess_confidence(record, name_markers, minimum_name_length):
    attribute_a = record.get("attribute_a") or ""
    attribute_b = record.get("attribute_b") or ""

    def is_complete(name):
        return (
            len(name) >= minimum_name_length
            and any(marker in name for marker in name_markers)
        )

    attribute_a_complete = is_complete(attribute_a)
    attribute_b_complete = is_complete(attribute_b)
    if attribute_a_complete and attribute_b_complete:
        return "high"
    if attribute_a_complete or attribute_b_complete:
        return "medium"
    if attribute_a or attribute_b:
        return "low_with_data"
    return "low"


def load_results(records, name_markers=(), minimum_name_length=None):
    results = {}
    for record in records:
        name = str(record["entity"]).strip()
        if not name or name in results:
            raise ValueError("阶段一结果的 entity 必须非空且唯一。")
        item = {field: record.get(field) for field in AUDIT_COLUMNS}
        item["entity"] = name
        if minimum_name_length is not None:
            item["confidence"] = assess_confidence(item, name_markers, minimum_name_length)
        if item["confidence"] not in CONFIDENCE_ORDER:
            raise ValueError("请提供已记录的置信等级，或同时指定名称判断标记与长度。")
        results[name] = item
    return results


def review_and_fill(source, results, entity_column, attribute_a_column, attribute_b_column):
    """通过实体标识关联抽取结果，按置信度排序审核表，保留原表非空值。"""
    required = [entity_column, attribute_a_column, attribute_b_column]
    if any(column not in source.columns for column in required):
        raise ValueError("待补表缺少指定的实体标识列或属性列。")

    audit = pd.DataFrame(list(results.values()), columns=AUDIT_COLUMNS)
    audit = audit.sort_values(
        by="confidence", key=lambda values: values.map(CONFIDENCE_ORDER)
    ).reset_index(drop=True)
    filled = source.copy(deep=True)
    for field in ("证据片段", "置信度", "来源阶段"):
        if field not in filled.columns:
            filled[field] = None
    attribute_columns = (
        (attribute_a_column, "attribute_a"),
        (attribute_b_column, "attribute_b"),
    )
    for column, _ in attribute_columns:
        filled[column] = filled[column].astype(object)

    for index, row in source.iterrows():
        record = results.get(str(row[entity_column]).strip())
        if record is None or record["confidence"] not in FILLABLE_CONFIDENCE:
            continue
        for column, field in attribute_columns:
            if is_empty(row[column]) and record.get(field):
                filled.at[index, column] = record[field]
        if record.get("evidence_quote"):
            filled.at[index, "证据片段"] = record["evidence_quote"]
        filled.at[index, "置信度"] = record["confidence"]
        if record.get("stage"):
            filled.at[index, "来源阶段"] = record["stage"]
    return audit, filled


def main():
    parser = argparse.ArgumentParser(description="用本地阶段一结果生成审核表及回填结果。")
    parser.add_argument("source", type=Path, help="运行者提供的待补 Excel 路径，替换 xxxx")
    parser.add_argument("extracted", type=Path, help="运行者提供的阶段一结果 JSON 路径，替换 xxxx")
    parser.add_argument("--entity-column", default="entity", help="待补表的实体标识列")
    parser.add_argument("--attribute-a-column", default="attribute_a", help="待补表的第一项属性列")
    parser.add_argument("--attribute-b-column", default="attribute_b", help="待补表的第二项属性列")
    parser.add_argument("--name-marker", action="append", default=[])
    parser.add_argument("--minimum-name-length", type=int)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--filled-output", type=Path, required=True)
    args = parser.parse_args()
    if any(path.name == "xxxx" or not path.is_file() for path in (args.source, args.extracted)):
        parser.error("请将 xxxx 替换为已获准使用的待补表和阶段一结果路径。")
    data_columns = (args.entity_column, args.attribute_a_column, args.attribute_b_column)
    if any(name.strip() in ("", "xxxx") for name in data_columns):
        parser.error("请将 xxxx 替换为待补表的实际列名。")
    if bool(args.name_marker) != (args.minimum_name_length is not None) or (
        args.minimum_name_length is not None and args.minimum_name_length < 1
    ):
        parser.error("重算等级时请同时提供名称判断标记和正整数长度。")
    paths = {args.source.resolve(), args.extracted.resolve(), args.review_output.resolve(), args.filled_output.resolve()}
    if len(paths) != 4:
        parser.error("两个输入和两个输出应使用不同文件。")
    records = json.loads(args.extracted.read_text(encoding="utf-8-sig"))
    results = load_results(records, args.name_marker, args.minimum_name_length)
    audit, filled = review_and_fill(
        pd.read_excel(args.source), results,
        *data_columns,
    )
    audit.to_excel(args.review_output, index=False)
    filled.to_excel(args.filled_output, index=False)


if __name__ == "__main__":
    main()

