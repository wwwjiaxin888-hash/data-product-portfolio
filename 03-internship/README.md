# 实习案例｜数据处理与质量校验

三个案例展示如何生成并验收月度统计汇总、审核与回填 AI 抽取结果，以及按层级生成企业关系路径。运行时由使用者提供获准使用的输入文件和字段参数。

| 案例 | 参与工作 | 代码 |
| --- | --- | --- |
| 月度企业统计 | 参与核对统计口径，和搭档使用流式分块统计生成汇总并复核结果 | [流式分块](月度统计_流式分块.py)、[一致性校验](月度统计_一致性校验.py) |
| AI 抽取结果审核与回填 | 复现审核和回填流程，核对空字段、原表已有值和证据记录 | [审核与回填](实体属性补全_审核与回填.py) |
| 企业关系层级分析 | 复现从根节点向下遍历企业关系的实现，核对层级和路径统计口径 | [BFS 层级遍历](股权穿透_BFS层级遍历.py) |

## 运行方式

使用 Python 3 和 pandas。实体属性补全脚本读写 XLSX 时还需要 openpyxl。将命令中的每个 `xxxx` 替换为相应的本地文件路径、字段名、统计类别或根节点标识。

```text
python 月度统计_流式分块.py "xxxx" --group "xxxx" --metric "xxxx" --output summary.jsonl
python 月度统计_一致性校验.py "xxxx" summary.jsonl
python 实体属性补全_审核与回填.py "xxxx" "xxxx" --entity-column "xxxx" --attribute-a-column "xxxx" --attribute-b-column "xxxx" --review-output review.xlsx --filled-output filled.xlsx
python 股权穿透_BFS层级遍历.py "xxxx" "xxxx" --output paths.csv --checkpoint progress.json
```

## 输入与输出

| 脚本 | 输入与输出 |
| --- | --- |
| 流式分块与一致性校验 | 明细 JSONL 每行提供 `stat_date`、`province`、`city`、`record_id`、类别列表 `groups` 和待汇总的数值字段。输出汇总 JSONL。校验脚本对比两份同口径汇总，报告行键、字段和值的差异。 |
| 实体属性补全 | 前两个参数依次为待补 XLSX 和抽取结果 JSON。JSON 是对象数组，每项提供唯一的 `entity`、`confidence`，以及可用的 `attribute_a`、`attribute_b`、`context`、`evidence_quote` 和 `stage`。输出审核表和回填表。 |
| 企业关系层级分析 | 前两个参数依次为关系 JSON 和根节点标识。JSON 的键为父节点标识，值为下级记录数组，每条下级记录提供 `name`，可附 `status`。输出路径 CSV。恢复时沿用原参数和断点路径，在命令末尾加 `--resume`。 |

## 分享范围

分享范围为本页和四份处理脚本。请在本地保存输入文件及用真实数据生成的 JSONL、Excel、CSV 和断点文件。
