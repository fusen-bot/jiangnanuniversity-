import pandas as pd

def read_excel(data):
    try:
        if data.endswith('.xlsx'):
            return pd.read_excel(data, engine='openpyxl')
        elif data.endswith('.xls'):
            return pd.read_excel(data, engine='xlrd')
        else:
            raise ValueError(f"不支持的文件格式: {data}")
    except Exception as e:
        print(f"读取文件 {data} 时出错: {e}")
        return None

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
