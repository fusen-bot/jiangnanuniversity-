import pdfplumber
import pandas as pd
import re

def extract_author_info(pdf_path: str):
    """提取通信作者信息"""
    papers_info = []
    
    # 加载员工数据
    employee_file = '/Users/changfusheng/Desktop/学报/PY_AUTO/data/在职员工.xlsx'
    retired_file = '/Users/changfusheng/Desktop/学报/PY_AUTO/data/退休员工.xlsx'
    
    try:
        employee_df = pd.read_excel(employee_file)
        retired_df = pd.read_excel(retired_file)
        combined_df = pd.concat([employee_df, retired_df])
        # 确保工号为整数类型
        combined_df['工号'] = pd.to_numeric(combined_df['工号'], errors='coerce').fillna(0).astype(int)
    except Exception as e:
        print(f"加载员工数据失败: {str(e)}")
        combined_df = pd.DataFrame()
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # 从第5页开始查找（跳过目录等前置页面）
            for page_num in range(0, len(pdf.pages)):
                print(f"\n正在处理第 {page_num + 1} 页...")
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                # 查找通信作者标记的几种可能模式
                patterns = [
                    r'\*\s*通[讯信]作者[:：].*?(?=\n|$)',  # *通信作者：xxx
                    r'†\s*通[讯信]作者[:：].*?(?=\n|$)',   # †通信作者：xxx
                    r'通[讯信]作者[：:]\s*[\u4e00-\u9fa5]+',  # 通信作者：xxx（中文名）
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        author_line = match.group(0)
                        print(f"\n找到通信作者行: {author_line}")
                        

                        # 提取稿件编号，一般在本页的顶部前 5 行会出现DOI：10.12441/spyswjs.20240318003，这个是稿件编号就是20240318003
                        manuscript_id = ''
                        fee_eligible = True  # 是否发稿费，默认发稿费
                        
                        # 获取当前页面的前5行来查找DOI
                        lines = text.split('\n')
                        for i, line in enumerate(lines[:5]):  # 只检查前5行
                            # 查找DOI模式：DOI：10.12441/spyswjs.20240318003
                            doi_match = re.search(r'DOI[：:]\s*10\.12441/spyswjs\.(\d+)', line)
                            if doi_match:
                                manuscript_id = doi_match.group(1)
                                print(f"找到稿件编号: {manuscript_id}")
                                
                                # 检查是否为2025年及以后的稿件
                                if manuscript_id.startswith('2025') or manuscript_id.startswith('2026') or manuscript_id.startswith('2027'):
                                    fee_eligible = False
                                    print(f"稿件编号 {manuscript_id} 为2025年及以后，标记不发稿费")
                                break

                        # 提取作者姓名
                        author = ''
                        author_match = re.search(r'者[：:]\s*([\u4e00-\u9fa5]+)', author_line)
                        if author_match:
                            author = author_match.group(1).strip()
                        
                        # 提取邮箱（处理可能跨行的情况）
                        email = ''
                        # 获取当前页面的所有行
                        lines = text.split('\n')
                        
                        # 遍历每一行寻找可能的邮箱部分
                        for i, line in enumerate(lines):
                            # 检查是否有以-或‐结尾的行
                            if line.rstrip().endswith(('-', '‐')):
                                # 移除结尾的-或‐，与下一行合并
                                if i + 1 < len(lines):
                                    combined_line = line.rstrip()[:-1] + lines[i + 1].strip()
                                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', combined_line)
                                    if email_match:
                                        email = email_match.group(0)
                                        break
                            
                            # 检查是否有以.或@结尾的行
                            elif line.rstrip().endswith(('.', '@')):
                                # 直接与下一行合并
                                if i + 1 < len(lines):
                                    combined_line = line.rstrip() + lines[i + 1].strip()
                                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', combined_line)
                                    if email_match:
                                        email = email_match.group(0)
                                        break
                            
                            # 检查当前行是否包含完整邮箱
                            else:
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', line)
                                if email_match:
                                    email = email_match.group(0)
                                    break
                        
                        # 提取单位（查找页面中的括号内容，支持跨行）
                        affiliation = ''
                        lines = text.split('\n')
                        for i, line in enumerate(lines):
                            # 检查当前行是否包含未闭合的括号
                            if ('（' in line or '(' in line) and ('）' not in line and ')' not in line):
                                # 尝试与下一行组合
                                if i + 1 < len(lines):
                                    combined_line = line + lines[i + 1].strip()
                                    aff_match = re.search(r'[（\(](.*?(?:大学|研究所|研究院|学院).*?)[\)）]', combined_line)
                                    if aff_match:
                                        affiliation = aff_match.group(1)
                                        break
                            
                            # 检查当前行是否包含完整的括号内容
                            elif '（' in line or '(' in line:
                                aff_match = re.search(r'[（\(](.*?(?:大学|研究所|研究院|学院).*?)[\)）]', line)
                                if aff_match:
                                    affiliation = aff_match.group(1)
                                    break
                        
                        if author:  # 只有当找到作者时才添加记录
                            is_internal = '江南大学' in affiliation
                            employee_id = ''
                            
                            # 如果是校内作者,查找工号
                            if is_internal and not combined_df.empty:
                                employee_match = combined_df[combined_df['姓名'] == author]
                                if not employee_match.empty:
                                    employee_id = str(employee_match.iloc[0]['工号'])
                            
                            print(f"找到信息：作者={author}, 单位={affiliation}, 邮箱={email}, 工号={employee_id}, 稿件编号={manuscript_id}, 发稿费={'是' if fee_eligible else '否'}")
                            
                            papers_info.append({
                                '序号': len(papers_info) + 1,
                                '稿件编号': manuscript_id,
                                '通信作者': author,
                                '单位': affiliation,
                                '邮箱': email,
                                '工号': employee_id,
                                '是否校内': '是' if is_internal else '否',
                                '是否发稿费': '是' if fee_eligible else '否',
                                '金额': '0' if not fee_eligible else '150'  # 根据是否发稿费设置金额
                            })
    
        print(f"\n总共找到 {len(papers_info)} 条记录")
        if not papers_info:
            print("警告：未找到任何通信作者信息！")
            # 打印几页的内容用于调试
            for i in range(min(3, len(pdf.pages))):
                print(f"\n第{i+1}页内容预览：")
                print(pdf.pages[i].extract_text()[:300])
        
        return papers_info
    
    except Exception as e:
        print(f"处理PDF时发生错误: {str(e)}")
        return []

def create_excel_report(papers_info, output_path):
    """生成Excel报告"""
    try:
        if not papers_info:
            print("没有找到任何作者信息！")
            return
        
        # 创建DataFrame
        df = pd.DataFrame(papers_info)
        print("\n提取的数据预览:")
        print(df)
        
        # 计算统计信息
        total = len(df)
        internal = len(df[df['是否校内'] == '是'])
        external = len(df[df['是否校内'] == '否'])
        fee_eligible = len(df[df['是否发稿费'] == '是'])
        fee_not_eligible = len(df[df['是否发稿费'] == '否'])
        
        # 创建统计信息
        stats_df = pd.DataFrame({
            '统计项': ['总论文数', '校内作者数', '校外作者数', '发稿费论文数', '不发稿费论文数'],
            '数量': [total, internal, external, fee_eligible, fee_not_eligible],
            '百分比': ['100%', f'{(internal/total)*100:.1f}%', f'{(external/total)*100:.1f}%', f'{(fee_eligible/total)*100:.1f}%', f'{(fee_not_eligible/total)*100:.1f}%']
        })
        
        # 保存到Excel
        with pd.ExcelWriter(output_path) as writer:
            df.to_excel(writer, sheet_name='详细数据', index=False)
            stats_df.to_excel(writer, sheet_name='统计概要', index=False)
        
        print(f"\n统计完成：")
        print(f"总论文数: {total}")
        print(f"校内作者: {internal}")
        print(f"校外作者: {external}")
        print(f"发稿费论文数: {fee_eligible}")
        print(f"不发稿费论文数: {fee_not_eligible}")
        
    except Exception as e:
        print(f"生成Excel报告时发生错误: {str(e)}")

def main():
    # 设置文件路径
    pdf_path = "/Users/changfusheng/Desktop/学报/PY_AUTO/uploads/食品与生物技术学报2024年9期_付印_H.pdf"
    
    # 从 PDF 路径中提取文件名
    pdf_filename = pdf_path.split('/')[-1].replace('.pdf', '')
    output_path = f"/Users/changfusheng/Desktop/学报/PY_AUTO/output/{pdf_filename}_统计结果.xlsx"
    
    print("开始提取作者信息...")
    papers_info = extract_author_info(pdf_path)
    
    if papers_info:
        print("\n生成Excel报告...")
        create_excel_report(papers_info, output_path)
        print(f"\n处理完成！结果已保存至：{output_path}")
    else:
        print("未能提取到任何作者信息，请检查PDF格式或路径是否正确。")

if __name__ == "__main__":
    main()
