import pandas as pd
import numpy as np
import random
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# 设置随机种子以确保结果可重现
random.seed(2024)
np.random.seed(2024)

# 街道数据
data = {
    '区': [],
    '街道': []
}

# 荔湾区街道
liwan_streets = ['石围塘', '金花', '沙面', '华林', '多宝', '昌华', '逢源', '龙津', '彩虹', '南源',
                 '西村', '站前', '岭南', '桥中', '冲口', '花地', '茶滘', '中南', '东漖', '东沙', '海龙', '白鹤洞']
# 海珠区街道
haizhu_streets = ['江海', '赤岗', '新港', '滨江', '素社', '凤阳', '龙凤', '沙园', '瑞宝', '海幢',
                  '南华西', '南石头', '江南中', '昌岗', '南洲', '琶洲', '官洲', '华洲']
# 黄埔区街道
huangpu_streets = ['萝岗', '夏港', '联和', '永和', '大沙', '黄埔', '红山', '鱼珠', '文冲', '南岗',
                   '穗东', '长洲', '长岭', '云埔', '九佛', '龙湖']
# 白云区街道
baiyun_streets = ['景泰', '松洲', '同德', '黄石', '棠景', '新市', '三元里', '同和', '京溪', '永平',
                  '均禾', '金沙', '石井', '嘉禾', '云城', '鹤龙', '白云湖', '石门', '龙归', '大源']
# 花都区街道
huadu_streets = ['花城', '新华', '新雅', '秀全']

# 构建完整数据集
for street in liwan_streets:
    data['区'].append('荔湾区')
    data['街道'].append(street)

for street in haizhu_streets:
    data['区'].append('海珠区')
    data['街道'].append(street)

for street in huangpu_streets:
    data['区'].append('黄埔区')
    data['街道'].append(street)

for street in baiyun_streets:
    data['区'].append('白云区')
    data['街道'].append(street)

for street in huadu_streets:
    data['区'].append('花都区')
    data['街道'].append(street)

# 创建DataFrame
df = pd.DataFrame(data)

# 为每个街道生成随机数
df['随机数'] = np.random.random(len(df))

# 按区和随机数排序
df_sorted = df.sort_values(['区', '随机数'])

# 选择每个区的前3个街道
selected_streets = df_sorted.groupby('区').head(3).reset_index(drop=True)

# 添加序号列
selected_streets['序号'] = selected_streets.groupby('区').cumcount() + 1

# 添加层级列（市区/县区）
def get_level(district):
    if district in ['荔湾区', '海珠区', '黄埔区']:
        return '市区'
    else:
        return '县区'

selected_streets['层级'] = selected_streets['区'].apply(get_level)

# 重新排列列的顺序
selected_streets = selected_streets[['层级', '区', '街道', '随机数', '序号']]

# 显示结果
print("广州市入样区街道抽样结果")
print("=" * 50)
for district in selected_streets['区'].unique():
    district_data = selected_streets[selected_streets['区'] == district]
    print(f"\n※{district}")
    streets_str = "、".join([f"※{street}" for street in district_data['街道'].values])
    print(f"街道：{streets_str}")
    print(f"{len(district_data)}个街道")
print(f"\n总计：{len(selected_streets)}个街道")

# 导出到Excel - 创建两个工作表
with pd.ExcelWriter('广州市入样街道抽样结果.xlsx', engine='openpyxl') as writer:
    # 工作表1：原始数据
    selected_streets.to_excel(writer, sheet_name='抽样详细数据', index=False)

    # 工作表2：抽样结果表格
    wb = writer.book
    ws = wb.create_sheet(title='抽样结果表格')

    # 定义表格标题
    headers = ['初级单元', '入样行政区', '第二单元抽样框', '入样街道', '第三级抽样框']

    # 写入表头
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    # 写入数据
    row = 2
    last_level = None
    last_district = None

    for _, street_data in selected_streets.iterrows():
        current_level = street_data['层级']
        current_district = street_data['区']

        # 初级单元（市区/县区） - 只在变化时显示
        level_value = current_level if current_level != last_level else ""

        # 入样行政区 - 只在变化时显示
        district_value = current_district if current_district != last_district else ""

        ws.cell(row=row, column=1, value=level_value)
        ws.cell(row=row, column=2, value=district_value)
        ws.cell(row=row, column=3, value=f"{current_district}所有街道")
        ws.cell(row=row, column=4, value=f"{street_data['街道']}街道")
        ws.cell(row=row, column=5, value="*")

        last_level = current_level
        last_district = current_district
        row += 1

    # 添加表格注释
    ws.cell(row=row + 1, column=1, value="注：*代表该街道所有居民为抽样框")

    # 设置表格样式
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))

    # 应用边框
    for r in range(1, row):
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = thin_border

    # 设置标题行加粗
    for c in range(1, 6):
        ws.cell(row=1, column=c).font = Font(bold=True)

    # 设置列宽
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15

    # 设置对齐方式
    for r in range(1, row + 2):
        for c in range(1, 6):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal='center', vertical='center')

# 创建工作表3：按区汇总的街道列表
with pd.ExcelWriter('广州市入样街道抽样结果.xlsx', engine='openpyxl', mode='a') as writer:
    wb = writer.book
    ws3 = wb.create_sheet(title='街道分布格式')

    # 写入标题
    ws3.merge_cells('A1:C1')
    ws3['A1'] = '广州市入样区街道分布'
    ws3['A1'].font = Font(bold=True, size=14)
    ws3['A1'].alignment = Alignment(horizontal='center')
    # 写入各区街道信息
    row = 3
    for district in selected_streets['区'].unique():
        district_data = selected_streets[selected_streets['区'] == district]

        # 写入区名
        ws3.cell(row=row, column=1, value=f"※{district}")
        ws3.cell(row=row, column=1).font = Font(bold=True)
        row += 1

        # 写入街道列表
        streets_list = "、".join([f"※{street}" for street in district_data['街道'].values])
        ws3.cell(row=row, column=1, value=f"街道：{streets_list}")
        row += 1

        # 写入街道数量
        ws3.cell(row=row, column=1, value=f"{len(district_data)}个街道")
        row += 1

        # 空一行
        row += 1

    # 写入总计
    ws3.cell(row=row, column=1, value=f"总计：{len(selected_streets)}个街道")
    ws3.cell(row=row, column=1).font = Font(bold=True)

# 显示抽样结果表格
print("\n抽样结果表格：")
print(selected_streets[['层级', '区', '街道']].to_string(index=False))
