#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查现有Excel文件中身份证号列的数据类型
"""

import os
import pandas as pd
from utils import check_id_card_column, read_excel

def check_excel_file_id_card(file_path):
    """
    检查单个Excel文件中身份证号列的数据类型
    """
    print(f"\n=== 检查文件: {file_path} ===")
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None
    
    try:
        # 读取Excel文件
        df = read_excel(file_path)
        if df is None:
            print(f"无法读取文件: {file_path}")
            return None
        
        # 检查身份证号列
        result = check_id_card_column(df)
        
        if 'error' in result:
            print(f"错误: {result['error']}")
            print(f"可用列: {result['available_columns']}")
        else:
            print(f"列名: {result['column_name']}")
            print(f"数据类型: {result['data_type']}")
            print(f"样本数据: {result['sample_data']}")
            print(f"科学记数法数量: {result['scientific_notation_count']}")
            print(f"空值数量: {result['null_count']}")
            print(f"总行数: {result['total_rows']}")
            print(f"是否存在科学记数法: {result['has_scientific_notation']}")
            
            # 如果存在科学记数法，显示详细信息
            if result['has_scientific_notation']:
                print("\n⚠️  警告：发现科学记数法格式的身份证号！")
                print("这些身份证号可能被错误地转换为数字格式。")
                print("建议检查原始Excel文件中的数据格式。")
        
        return result
        
    except Exception as e:
        print(f"检查文件时出错: {e}")
        return None

def check_directory_excel_files(directory_path):
    """
    检查目录中所有Excel文件的身份证号列
    """
    print(f"\n=== 检查目录: {directory_path} ===")
    
    if not os.path.exists(directory_path):
        print(f"目录不存在: {directory_path}")
        return
    
    excel_files = []
    for file in os.listdir(directory_path):
        if file.endswith(('.xlsx', '.xls')):
            excel_files.append(os.path.join(directory_path, file))
    
    if not excel_files:
        print(f"目录中没有找到Excel文件: {directory_path}")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件:")
    for file in excel_files:
        print(f"  - {os.path.basename(file)}")
    
    results = {}
    for file_path in excel_files:
        result = check_excel_file_id_card(file_path)
        if result:
            results[file_path] = result
    
    return results

def main():
    """
    主函数：检查项目中的Excel文件
    """
    print("身份证号列数据类型检查工具")
    print("=" * 50)
    
    # 检查当前目录
    current_dir = os.getcwd()
    print(f"当前目录: {current_dir}")
    
    # 检查当前目录中的Excel文件
    current_results = check_directory_excel_files(current_dir)
    
    # 检查上级目录中的Excel文件
    parent_dir = os.path.dirname(current_dir)
    parent_results = check_directory_excel_files(parent_dir)
    
    # 检查uploads目录
    uploads_dir = os.path.join(parent_dir, 'uploads')
    uploads_results = check_directory_excel_files(uploads_dir)
    
    # 总结报告
    print("\n" + "=" * 50)
    print("检查总结报告")
    print("=" * 50)
    
    all_results = {}
    if current_results:
        all_results.update(current_results)
    if parent_results:
        all_results.update(parent_results)
    if uploads_results:
        all_results.update(uploads_results)
    
    if all_results:
        scientific_notation_files = []
        normal_files = []
        
        for file_path, result in all_results.items():
            if 'error' not in result:
                if result.get('has_scientific_notation', False):
                    scientific_notation_files.append(file_path)
                else:
                    normal_files.append(file_path)
        
        print(f"\n总共检查了 {len(all_results)} 个文件:")
        print(f"  - 正常格式文件: {len(normal_files)} 个")
        print(f"  - 包含科学记数法文件: {len(scientific_notation_files)} 个")
        
        if scientific_notation_files:
            print("\n⚠️  需要关注的文件（包含科学记数法格式身份证号）:")
            for file_path in scientific_notation_files:
                print(f"  - {os.path.basename(file_path)}")
            print("\n建议：")
            print("1. 检查这些Excel文件中身份证号列的格式")
            print("2. 确保身份证号以文本格式存储")
            print("3. 重新保存文件时选择'文本'格式")
        else:
            print("\n✅ 所有文件的身份证号列格式正常！")
    else:
        print("没有找到任何Excel文件进行检查。")

if __name__ == "__main__":
    main() 