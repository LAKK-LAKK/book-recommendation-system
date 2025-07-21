# /BookRecommendSystem/fetch_summaries_api.py (代理优化版)

import requests
import time
import random
from app import create_app, db
from app.models import Book

# --- 1. 在脚本顶部定义代理 (请替换成您自己的端口号) ---
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 7890  # 这是一个示例端口，请务必替换为您自己找到的真实端口号！

proxies = {
    'http': f'http://{PROXY_HOST}:{PROXY_PORT}',
    'https': f'http://{PROXY_HOST}:{PROXY_PORT}',  # HTTPS请求通常也通过同一个HTTP代理地址
}
# ----------------------------------------------------

API_ENDPOINT = "https://openlibrary.org/api/books"
BATCH_SIZE = 40


def get_summary_from_response(data, isbn):
    """从API的JSON响应中解析出简介文本 (此函数保持不变)"""
    # ... (代码省略，保持不变)
    book_key = f"ISBN:{isbn}"
    if not data or book_key not in data:
        return None
    book_data = data[book_key]
    if 'description' in book_data:
        desc = book_data['description']
        return desc['value'] if isinstance(desc, dict) and 'value' in desc else desc
    if 'notes' in book_data:
        notes = book_data['notes']
        return notes['value'] if isinstance(notes, dict) and 'value' in notes else notes
    if 'first_sentence' in book_data:
        fs = book_data['first_sentence']
        return fs['value'] if isinstance(fs, dict) and 'value' in fs else fs
    return None


def fetch_book_summaries_batch():
    """主函数，批量获取并更新图书简介"""
    app = create_app()
    app.app_context().push()

    books_to_update = Book.query.filter(Book.isbn.isnot(None)).all()
    total_books = len(books_to_update)
    print(f"任务开始：共找到 {total_books} 本书需要获取简介。将通过代理 {PROXY_HOST}:{PROXY_PORT} 进行处理。")
    total_batchs = total_books//BATCH_SIZE

    for i in range(7814, total_books, BATCH_SIZE):
        batch_books = books_to_update[i:i + BATCH_SIZE]
        isbn_list = [str(book.isbn).strip() for book in batch_books if str(book.isbn).strip()]
        if not isbn_list:
            continue
        bibkeys_str = ",".join([f"ISBN:{isbn}" for isbn in isbn_list])
        params = {'bibkeys': bibkeys_str, 'jscmd': 'data', 'format': 'json'}

        print(f"\n正在处理批次 {i // BATCH_SIZE + 1}/{total_batchs}...")

        try:
            # --- 2. 在requests请求中加入proxies参数 ---
            response = requests.get(API_ENDPOINT, params=params, timeout=30, proxies=proxies)
            # -------------------------------------------

            if response.status_code == 200:
                # ... (后续处理逻辑保持不变)
                response_data = response.json()
                for book in batch_books:
                    summary = get_summary_from_response(response_data, str(book.isbn).strip())
                    if summary:
                        book.summary = summary
                        print(f"  ✅ 成功获取《{book.title}》的简介。")
                db.session.commit()
                print(f"批次 {i // BATCH_SIZE + 1} 处理完毕并已保存到数据库。")
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求异常: {e}")

        time.sleep(random.uniform(0.5, 1.0))

    print("\n所有书籍已处理完毕！")


if __name__ == '__main__':
    fetch_book_summaries_batch()