import pandas as pd
import numpy as np
import random


def pps_sampling_code_method(population_data, sample_size, layer_name):
    """
    PPS代码法抽样，生成包含区域范围及抽中结果的DataFrame
    """
    data = population_data.copy().reset_index(drop=True)

    # 计算人口数（人）和累积人口（人）
    data['人口数(人)'] = data['2023常住人口（单位：万人）'] * 10000
    data['累积人口(人)'] = data['人口数(人)'].cumsum()

    # 计算每个区域的起始/结束范围（人）
    data['起始范围(人)'] = data['累积人口(人)'].shift(fill_value=0) + 1
    data['结束范围(人)'] = data['累积人口(人)']

    # 总人口与抽样间隔
    total_population = data['结束范围(人)'].iloc[-1]
    sampling_interval = total_population / sample_size

    # 生成随机数序列
    random_start = random.randint(1, int(sampling_interval))
    random_numbers = [random_start + i * sampling_interval for i in range(sample_size)]

    # 初始化抽中标识列
    data['随机数'] = np.nan
    data['抽中再编号'] = np.nan

    # 匹配随机数到区域区间
    for i, rand_num in enumerate(random_numbers):
        for idx, row in data.iterrows():
            if row['起始范围(人)'] <= rand_num <= row['结束范围(人)']:
                data.loc[idx, '随机数'] = rand_num
                data.loc[idx, '抽中再编号'] = i + 1
                break  # 找到一个就跳出内层循环
    # 格式整理：统一列名与单位
    data = data.rename(columns={
        '地区': '行政区',
        '2023常住人口（单位：万人）': '居民户数(万人)',
        '累积人口(人)': '累积(万人)'
    })
    data['累积(万人)'] = data['累积(万人)'] / 10000  # 转换为“万人”单位
    data['规定范围'] = data.apply(lambda x: f"{int(x['起始范围(人)'])}-{int(x['结束范围(人)'])}", axis=1)
    data['层级'] = layer_name

    # 添加序号
    data = data.reset_index().rename(columns={'index': '序号'})
    data['序号'] = data['序号'] + 1  # 序号从1开始

    # 选择最终展示列
    return data[['序号', '行政区', '居民户数(万人)', '累积(万人)', '规定范围', '随机数', '抽中再编号', '层级']]


# --- 主程序 ---

# 这里的'分层'列用于区分市区和县区
df = pd.DataFrame({
    '分层': ['市区', '市区', '市区', '市区', '市区', '市区', '县区', '县区', '县区', '县区', '县区'],
    '地区': ['荔湾区', '越秀区', '海珠区', '天河区', '黄埔区', '番禺区', '白云区', '花都区', '南沙区', '从化区',
             '增城区'],
    '2023常住人口（单位：万人）': [113.30, 96.00, 176.83, 223.80, 122.21, 282.29, 366.68, 172.87, 96.79, 73.26, 158.67]
})

# 从Excel文件读取数据
# df = pd.read_excel('2023年各区常住人口.xlsx')

print("原始数据:")
print(df)
print("\n" + "=" * 80 + "\n")

# 分离市区和县区数据
urban_data = df[df['分层'] == '市区'].reset_index(drop=True)
county_data = df[df['分层'] == '县区'].reset_index(drop=True)

# 执行PPS抽样
print("PPS抽样结果 - 广州市入样区")

# 市区抽取3个区
urban_samples = pps_sampling_code_method(urban_data, 3, "市区")
print("\n【市区抽样结果】 (计划抽取3个)")
# 显示关键列
print(urban_samples[['序号', '行政区', '居民户数(万人)', '累积(万人)', '规定范围', '随机数', '抽中再编号']].to_string(
    index=False, na_rep=''))

# 县区抽取2个区
county_samples = pps_sampling_code_method(county_data, 2, "县区")
print("\n【县区抽样结果】 (计划抽取2个)")
print(county_samples[['序号', '行政区', '居民户数(万人)', '累积(万人)', '规定范围', '随机数', '抽中再编号']].to_string(
    index=False, na_rep=''))

# 抽样过程详细信息
print("\n" + "=" * 80)
print("抽样过程详细信息:")
urban_total_pop = urban_data['2023常住人口（单位：万人）'].sum() * 10000
county_total_pop = county_data['2023常住人口（单位：万人）'].sum() * 10000

print(f"\n[市区层]")
print(f"  总人口: {urban_total_pop:,.0f}人")
print(f"  抽样间隔: {urban_total_pop / 3:,.0f}人")
selected_urban_areas = urban_samples[urban_samples['抽中再编号'].notna()]['行政区'].tolist()
print(f"  实际入样行政区: {', '.join(selected_urban_areas)}")

print(f"\n[县区层]")
print(f"  总人口: {county_total_pop:,.0f}人")
print(f"  抽样间隔: {county_total_pop / 2:,.0f}人")
selected_county_areas = county_samples[county_samples['抽中再编号'].notna()]['行政区'].tolist()
print(f"  实际入样行政区: {', '.join(selected_county_areas)}")

print("\n" + "=" * 80)
