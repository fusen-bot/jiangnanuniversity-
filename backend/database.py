import pandas as pd
from utils import read_excel

def load_employee_data(employee_file, retired_file):
    employee_df = read_excel(employee_file)
    retired_df = read_excel(retired_file)
    if employee_df is None or retired_df is None:
        print("错误：无法读取员工数据文件")
        return None
    combined_df = pd.concat([employee_df, retired_df])
    combined_df['工号'] = pd.to_numeric(combined_df['工号'], errors='coerce').fillna(0).astype(int)
    return combined_df
