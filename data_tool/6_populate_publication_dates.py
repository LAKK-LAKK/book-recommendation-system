# /BookRecommendSystem/6_populate_publication_dates.py

import re
from datetime import date
from app import create_app, db
from app.models import Book


def parse_date_string(text):
    """
    智能解析多种格式的日期字符串，返回一个date对象
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()
    year, month, day = None, 1, 1  # 默认月和日为1

    try:
        # 匹配 YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD 等
        match = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', text)
        if match:
            year, month, day = map(int, match.groups())
            return date(year, month, day)

        # 匹配 YYYY-MM, YYYY.MM, YYYY/MM, YYYY年M月 等
        match = re.search(r'(\d{4})[./年-](\d{1,2})', text)
        if match:
            year, month = map(int, match.groups())
            return date(year, month, day)

        # 匹配 YYYY年 或纯粹的 YYYY
        match = re.search(r'(\d{4})', text)
        if match:
            year = int(match.group(1))
            return date(year, month, day)
    except (ValueError, TypeError):
        # 如果出现无效日期（如13月32日），则忽略
        return None

    return None


def main():
    """主函数，遍历数据库并填充日期"""
    app = create_app()
    app.app_context().push()

    # 查询所有publication_date为空，但publication_time不为空的书籍
    books_to_process = Book.query.filter(
        Book.publication_time.isnot(None),
        Book.publication_date.is_(None)
    ).all()

    total = len(books_to_process)
    if total == 0:
        print("没有需要处理的书籍。")
        return

    print(f"任务开始：共找到 {total} 本书需要填充出版日期。")

    processed_count = 0
    for book in books_to_process:
        parsed_date = parse_date_string(book.publication_time)
        if parsed_date:
            book.publication_date = parsed_date
            processed_count += 1
            if processed_count % 100 == 0:
                print(f"  已处理 {processed_count}/{total} ...")

    # 一次性提交所有更改
    db.session.commit()
    print(f"\n数据清洗完成！总共成功为 {processed_count} 本书填充了规范化的出版日期。")


if __name__ == '__main__':
    main()