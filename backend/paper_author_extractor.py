import os
from pathlib import Path

import pandas as pd
import pdfplumber
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv('APP_DATA_DIR', PROJECT_ROOT / 'data')).expanduser()
OUTPUT_DIR = Path(os.getenv('APP_OUTPUT_DIR', PROJECT_ROOT / 'output')).expanduser()
INTERNAL_KEYWORDS = [keyword.strip() for keyword in os.getenv('INTERNAL_KEYWORDS', '').split(',') if keyword.strip()]


def extract_author_info(pdf_path: str):
    papers_info = []
    employee_file = DATA_DIR / '在职员工.xlsx'
    retired_file = DATA_DIR / '退休员工.xlsx'

    try:
        employee_df = pd.read_excel(employee_file)
        retired_df = pd.read_excel(retired_file)
        combined_df = pd.concat([employee_df, retired_df])
        combined_df['工号'] = pd.to_numeric(combined_df['工号'], errors='coerce').fillna(0).astype(int)
    except Exception as e:
        print(f'加载员工数据失败: {str(e)}')
        combined_df = pd.DataFrame()

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(0, len(pdf.pages)):
                print(f'\n正在处理第 {page_num + 1} 页...')
                page = pdf.pages[page_num]
                text = page.extract_text()

                patterns = [
                    r'\*\s*通[讯信]作者[:：].*?(?=\n|$)',
                    r'†\s*通[讯信]作者[:：].*?(?=\n|$)',
                    r'通[讯信]作者[：:]\s*[一-龥]+',
                ]

                for pattern in patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        author_line = match.group(0)
                        print(f'\n找到通信作者行: {author_line}')

                        manuscript_id = ''
                        fee_eligible = True
                        lines = text.split('\n')
                        for line in lines[:5]:
                            doi_match = re.search(r'DOI[：:]\s*10\.12441/spyswjs\.(\d+)', line)
                            if doi_match:
                                manuscript_id = doi_match.group(1)
                                print(f'找到稿件编号: {manuscript_id}')
                                if manuscript_id.startswith(('2025', '2026', '2027')):
                                    fee_eligible = False
                                    print(f'稿件编号 {manuscript_id} 为2025年及以后，标记不发稿费')
                                break

                        author = ''
                        author_match = re.search(r'者[：:]\s*([一-龥]+)', author_line)
                        if author_match:
                            author = author_match.group(1).strip()

                        email = ''
                        lines = text.split('\n')
                        for index, line in enumerate(lines):
                            if line.rstrip().endswith(('-', '‐')) and index + 1 < len(lines):
                                combined_line = line.rstrip()[:-1] + lines[index + 1].strip()
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', combined_line)
                                if email_match:
                                    email = email_match.group(0)
                                    break
                            elif line.rstrip().endswith(('.', '@')) and index + 1 < len(lines):
                                combined_line = line.rstrip() + lines[index + 1].strip()
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', combined_line)
                                if email_match:
                                    email = email_match.group(0)
                                    break
                            else:
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', line)
                                if email_match:
                                    email = email_match.group(0)
                                    break

                        affiliation = ''
                        lines = text.split('\n')
                        for index, line in enumerate(lines):
                            has_open_bracket = '（' in line or '(' in line
                            has_close_bracket = '）' in line or ')' in line
                            if has_open_bracket and not has_close_bracket and index + 1 < len(lines):
                                combined_line = line + lines[index + 1].strip()
                                aff_match = re.search(r'[（\(](.*?(?:大学|研究所|研究院|学院).*?)[\)）]', combined_line)
                                if aff_match:
                                    affiliation = aff_match.group(1)
                                    break
                            elif has_open_bracket:
                                aff_match = re.search(r'[（\(](.*?(?:大学|研究所|研究院|学院).*?)[\)）]', line)
                                if aff_match:
                                    affiliation = aff_match.group(1)
                                    break

                        if author:
                            is_internal = any(keyword in affiliation for keyword in INTERNAL_KEYWORDS)
                            employee_id = ''
                            if is_internal and not combined_df.empty:
                                employee_match = combined_df[combined_df['姓名'] == author]
                                if not employee_match.empty:
                                    employee_id = str(employee_match.iloc[0]['工号'])

                            print(
                                f'找到信息：作者={author}, 单位={affiliation}, 邮箱={email}, '
                                f'工号={employee_id}, 稿件编号={manuscript_id}, 发稿费={'是' if fee_eligible else '否'}'
                            )

                            papers_info.append({
                                '序号': len(papers_info) + 1,
                                '稿件编号': manuscript_id,
                                '通信作者': author,
                                '单位': affiliation,
                                '邮箱': email,
                                '工号': employee_id,
                                '是否校内': '是' if is_internal else '否',
                                '是否发稿费': '是' if fee_eligible else '否',
                                '金额': '0' if not fee_eligible else '150'
                            })

        print(f'\n总共找到 {len(papers_info)} 条记录')
        if not papers_info:
            print('警告：未找到任何通信作者信息！')
            for index in range(min(3, len(pdf.pages))):
                print(f'\n第{index + 1}页内容预览：')
                print(pdf.pages[index].extract_text()[:300])

        return papers_info
    except Exception as e:
        print(f'处理PDF时发生错误: {str(e)}')
        return []


def create_excel_report(papers_info, output_path):
    try:
        if not papers_info:
            print('没有找到任何作者信息！')
            return

        df = pd.DataFrame(papers_info)
        print('\n提取的数据预览:')
        print(df)

        total = len(df)
        internal = len(df[df['是否校内'] == '是'])
        external = len(df[df['是否校内'] == '否'])
        fee_eligible = len(df[df['是否发稿费'] == '是'])
        fee_not_eligible = len(df[df['是否发稿费'] == '否'])

        stats_df = pd.DataFrame({
            '统计项': ['总论文数', '校内作者数', '校外作者数', '发稿费论文数', '不发稿费论文数'],
            '数量': [total, internal, external, fee_eligible, fee_not_eligible],
            '百分比': [
                '100%',
                f'{(internal / total) * 100:.1f}%',
                f'{(external / total) * 100:.1f}%',
                f'{(fee_eligible / total) * 100:.1f}%',
                f'{(fee_not_eligible / total) * 100:.1f}%'
            ]
        })

        with pd.ExcelWriter(output_path) as writer:
            df.to_excel(writer, sheet_name='详细数据', index=False)
            stats_df.to_excel(writer, sheet_name='统计概要', index=False)

        print('\n统计完成：')
        print(f'总论文数: {total}')
        print(f'校内作者: {internal}')
        print(f'校外作者: {external}')
        print(f'发稿费论文数: {fee_eligible}')
        print(f'不发稿费论文数: {fee_not_eligible}')
    except Exception as e:
        print(f'生成Excel报告时发生错误: {str(e)}')


def main():
    sample_pdf_path = os.getenv('AUTHOR_SAMPLE_PDF_PATH', '')
    if not sample_pdf_path:
        print('未设置 AUTHOR_SAMPLE_PDF_PATH，跳过示例运行。')
        return

    pdf_path = Path(sample_pdf_path).expanduser()
    pdf_filename = pdf_path.stem
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f'{pdf_filename}_统计结果.xlsx'

    print('开始提取作者信息...')
    papers_info = extract_author_info(str(pdf_path))

    if papers_info:
        print('\n生成Excel报告...')
        create_excel_report(papers_info, str(output_path))
        print(f'\n处理完成！结果文件名：{output_path.name}')
    else:
        print('未能提取到任何作者信息，请检查PDF格式或路径是否正确。')


if __name__ == '__main__':
    main()
