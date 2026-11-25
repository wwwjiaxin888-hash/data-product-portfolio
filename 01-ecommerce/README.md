# 电商用户行为分析与简易问数助手

我用 Python 清洗电商行为日志，在 MySQL 中建立分层数仓，并通过 FineBI 展示各行为去重用户数、品类表现与留存。随后用 Figma 设计问数界面，在 Coze 中实现查询条件校验、指标汇总和异常反馈。

**数据范围**　2024-11-25 至 2024-12-04，清洗后共 **10,000 条行为日志、880 名用户、8 个品类**。

## FineBI 看板与筛选验收

![FineBI 各行为去重用户数，日期为 2024-11-30，品类为 1004](assets/finebi-activity-bar.png)

浏览、收藏、加购和购买在当前日期与品类下分别按用户去重。同一用户可以同时计入多种行为。横向条形图用于比较人数。日活图显示筛选范围内的去重活跃用户数，图中异常提示使用全站历史基线，仅供全站口径参考。

| 组合筛选 | 浏览 | 收藏 | 加购 | 购买 |
| --- | ---: | ---: | ---: | ---: |
| 2024-11-30 × 1004 | 141 | 16 | 49 | 18 |
| 2024-11-29 × 1002 | 81 | 9 | 24 | 10 |

两组筛选下的四项人数均与清洗日志独立复算一致。品类 1004 在全观察期的购买人数与浏览人数之比为 **127 ÷ 542 ≈ 23.43%**，分子和分母均从明细按用户分别去重。

留存按首访日期分组，超出日志覆盖期的留存值保留缺失。[FineBI 留存曲线](assets/FineBI%E7%95%99%E5%AD%98.png)。

## Coze 工作流与 Figma 原型

对同一套 20 道题逐题复测，问数工作流通过数从 **12/20 提升到 19/20**。表中保留标准答案、判定规则、两轮实际回答和失败原因。[下载首测与复测判定表（Excel）](assets/coze-evaluation-20-questions.xlsx)

- [Coze汇总查询工作流修订截图](assets/Coze%E6%B1%87%E6%80%BB%E6%9F%A5%E8%AF%A2%E5%B7%A5%E4%BD%9C%E6%B5%81%E4%BF%AE%E8%AE%A2%E6%88%AA%E5%9B%BE.png)。提取日期与查询条件、校验范围、执行汇总 SQL、格式化指标结果并处理异常。
- [Coze工作流卡片更新截图](assets/Coze%E5%B7%A5%E4%BD%9C%E6%B5%81%E5%8D%A1%E7%89%87%E6%9B%B4%E6%96%B0%E6%88%AA%E5%9B%BE.png)。展示智能体配置和品类 1004 的示例问答。另附[Coze商店新版卡片截图](assets/Coze%E5%95%86%E5%BA%97%E6%96%B0%E7%89%88%E5%8D%A1%E7%89%87%E6%88%AA%E5%9B%BE.png)。

[查看问数助手的 Figma 原型](https://www.figma.com/design/7qgWOwCRUxYxpi2MOFkcQ0/%E7%94%B5%E5%95%86%E7%94%A8%E6%88%B7%E8%A1%8C%E4%B8%BA%E5%88%86%E6%9E%90)

| Figma 查询结果 | Figma 日期超范围提示 |
| --- | --- |
| <img src="assets/query-result.png" width="210" alt="Figma 原型，显示查询结果与各行为去重人数"> | <img src="assets/date-out-of-range.png" width="210" alt="Figma 原型，提示可查询日期范围并引导修改日期"> |

## 代码入口

| 操作 | 文件 |
| --- | --- |
| 清洗、去重并转换时间戳 | [数据清洗.ipynb](notebooks/%E6%95%B0%E6%8D%AE%E6%B8%85%E6%B4%97.ipynb) |
| 计算各行为去重用户数 | [漏斗计算.ipynb](notebooks/%E6%BC%8F%E6%96%97%E8%AE%A1%E7%AE%97.ipynb) |
| 按日期和品类汇总 | [品类_日期聚合表.ipynb](notebooks/%E5%93%81%E7%B1%BB_%E6%97%A5%E6%9C%9F%E8%81%9A%E5%90%88%E8%A1%A8.ipynb) |
| 计算次日留存和 FineBI 留存曲线所需数据 | [次日留存率的计算.ipynb](notebooks/%E6%AC%A1%E6%97%A5%E7%95%99%E5%AD%98%E7%8E%87%E7%9A%84%E8%AE%A1%E7%AE%97.ipynb)、[生成retention.csv导入FineBI做留存曲线.ipynb](notebooks/%E7%94%9F%E6%88%90retention.csv%E5%AF%BC%E5%85%A5FineBI%E5%81%9A%E7%95%99%E5%AD%98%E6%9B%B2%E7%BA%BF.ipynb) |
| 建立 ODS、DWD、DWS 和 ADS 表 | [数仓建库_.sql](sql/%E6%95%B0%E4%BB%93%E5%BB%BA%E5%BA%93_.sql) |
| 只读核对表、日期和品类去重口径 | [品类口径只读核对.sql](sql/%E5%93%81%E7%B1%BB%E5%8F%A3%E5%BE%84%E5%8F%AA%E8%AF%BB%E6%A0%B8%E5%AF%B9.sql) |

Notebook 使用 pandas、NumPy、Matplotlib、seaborn 和 Excel 导出依赖 openpyxl。清洗入口读取本地原始日志 `practice.csv`，下游 Notebook 读取生成的 `output/data_clean.csv`。作品集公开代码和截图，原日志保存在本地。

建表脚本含 `DROP` 和 `TRUNCATE`，用于准备好输入数据的测试数据库。检查已有结果可使用只读 SQL。
