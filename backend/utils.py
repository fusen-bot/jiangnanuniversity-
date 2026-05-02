import pandas as pd

def read_excel(data):
    try:
        if data.endswith('.xlsx'):
            # 指定身份证号列为字符串类型，避免被转换为科学记数法
            dtype_dict = {'审稿人身份证号': str}
            return pd.read_excel(data, engine='openpyxl', dtype=dtype_dict)
        elif data.endswith('.xls'):
            dtype_dict = {'审稿人身份证号': str}
            return pd.read_excel(data, engine='xlrd', dtype=dtype_dict)
        else:
            raise ValueError(f"不支持的文件格式: {data}")
    except Exception as e:
        print(f"读取文件 {data} 时出错: {e}")
        return None

def check_id_card_column(df, column_name='审稿人身份证号'):
    """
    检查身份证号列的数据类型和样本数据
    """
    if column_name not in df.columns:
        return {
            'error': f'列 "{column_name}" 不存在',
            'available_columns': list(df.columns)
        }
    
    # 获取列的数据类型
    dtype = df[column_name].dtype
    
    # 获取前5行样本数据
    sample_data = df[column_name].head().tolist()
    
    # 检查是否有科学记数法格式的数据
    scientific_notation_count = 0
    for value in df[column_name].dropna():
        if isinstance(value, (int, float)) and 'e' in str(value).lower():
            scientific_notation_count += 1
    
    # 检查是否有空值
    null_count = df[column_name].isnull().sum()
    
    return {
        'column_name': column_name,
        'data_type': str(dtype),
        'sample_data': sample_data,
        'scientific_notation_count': scientific_notation_count,
        'null_count': null_count,
        'total_rows': len(df),
        'has_scientific_notation': scientific_notation_count > 0
    }

def is_internal(unit, address):
    keywords = ['江南大学', '蠡湖大道', '1800号']
    return any(keyword in str(unit) or keyword in str(address) for keyword in keywords)

def match_employee_info(name, employee_df, retired_df):
    matches = employee_df[employee_df['姓名'] == name]
    if len(matches) == 0:
        retired_matches = retired_df[retired_df['姓名'] == name]
        if len(retired_matches) == 0:
            return None, None, False, 'not_found'
        elif len(retired_matches) == 1:
            return retired_matches.iloc[0]['工号'], retired_matches.iloc[0]['部门'], False, 'retired'
        else:
            return retired_matches.iloc[0]['工号'], retired_matches.iloc[0]['部门'], True, 'retired'
    elif len(matches) == 1:
        return matches.iloc[0]['工号'], matches.iloc[0]['部门'], False, 'active'
    else:
        return matches.iloc[0]['工号'], matches.iloc[0]['部门'], True, 'active'
