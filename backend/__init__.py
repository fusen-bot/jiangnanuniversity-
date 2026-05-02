# 后端包的初始化文件

# 导入主要的模块和函数
from .main import app
from .data_processing import (
    process_review_data,
    query_by_employee_id,
    query_by_name,
    query_by_manuscript_id_or_reviewer
)
from .database import load_employee_data
from .utils import read_excel, is_internal, match_employee_info

# 定义 __all__ 列表，控制 "from backend import *" 的行为
__all__ = [
    'app',
    'process_review_data',
    'query_by_employee_id',
    'query_by_name',
    'query_by_manuscript_id_or_reviewer',
    'load_employee_data',
    'read_excel',
    'is_internal',
    'match_employee_info'
]

# 包的元数据
__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "审稿费管理系统后端包"

# 包初始化代码
print(f"初始化审稿费管理系统后端包 (版本 {__version__})...")

# 可以在这里添加任何需要在导入包时执行的初始化代码
# 例如，设置日志记录
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("审稿费管理系统后端已初始化")

# 如果有任何全局配置或设置，也可以在这里进行
# 例如：
BASE_PATH = '/path/to/your/data/folder'  # 请替换为实际路径

# 注意：避免在__init__.py中进行耗时的操作，因为这会在每次导入包时执行
