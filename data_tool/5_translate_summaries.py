# /BookRecommendSystem/5_translate_summaries.py
import concurrent.futures

from app import create_app, db
from app.models import Book
from deep_translator import GoogleTranslator
import time

# --- 1. 在脚本顶部定义代理 (请替换成您自己的端口号) ---
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 7890  # 这是一个示例端口，请务必替换为您自己找到的真实端口号！
# 并发数量，可以根据你的网络情况调整，建议从5开始
MAX_WORKERS = 10


proxies = {
    'http': f'http://{PROXY_HOST}:{PROXY_PORT}',
    'https': f'http://{PROXY_HOST}:{PROXY_PORT}',  # HTTPS请求通常也通过同一个HTTP代理地址
}


def translate_task(book_info):
    """
    单个翻译任务，将在一个独立的线程中运行
    接收一个字典，返回一个结果字典，避免线程间共享数据库对象
    """
    book_id = book_info['id']
    summary_to_translate = book_info['summary']

    print(f"  线程启动: 开始翻译 book_id {book_id}...")
    try:
        translator = GoogleTranslator(source='en', target='zh-CN', proxies=proxies)
        # 截取前4800个字符以符合API限制
        translated_text = translator.translate(summary_to_translate[:4800])
        if translated_text:
            print(f"  ✅ 翻译成功: book_id {book_id}")
            return {'id': book_id, 'summary_zh': translated_text}
    except Exception as e:
        print(f"  ❌ 翻译失败: book_id {book_id}, 错误: {e}")

    return None


def main():
    """主函数"""
    app = create_app()
    app.app_context().push()

    books_to_translate = Book.query.filter(
        Book.summary.isnot(None),
        Book.summary_zh.is_(None)
    ).all()

    total = len(books_to_translate)
    if total == 0:
        print("没有需要翻译的书籍。")
        return

    print(f"任务开始：共找到 {total} 本书需要翻译简介，将使用 {MAX_WORKERS} 个并发线程。")

    # 创建一个简单的字典列表，用于传递给线程，避免数据库会话问题
    tasks = [{'id': book.id, 'summary': book.summary} for book in books_to_translate]

    success_count = 0

    # 使用线程池执行器
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # map() 会自动将tasks列表中的每一项分配给一个线程去执行 translate_task 函数
        results = executor.map(translate_task, tasks)

        # 循环处理返回的结果
        for result in results:
            if result:
                # 在主线程中安全地更新数据库
                book_to_update = Book.query.get(result['id'])
                if book_to_update:
                    book_to_update.summary_zh = result['summary_zh']
                    success_count += 1

                # 每成功翻译10本书，就提交一次数据库，以保存进度
                if success_count % 10 == 0:
                    db.session.commit()
                    print(f"--- 进度已保存：{success_count}/{total} ---")

    # 提交剩余的更改
    db.session.commit()
    print(f"\n翻译任务完成！总共成功翻译了 {success_count} / {total} 本书的简介。")


if __name__ == '__main__':
    main()