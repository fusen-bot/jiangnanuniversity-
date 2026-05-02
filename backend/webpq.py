import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import json
import re
import time
import logging
from queue import Queue
from urllib.parse import urljoin
from multiprocessing import Process, Queue as MPQueue
from pdf2image import convert_from_path
import shutil

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置
BASE_URL = "http://spyswjs.cnjournals.com"
BROWSER_ISSUE_URL = f"{BASE_URL}/spyswjs/issue/browser"
DOWNLOAD_DIR = "downloads"
PROCESSED_DIR = "processed"
DB_NAME = "journal_articles.db"
MAX_RETRIES = 3
DELAY = 2  # 请求间隔增加到2秒
DOWNLOAD_TIMEOUT = 60  # 下载超时时间设置为60秒（1分钟）

# 创建下载和处理目录
for directory in [DOWNLOAD_DIR, PROCESSED_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_db_connection():
    """创建并返回一个新的数据库连接"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_soup(url, retries=MAX_RETRIES):
    """获取BeautifulSoup对象"""
    for _ in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {e}")
            time.sleep(DELAY)
    return None

def get_years_and_issues():
    """获取所有年份和期数信息"""
    soup = get_soup(BROWSER_ISSUE_URL)
    if not soup:
        return {}

    # 查找包含 JSON 数据的脚本标签
    script_tag = soup.find('script', string=re.compile('var strAllIssueJson'))
    if not script_tag:
        logger.error("未找到包含期刊信息的脚本标签")
        return {}

    # 提取 JSON 字符串
    json_str = re.search(r'var strAllIssueJson="(.+?)";', script_tag.string)
    if not json_str:
        logger.error("未能从脚本中提取 JSON 字符串")
        return {}

    try:
        # 解析 JSON 数据
        json_data = json_str.group(1).replace('\\', '')
        data = json.loads(json_data)
        years_issues = {}
        for year in data['years']:
            if year['year_id'] == '2023':
                years_issues['2023'] = [issue['cn_name'] for issue in year['issues']]
                break

        logger.info(f"获取到的2023年期数信息: {years_issues}")
        return years_issues
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析错误: {e}")
        return {}
    except KeyError as e:
        logger.error(f"JSON 结构不符合预期: {e}")
        return {}

def get_article_details(article_id):
    """获取文章详细信息"""
    url = f"{BASE_URL}/spyswjs/article/abstract/{article_id}?st=article_issue"
    logger.info(f"正在获取文章详情: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"无法获取文章详情页面: {url}, 状态码: {response.status_code}")
        return None

    logger.info(f"成功获取文章详情页面: {url}")
    
    # 查找包含作者信息的JavaScript变量
    author_json_match = re.search(r'var strAuthorsJson\s*=\s*"(.+?)";', response.text)
    if author_json_match:
        logger.info("找到作者信息JSON")
        # 提取JSON字符串但不解码
        raw_json_str = author_json_match.group(1)
        logger.info(f"提取的原始JSON字符串: {raw_json_str}")
        
        try:
            # 尝试修复JSON字符串
            fixed_json_str = raw_json_str.replace('\\"', '"').replace('\\\\', '\\')
            logger.info(f"修复后的JSON字符串: {fixed_json_str}")
            
            # 解析修复后的JSON
            author_data = json.loads(fixed_json_str)
            logger.info(f"成功解析JSON数据")
            
            authors = author_data.get('authors', [])
            logger.info(f"解析到的作者数量: {len(authors)}")
            
            is_internal = any("江南大学" in author.get('cn_institution', '') for author in authors)
            
            if authors:
                main_author = authors[0]  # 使用第一个作者作为主要作者
                logger.info(f"主要作者信息: 名字={main_author['cn_name']}, 单位={main_author['cn_institution']}")
                all_authors = [{
                    "name": author['cn_name'],
                    "affiliation": author['cn_institution']
                } for author in authors]
                logger.info(f"所有作者信息: {json.dumps(all_authors, ensure_ascii=False)}")
                return {
                    "author_name": main_author['cn_name'],
                    "is_internal": is_internal,
                    "all_authors": all_authors
                }
            else:
                logger.warning(f"未找到作者信息: {url}")
        except Exception as e:
            logger.error(f"解析作者JSON数据失败: {url}, 错误: {str(e)}")
    else:
        logger.warning(f"未找到作者信息JSON: {url}")
    
    return None

def get_articles(year, issue, pdf_queue):
    """获取指定年份和期数的文章信息并下载PDF"""
    # 计算卷数
    volume = 42 - (2023 - int(year))
    # 从issue中提取数字
    issue_number = ''.join(filter(str.isdigit, issue))
    
    url = f"{BASE_URL}/spyswjs/article/issue/{year}_{volume}_{issue_number}"
    logger.info(f"正在获取文章信息: {url}")
    soup = get_soup(url)
    if not soup:
        logger.error(f"无法获取页面内容: {url}")
        return []

    articles = []
    article_list = soup.find('div', class_='article_list')
    if article_list:
        logger.info(f"找到文章列表元素")
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            for article in article_list.find_all('li', class_='article_line'):
                title_elem = article.find('div', class_='article_title')
                pdf_elem = article.find('a', class_='btn_pdf')
                if title_elem and pdf_elem:
                    title = title_elem.text.strip()
                    pdf_link = urljoin(BASE_URL, pdf_elem['href'])
                    
                    # 提取稿件编号
                    article_id = title_elem.find('a')['href'].split('/')[-1].split('?')[0]
                    
                    # 获取文章详细信息
                    article_details = get_article_details(article_id)
                    
                    logger.info(f"找到文章: {title}, 稿件编号: {article_id}")
                    
                    # 下载PDF
                    local_path = download_pdf(pdf_link, title, pdf_queue)
                    if local_path:
                        if article_details:
                            article_info = {
                                "title": title,
                                "pdf_link": pdf_link,
                                "local_path": local_path,
                                "article_id": article_id,
                                "author_name": article_details['author_name'],
                                "is_internal": article_details['is_internal'],
                                "all_authors": article_details['all_authors']
                            }
                            articles.append(article_info)
                            logger.info(f"成功下载PDF: {local_path}")
                            
                            # 将PDF信息添加到队列中
                            pdf_queue.put((local_path, article_details['is_internal'], article_id, title))
                            
                            try:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO articles 
                                    (title, pdf_link, local_path, year, issue, article_id, author_name, is_internal) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (title, pdf_link, local_path, year, issue, article_id, 
                                      article_info['author_name'], article_info['is_internal']))
                                conn.commit()
                                logger.info(f"成功将文章信息插入数据库: {title}")
                            except Exception as e:
                                logger.error(f"插入数据库时出错: {e}")
                        else:
                            logger.warning(f"未找到作者信息: {title}")
                    else:
                        logger.warning(f"无法下载PDF: {title}")
                    
                    time.sleep(DELAY)  # 每下载一篇文章后等待
                else:
                    logger.warning(f"文章元素不完整: title_elem={bool(title_elem)}, pdf_elem={bool(pdf_elem)}")
        except Exception as e:
            logger.error(f"处理文章列表时出错: {e}")
        finally:
            conn.close()
    else:
        logger.warning("未找到文章列表元素")
    
    logger.info(f"总共找到并下载了 {len(articles)} 篇文章")
    return articles

def sanitize_filename(filename):
    """处理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def process_pdf(pdf_queue, year, issue):
    """处理PDF文件，只保留第一页并转换为PNG，然后移动到对应的年份和期数文件夹"""
    issue_dir = os.path.join(PROCESSED_DIR, f"{year}_{issue}")
    if not os.path.exists(issue_dir):
        os.makedirs(issue_dir)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        while True:
            pdf_info = pdf_queue.get()
            if pdf_info is None:
                break
            
            # 修复：确保 pdf_info 包含正确数量的元素
            if len(pdf_info) != 4:
                logger.error(f"无效的 PDF 信息: {pdf_info}")
                continue
            
            pdf_path, is_internal, article_id, title = pdf_info
            
            try:
                # 转换PDF第一页为PNG
                internal_status = "校内" if is_internal else "校外"
                sanitized_title = sanitize_filename(title)
                png_filename = f"{internal_status}_{article_id}_{sanitized_title}.png"
                temp_png_path = os.path.join(PROCESSED_DIR, png_filename)
                images = convert_from_path(pdf_path, first_page=1, last_page=1)
                if images:
                    images[0].save(temp_png_path, 'PNG')
                    
                    # 移动PNG文件到对应的年份和期数文件夹
                    final_png_path = os.path.join(issue_dir, png_filename)
                    shutil.move(temp_png_path, final_png_path)
                    
                    logger.info(f"已处理PDF并保存为PNG: {final_png_path}")
                    
                    # 更新数据库中的本地路径
                    cursor.execute("""
                        UPDATE articles 
                        SET local_path = ? 
                        WHERE article_id = ?
                    """, (final_png_path, article_id))
                    conn.commit()
                    
                    # 删除原PDF文件
                    os.remove(pdf_path)
                    logger.info(f"已删除原PDF文件: {pdf_path}")
                else:
                    logger.warning(f"无法处理PDF: {pdf_path}")
            except Exception as e:
                logger.error(f"处理PDF时出错: {pdf_path}, 错误: {e}")
    finally:
        conn.close()

def download_pdf(url, filename, pdf_queue, retries=MAX_RETRIES):
    """下载PDF文件"""
    sanitized_filename = sanitize_filename(filename)
    local_path = os.path.join(DOWNLOAD_DIR, f"{sanitized_filename}.pdf")
    
    if os.path.exists(local_path):
        logger.info(f"文件已存在，跳过下载: {local_path}")
        pdf_queue.put(local_path)
        return local_path

    for _ in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"下载成功: {local_path}")
            pdf_queue.put(local_path)
            return local_path
        except requests.RequestException as e:
            logger.error(f"下载失败: {url}, 错误: {e}")
            time.sleep(DELAY)
    
    return None

def worker(queue):
    """工作线程函数"""
    while True:
        item = queue.get()
        if item is None:
            break
        title, pdf_link, year, issue = item
        local_path = download_pdf(pdf_link, title)
        if local_path:
            cursor.execute("INSERT OR REPLACE INTO articles VALUES (?, ?, ?, ?, ?)",
                           (title, pdf_link, local_path, year, issue))
            conn.commit()
        queue.task_done()

def scrape_and_process_data(year, issue):
    logger.info(f"开始爬取和处理 {year} 年 {issue} 的数据")
    
    pdf_queue = MPQueue()
    pdf_process = Process(target=process_pdf, args=(pdf_queue, year, issue))
    pdf_process.start()
    
    articles = get_articles(year, issue, pdf_queue)
    
    # 等待所有PDF处理完成
    pdf_queue.put(None)
    pdf_process.join()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT title, local_path FROM articles WHERE year = ? AND issue = ?", (year, issue))
        processed_articles = cursor.fetchall()
        
        result = {
            "year": year,
            "issue": issue,
            "articles_count": len(articles),
            "processed_articles": [{"title": row['title'], "image_path": row['local_path']} for row in processed_articles]
        }
    except Exception as e:
        logger.error(f"查询处理后的文章时出错: {e}")
        result = {"error": str(e)}
    finally:
        conn.close()
    
    logger.info(f"爬虫任务完成,共处理 {len(processed_articles)} 篇文章")
    return result

def create_table():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                title TEXT,
                pdf_link TEXT,
                local_path TEXT,
                year TEXT,
                issue TEXT,
                article_id TEXT PRIMARY KEY,
                author_name TEXT,
                is_internal INTEGER
            )
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"创建表时出错: {e}")
    finally:
        conn.close()

def main():
    create_table()  # 添加这行
    year = '2023'
    issue = '第9期'
    
    result = scrape_and_process_data(year, issue)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()