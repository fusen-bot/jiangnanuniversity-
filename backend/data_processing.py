import pandas as pd
from datetime import datetime, timedelta
from utils import read_excel, is_internal, match_employee_info

def process_review_data(review_file, re_review_file, employee_file, retired_file, target_month):
    """
    处理审稿数据的主函数 - 修改版
    """
    # 读取所有文件
    review_df = read_excel(review_file)
    re_review_df = read_excel(re_review_file)
    employee_df = read_excel(employee_file)
    retired_df = read_excel(retired_file)

    if review_df is None or re_review_df is None or employee_df is None or retired_df is None:
        print("错误：一个或多个必要的文件无法读取。请检查文件路径和格式。")
        return None

    # 转换日期列并格式化为年月日
    review_df['审回时间'] = pd.to_datetime(review_df['审回时间']).dt.strftime('%Y-%m-%d')
    re_review_df['审回时间'] = pd.to_datetime(re_review_df['审回时间']).dt.strftime('%Y-%m-%d')

    # 筛选目标月份数据
    target_date = datetime.strptime(target_month, "%Y-%m")
    start_date = target_date.replace(day=1)
    end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # 筛选月份（需要重新转换日期进行比较）
    review_df['比较日期'] = pd.to_datetime(review_df['审回时间'])
    re_review_df['比较日期'] = pd.to_datetime(re_review_df['审回时间'])
    
    review_df = review_df[(review_df['比较日期'] >= start_date) & (review_df['比较日期'] <= end_date)]
    re_review_df = re_review_df[(re_review_df['比较日期'] >= start_date) & (re_review_df['比较日期'] <= end_date)]
    
    # 删除比较日期列
    review_df = review_df.drop('比较日期', axis=1)
    re_review_df = re_review_df.drop('比较日期', axis=1)

    # 添加数据来源标记
    review_df['审稿类型'] = '评审'
    re_review_df['审稿类型'] = '复审'

    # 合并评审和复审数据
    combined_df = pd.concat([review_df, re_review_df], ignore_index=True)

    # 剔除审稿费金额为空或 0 的数据
    combined_df = combined_df[combined_df['审稿费金额'].notna() & (combined_df['审稿费金额'] != 0)]

    # 判断校内/校外
    combined_df['校内人员'] = combined_df.apply(lambda row: is_internal(row['审稿人单位'], row['审稿人地址']), axis=1)

    # 工号匹配
    combined_df['工号'] = ''
    combined_df['部门'] = ''
    combined_df['工号重复'] = False
    combined_df['人员状态'] = ''
    
    for idx, row in combined_df[combined_df['校内人员']].iterrows():
        emp_id, department, is_duplicate, status = match_employee_info(row['审稿人姓名'], employee_df, retired_df)
        combined_df.at[idx, '工号'] = emp_id if emp_id else ''
        combined_df.at[idx, '部门'] = department if department else ''
        combined_df.at[idx, '工号重复'] = is_duplicate
        combined_df.at[idx, '人员状态'] = status

    # 只检查校外专家的银行账户信息
    combined_df['银行账户缺失'] = ''
    bank_account_column = '银行账号'
    bank_name_column = '开户银行'
    
    if bank_account_column in combined_df.columns and bank_name_column in combined_df.columns:
        mask = (~combined_df['校内人员']) & (
            combined_df[bank_account_column].isna() | 
            combined_df[bank_name_column].isna()
        )
        combined_df.loc[mask, '银行账户缺失'] = '缺失'

    # 删除指定的列
    columns_to_drop = [
        '审稿流水号', '杂志编号', '职称', '出生年月', '审稿人邮箱', '会议ID','汇款时间','汇款单号','结算方式','备注','一级分类'
    ]
    combined_df = combined_df.drop(columns=columns_to_drop, errors='ignore')

    # 重新排列列顺序
    desired_columns = ['审稿类型', '稿件编号', '审稿人姓名', '审回时间', '审稿人单位', 
                      '审稿人地址', '审稿费金额', '工号','部门']
    
    # 获取实际存在的列
    existing_columns = [col for col in desired_columns if col in combined_df.columns]
    # 添加其他可能存在的列
    remaining_columns = [col for col in combined_df.columns if col not in existing_columns]
    final_columns = existing_columns + remaining_columns

    combined_df = combined_df[final_columns]

    # 在返回数据之前，将 NaN 值替换为 None
    return combined_df.where(pd.notnull(combined_df), None).to_dict(orient='records')

def query_by_employee_id(employee_data, employee_id):
    try:
        employee_ids = [int(id.strip()) for id in str(employee_id).split()]
        results = []
        for emp_id in employee_ids:
            result = employee_data[employee_data['工号'] == emp_id]
            if not result.empty:
                results.extend(result[['姓名', '工号', '部门']].to_dict(orient='records'))
        
        if not results:
            return {"message": f"未找到工号为 {employee_id} 的员工"}
        return results
    except ValueError as e:
        return {"message": f"无效的工号格式: {str(e)}"}

def query_by_name(employee_data, name):
    names = [n.strip() for n in name.split()]
    results = []
    for n in names:
        result = employee_data[employee_data['姓名'] == n]
        if not result.empty:
            results.extend(result[['姓名', '工号', '部门']].to_dict(orient='records'))
    
    if not results:
        return {"message": f"未找到姓名为 {name} 的员工"}
    return results

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
