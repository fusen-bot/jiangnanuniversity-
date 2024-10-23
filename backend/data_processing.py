import pandas as pd
from datetime import datetime, timedelta
from utils import read_excel, is_internal, match_employee_info

def process_review_data(review_file, re_review_file, employee_file, retired_file, target_month):
    # 读取文件
    review_df = read_excel(review_file)
    re_review_df = read_excel(re_review_file)
    employee_df = read_excel(employee_file)
    retired_df = read_excel(retired_file)

    if review_df is None or re_review_df is None or employee_df is None or retired_df is None:
        print("错误：一个或多个必要的文件无法读取。请检查文件路径和格式。")
        return None

    # 转换日期列
    review_df['审回时间'] = pd.to_datetime(review_df['审回时间'])
    re_review_df['审回时间'] = pd.to_datetime(re_review_df['审回时间'])

    # 筛选目标月份数据
    target_date = datetime.strptime(target_month, "%Y-%m")
    start_date = target_date.replace(day=1)
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    next_month_end = end_date + timedelta(days=31)

    review_df = review_df[(review_df['审回时间'] >= start_date) & (review_df['审回时间'] <= end_date)]
    re_review_df = re_review_df[(re_review_df['审回时间'] >= start_date) & (re_review_df['审回时间'] <= next_month_end)]

    # 初始化费用
    review_df['审稿费用'] = 150
    review_df['复审'] = False
    review_df['复审月份'] = ''

    # 处理复审数据
    for _, row in re_review_df.iterrows():
        mask = (review_df['稿件编号'] == row['稿件编号'])
        if mask.any():
            review_df.loc[mask, '审稿费用'] = review_df.loc[mask, '审稿费用'].apply(lambda x: min(x + 50, 200))
            review_df.loc[mask, '复审'] = True
            current_month = row['审回时间'].strftime('%Y-%m')
            review_df.loc[mask, '复审月份'] += f"{current_month}," if review_df.loc[mask, '复审月份'].values[0] else current_month
        else:
            print(f"警告：复审记录无匹配的评审记录 - 稿件编号: {row['稿件编号']}")

    # 判断校内/校外
    review_df['校内人员'] = review_df.apply(lambda row: is_internal(row['审稿人单位'], row['审稿人地址']), axis=1)

    # 工号匹配
    review_df['工号'] = ''
    review_df['部门'] = ''
    review_df['工号重复'] = False
    review_df['人员状态'] = ''
    for idx, row in review_df[review_df['校内人员']].iterrows():
        emp_id, department, is_duplicate, status = match_employee_info(row['审稿人姓名'], employee_df, retired_df)
        review_df.at[idx, '工号'] = emp_id if emp_id else ''
        review_df.at[idx, '部门'] = department if department else ''
        review_df.at[idx, '工号重复'] = is_duplicate
        review_df.at[idx, '人员状态'] = status

    # 检查校外专家的银行账户信息
    review_df['银行账户缺失'] = False
    bank_account_column = '银行账号'
    bank_name_column = '开户银行'
    
    if bank_account_column in review_df.columns and bank_name_column in review_df.columns:
        review_df.loc[~review_df['校内人员'], '银行账户缺失'] = (
            review_df.loc[~review_df['校内人员'], bank_account_column].isna() & 
            review_df.loc[~review_df['校内人员'], bank_name_column].isna()
        )
    else:
        print("警告：未找到银行账户信息列。无法完全检查银行账户信息。")

    # 在返回数据之前，将 NaN 值替换为 None
    return review_df.where(pd.notnull(review_df), None).to_dict(orient='records')

def query_by_employee_id(employee_data, employee_id):
    result = employee_data[employee_data['工号'] == employee_id]
    if result.empty:
        return {"message": f"未找到工号为 {employee_id} 的员工"}
    else:
        return result[['姓名', '工号', '部门']].to_dict(orient='records')

def query_by_name(employee_data, name):
    result = employee_data[employee_data['姓名'] == name]
    if result.empty:
        return {"message": f"未找到姓名为 {name} 的员工"}
    else:
        return result[['姓名', '工号', '部门']].to_dict(orient='records')

def query_by_manuscript_id_or_reviewer(review_file, re_review_file, query):
    review_df = read_excel(review_file)
    re_review_df = read_excel(re_review_file)

    if review_df is None or re_review_df is None:
        return {"error": "无法读取评审表或复审表文件"}

    review_df['稿件编号'] = review_df['稿件编号'].astype(str)
    re_review_df['稿件编号'] = re_review_df['稿件编号'].astype(str)

    review_result = review_df[(review_df['稿件编号'] == query) | (review_df['审稿人姓名'] == query)]
    re_review_result = re_review_df[(re_review_df['稿件编号'] == query) | (re_review_df['审稿人姓名'] == query)]

    results = {
        "review": review_result[['稿件编号', '审稿人姓名', '审回时间']].to_dict(orient='records'),
        "re_review": re_review_result[['稿件编号', '审稿人姓名', '审回时间']].to_dict(orient='records')
    }

    return results
