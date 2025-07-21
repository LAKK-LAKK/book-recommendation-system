# /BookRecommendSystem/config.py
import os

# 引入一个库来加载.env文件
from dotenv import load_dotenv

# 获取项目根目录
basedir = os.path.abspath(os.path.dirname(__file__))
# 加载.env文件
load_dotenv(os.path.join(basedir, '../.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-hard-to-guess-string'

    # --- 从环境变量中读取数据库URI ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:LAKK001@127.0.0.1:3306/douban_book_recommendation'

    SQLALCHEMY_TRACK_MODIFICATIONS = False