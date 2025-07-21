import pandas as pd
import pymysql
import re

# --- 数据库配置 ---
DB_CONFIG = {
    'host': '127.0.0.1',  # 或者你的MySQL服务器IP
    'port': 3306,
    'user': 'root',  # 你的MySQL用户名
    'password': 'LAKK001',  # 你的MySQL密码
    'database': 'douban_book_recommendation',
    'charset': 'utf8mb4'
}

# --- CSV文件路径 ---
CSV_FILE_PATH = './book_douban.csv'  # 将CSV文件放在脚本同目录下


def clean_data(value):
    """一个简单的清洗函数，处理"none"和提取价格中的数字"""
    if isinstance(value, str):
        if value.strip().lower() == 'none':
            return None
        # 尝试从价格字符串中提取数字，例如 "O 14.5" -> 14.5
        match = re.search(r'[\d\.]+', value)
        if match:
            return match.group(0)
    return value


def import_books():
    """读取CSV并将数据导入到MySQL数据库"""
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        # 为了方便，重命名字段以匹配数据库列名
        df.rename(columns={
            '书名': 'title',
            '出版时间': 'publication_time',
            '数': 'pages',
            '价格': 'price',
            'ISBM': 'isbn',  # 注意CSV中可能是ISBM
            '评分': 'rating',
            '评论数量': 'review_count'
        }, inplace=True)

        # 筛选出我们需要的列
        df = df[['title', 'publication_time', 'pages', 'price', 'isbn', 'rating', 'review_count']]

        print(f"成功读取 {len(df)} 条图书数据。")

    except FileNotFoundError:
        print(f"错误：找不到CSV文件 '{CSV_FILE_PATH}'。请确保文件路径正确。")
        return

    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        print("开始向数据库导入数据...")
        insert_count = 0
        for index, row in df.iterrows():
            # 简单的去重逻辑，如果ISBN已存在则跳过
            # 在实际应用中，更好的方式是先检查
            try:
                sql = """
                INSERT INTO books (title, publication_time, pages, price, isbn, rating, review_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                # 清洗每一行的数据
                params = (
                    row['title'],
                    clean_data(row['publication_time']),
                    clean_data(row['pages']),
                    clean_data(row['price']),
                    clean_data(row['isbn']),
                    clean_data(row['rating']),
                    clean_data(row['review_count'])
                )
                cursor.execute(sql, params)
                insert_count += 1
            except pymysql.err.IntegrityError as e:
                # 忽略因ISBN重复导致的插入失败
                # print(f"跳过重复的ISBN: {row['isbn']}")
                pass
            except Exception as e:
                print(f"插入第 {index} 行数据时发生错误: {e}")

        connection.commit()
        print(f"数据导入完成！成功插入 {insert_count} 条记录。")

    except pymysql.MySQLError as e:
        print(f"数据库连接或操作失败: {e}")
    finally:
        if connection:
            connection.close()


if __name__ == '__main__':
    import_books()