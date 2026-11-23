import pandas as pd
import numpy as np
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
import warnings

warnings.filterwarnings('ignore')

# -------------------------- 核心参数配置 --------------------------
# 群体划分参数（第三题：A=学生，其他=上班族）
THIRD_QUESTION_COL = '3、职业或身份（A：在校学生，B：企业工作人员，C：企业或事业单位管理者（基层、中高层），D：普通职员，E：自由职业者F：从事农林牧渔业劳动者，G：个体经营者，H：其他）'
STUDENT_OPTION = 'A'

# 输出文件路径
OUTPUT_EXCEL = '菜品关联规则分析结果（含学生上班族）.xlsx'


# -------------------------- 工具函数 --------------------------
def get_third_question_col(df):
    """匹配第三题列名"""
    if THIRD_QUESTION_COL in df.columns:
        return THIRD_QUESTION_COL
    candidate_cols = [col for col in df.columns if any(keyword in str(col) for keyword in ['3', '第三题', 'Q3'])]
    if candidate_cols:
        selected_col = candidate_cols[0]
        print(f"未找到列名'{THIRD_QUESTION_COL}'，自动匹配第三题列：{selected_col}")
        return selected_col
    raise ValueError("未找到第三题列！请手动设置THIRD_QUESTION_COL")


def split_student_worker(df):
    """根据第三题划分学生和上班族群体"""
    q3_col = get_third_question_col(df)
    df[q3_col] = df[q3_col].astype(str).str.strip()

    df_student = df[df[q3_col] == STUDENT_OPTION].copy()
    df_worker = df[(df[q3_col] != STUDENT_OPTION) & (df[q3_col] != '')].copy()

    print(f"\n【群体划分结果】")
    print(f"总样本数：{len(df)}")
    print(f"学生群体：{len(df_student)} 人（第三题{STUDENT_OPTION}选项，占比{len(df_student) / len(df) * 100:.1f}%）")
    print(f"上班族群体：{len(df_worker)} 人（第三题非{STUDENT_OPTION}选项，占比{len(df_worker) / len(df) * 100:.1f}%）")

    return df_student, df_worker, q3_col


def prepare_transaction_data(df_subset, dish_columns, dish_mapping):
    """准备关联分析的交易数据"""
    dish_data = df_subset[dish_columns].copy()
    dish_data = dish_data.rename(columns=dish_mapping)
    dish_data = dish_data.fillna(0)

    try:
        dish_data = dish_data.map(lambda x: 1 if x == 1 else 0)
    except AttributeError:
        try:
            dish_data = dish_data.applymap(lambda x: 1 if x == 1 else 0)
        except AttributeError:
            dish_data = (dish_data == 1).astype(int)

    transactions = []
    for _, row in dish_data.iterrows():
        bought_dishes = [dish for dish in dish_data.columns if row[dish] == 1]
        if bought_dishes:
            transactions.append(bought_dishes)

    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    transaction_df = pd.DataFrame(te_ary, columns=te.columns_)

    print(f"有效交易数：{len(transactions)}（{len(transactions) / len(df_subset) * 100:.1f}%的用户有购买记录）")
    return transaction_df, transactions, dish_data


def mine_group_rules(transaction_df, group_name, min_support=0.1, min_confidence=0.5):
    """挖掘关联规则"""
    if len(transaction_df) < 50:
        min_support = 0.05
        print(f"{group_name}样本量小，自动降低最小支持度至{min_support}")

    frequent_itemsets = apriori(transaction_df, min_support=min_support, use_colnames=True)
    frequent_itemsets = frequent_itemsets.sort_values('support',
                                                      ascending=False) if not frequent_itemsets.empty else frequent_itemsets

    rules = pd.DataFrame()
    if not frequent_itemsets.empty:
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
        if not rules.empty:
            rules = rules.sort_values(['confidence', 'support'], ascending=[False, False])
            rules['antecedents_str'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
            rules['consequents_str'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
            rules['rule_str'] = rules['antecedents_str'] + ' → ' + rules['consequents_str']

    print(f"{group_name}：频繁项集{len(frequent_itemsets)}个，关联规则{len(rules)}条")
    if not rules.empty:
        print(f"{group_name}Top3规则：\n{rules[['rule_str', 'support', 'confidence']].head(3)}")
    return frequent_itemsets, rules


# -------------------------- 数据读取与处理 --------------------------
# 读取Excel文件
file_path = '2.1处理后问卷.xlsx'
df = pd.read_excel(file_path, sheet_name='Sheet1')

# 查看数据结构
print("=" * 60)
print("1. 原始数据概况")
print("=" * 60)
print(f"数据形状: {df.shape}")
print(f"前10列名称: {df.columns.tolist()[:10]}...（共{len(df.columns)}列）")

# 查找菜品相关列（第17题：含17且带A-F选项）
dish_columns = []
for col in df.columns:
    col_str = str(col)
    if '17' in col_str and any(option in col_str for option in ['A', 'B', 'C', 'D', 'E', 'F']):
        dish_columns.append(col)

if not dish_columns:
    raise ValueError("未找到第17题的菜品列！请检查列名是否含'17'和'A-F'选项")
print(f"\n第17题菜品列：{dish_columns}（共{len(dish_columns)}类菜品）")

# 菜品名称映射
dish_mapping = {
    '17_A': '杂粮拌饭类',
    '17_B': '低卡面食类',
    '17_C': '蒸炖菜品类',
    '17_D': '沙拉凉拌类',
    '17_E': '汤品类',
    '17_F': '粥类'
}

for col in dish_columns:
    if col not in dish_mapping:
        dish_mapping[col] = f'菜品_{col.split("_")[-1]}'

# -------------------------- 群体划分与关联规则挖掘 --------------------------
print("\n" + "=" * 60)
print("2. 群体划分与分群体关联规则")
print("=" * 60)

# 划分学生和上班族群体
df_student, df_worker, q3_col = split_student_worker(df)

# 挖掘整体数据规则
print("\n--- 整体数据关联规则 ---")
global_trans_df, global_trans, global_dish_data = prepare_transaction_data(df, dish_columns, dish_mapping)
global_frequent, global_rules = mine_group_rules(global_trans_df, "整体数据")

# 挖掘学生群体规则
print("\n--- 学生群体关联规则 ---")
student_trans_df, student_trans, student_dish_data = prepare_transaction_data(df_student, dish_columns, dish_mapping)
student_frequent, student_rules = mine_group_rules(student_trans_df, "学生群体")

# 挖掘上班族群体规则
print("\n--- 上班族群体关联规则 ---")
worker_trans_df, worker_trans, worker_dish_data = prepare_transaction_data(df_worker, dish_columns, dish_mapping)
worker_frequent, worker_rules = mine_group_rules(worker_trans_df, "上班族群体")

# -------------------------- Excel结果导出 --------------------------
print("\n" + "=" * 60)
print("3. 结果导出到Excel")
print("=" * 60)
with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
    # 分析概要
    summary_df = pd.DataFrame({
        '统计项目': ['总样本数', '学生样本数', '上班族样本数',
                     '整体有效交易数', '学生有效交易数', '上班族有效交易数',
                     '分析菜品数', '第三题列名'],
        '数值': [len(df), len(df_student), len(df_worker),
                 len(global_trans), len(student_trans), len(worker_trans),
                 len(global_dish_data.columns), q3_col]
    })
    summary_df.to_excel(writer, sheet_name='分析概要', index=False)

    # 菜品购买频率（分群体对比）
    global_freq = global_dish_data.sum().reset_index()
    global_freq.columns = ['菜品类型', '整体购买次数']
    global_freq['整体购买率(%)'] = (global_freq['整体购买次数'] / len(df) * 100).round(1)

    student_freq = student_dish_data.sum().reset_index() if not student_dish_data.empty else pd.DataFrame(
        columns=['index', 0])
    student_freq.columns = ['菜品类型', '学生购买次数']
    student_freq['学生购买率(%)'] = (student_freq['学生购买次数'] / len(df_student) * 100).round(1) if len(
        df_student) > 0 else 0

    worker_freq = worker_dish_data.sum().reset_index() if not worker_dish_data.empty else pd.DataFrame(
        columns=['index', 0])
    worker_freq.columns = ['菜品类型', '上班族购买次数']
    worker_freq['上班族购买率(%)'] = (worker_freq['上班族购买次数'] / len(df_worker) * 100).round(1) if len(
        df_worker) > 0 else 0

    freq_merged = global_freq.merge(student_freq, on='菜品类型', how='left').merge(worker_freq, on='菜品类型',
                                                                                   how='left').fillna(0)
    freq_merged.to_excel(writer, sheet_name='菜品购买频率（分群体）', index=False)

    # 整体频繁项集与关联规则
    if not global_frequent.empty:
        global_itemsets = global_frequent.copy()
        global_itemsets['itemset'] = global_itemsets['itemsets'].apply(lambda x: ', '.join(list(x)))
        global_itemsets[['itemset', 'support']].to_excel(writer, sheet_name='整体频繁项集', index=False)
    if not global_rules.empty:
        global_rules_out = global_rules[['rule_str', 'antecedents_str', 'consequents_str',
                                         'support', 'confidence', 'lift', 'leverage', 'conviction']].copy()
        global_rules_out.columns = ['规则描述', '前项', '后项', '支持度', '置信度', '提升度', '杠杆率', '确信度']
        global_rules_out.to_excel(writer, sheet_name='整体关联规则', index=False)

    # 学生群体工作表
    if not student_frequent.empty:
        student_itemsets = student_frequent.copy()
        student_itemsets['itemset'] = student_itemsets['itemsets'].apply(lambda x: ', '.join(list(x)))
        student_itemsets[['itemset', 'support']].to_excel(writer, sheet_name='学生频繁项集', index=False)

    if not student_rules.empty:
        student_rules_out = student_rules[['rule_str', 'antecedents_str', 'consequents_str',
                                           'support', 'confidence', 'lift']].copy()
        student_rules_out.columns = ['规则描述', '前项', '后项', '支持度', '置信度', '提升度']
        student_rules_out.to_excel(writer, sheet_name='学生关联规则', index=False)

    # 上班族群体工作表
    if not worker_frequent.empty:
        worker_itemsets = worker_frequent.copy()
        worker_itemsets['itemset'] = worker_itemsets['itemsets'].apply(lambda x: ', '.join(list(x)))
        worker_itemsets[['itemset', 'support']].to_excel(writer, sheet_name='上班族频繁项集', index=False)

    if not worker_rules.empty:
        worker_rules_out = worker_rules[['rule_str', 'antecedents_str', 'consequents_str',
                                         'support', 'confidence', 'lift']].copy()
        worker_rules_out.columns = ['规则描述', '前项', '后项', '支持度', '置信度', '提升度']
        worker_rules_out.to_excel(writer, sheet_name='上班族关联规则', index=False)

    # 群体规则对比（Top5）
    compare_data = []
    if not student_rules.empty:
        for i, (_, row) in enumerate(student_rules.head(5).iterrows(), 1):
            compare_data.append(['学生', i, row['rule_str'], row['support'], row['confidence'], row['lift']])
    if not worker_rules.empty:
        for i, (_, row) in enumerate(worker_rules.head(5).iterrows(), 1):
            compare_data.append(['上班族', i, row['rule_str'], row['support'], row['confidence'], row['lift']])

    if compare_data:
        compare_df = pd.DataFrame(compare_data, columns=['群体', '排名', '规则描述', '支持度', '置信度', '提升度'])
        compare_df.to_excel(writer, sheet_name='群体规则对比（Top5）', index=False)

    # 原始数据预览
    global_dish_data.head(100).to_excel(writer, sheet_name='原始数据预览', index=False)

# -------------------------- 核心结果展示 --------------------------
print("\n" + "=" * 60)
print("4. 核心分析结果")
print("=" * 60)
if not global_rules.empty:
    top_global = global_rules.iloc[0]
    print(f"\n【整体核心规则】")
    print(f"最强关联规则：{top_global['rule_str']}")
    print(f"置信度：{top_global['confidence']:.3f}，支持度：{top_global['support']:.3f}")

print(f"\n【群体规则摘要】")
if not student_rules.empty:
    top_student = student_rules.iloc[0]
    print(f"学生群体核心规则：{top_student['rule_str']}（置信度{top_student['confidence']:.3f}）")
else:
    print(f"学生群体：未挖掘到有效关联规则")

if not worker_rules.empty:
    top_worker = worker_rules.iloc[0]
    print(f"上班族群体核心规则：{top_worker['rule_str']}（置信度{top_worker['confidence']:.3f}）")
else:
    print(f"上班族群体：未挖掘到有效关联规则")

print("\n" + "=" * 60)
print("分析完成")
print("=" * 60)
