# 广州中式轻食消费者偏好调研

**市场调查与分析大赛** · PPS 抽样 / SPSS / Python / Apriori

参与抽样与数据分析，使用多阶段 PPS 抽样及量表信效度检验。项目获得 **611 份有效问卷**，有效率为 **87.3%**。

- **痛点识别。** 价格偏高和口味单一分别占 **71.69%** 和 **69.56%**。
- **偏好分析。** 用 Apriori 分析不同人群的菜品共现，学生群体排名前五的规则置信度均超过 **0.64**。
- **方案建议。** 将菜品共现结果作为套餐组合的参考，结合不同人群的预算与渠道差异提出营销建议。

## 报告与原项目代码

- [下载团队报告节选（PDF，17 页）](https://raw.githubusercontent.com/wwwjiaxin888-hash/data-product-portfolio/main/04-market-research/research-report-excerpts.pdf)。节选保留原报告页码。抽样设计见第 19–22 页，量表检验见第 28–30 页，菜品关联规则见第 43–45 页，结论与建议见第 57–61 页。
- [PPS 入样区抽取](pps-district.py) 和 [入样街道抽取](pps-street.py)。源自团队《代码修改.docx》中两段抽样代码。
- [Apriori 关联规则分析](apriori-analysis.py)。源自同一附件，展示按人群整理交易项集、计算支持度和置信度并筛选规则。
- [下载原报告营销模型结果（PDF）](https://raw.githubusercontent.com/wwwjiaxin888-hash/data-product-portfolio/main/04-market-research/marketing-analysis-tables.pdf)。摘自《三稿.pdf》的营销模式章节，保留原图表和页码。

这些是团队原项目的文件。我参与抽样与数据分析。复现需团队授权的问卷及抽样输入。
