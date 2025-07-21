# /BookRecommendSystem/precompute_recs.py (内存优化版)

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os

from app import create_app, db
from app.models import Book

app = create_app()
app.app_context().push()

print("开始预计算推荐数据 (内存优化版)...")

# 1. 加载数据并创建用于分析的文本
print("正在加载图书数据...")
all_books = Book.query.all()
if not all_books:
    print("数据库中没有图书，退出。")
    exit()

books_data = [{
    'id': book.id,
    'text_for_tfidf': (book.title + ' ') * 2 + (book.summary_zh or book.summary or '')
} for book in all_books]
books_df = pd.DataFrame(books_data)
print(f"成功加载 {len(books_df)} 本图书。")

# 2. 计算TF-IDF向量矩阵 (这部分依然需要较多内存，但远小于相似度矩阵)
print("正在计算TF-IDF向量...")
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(books_df['text_for_tfidf'])
print("TF-IDF矩阵计算完成！")

# 3. 创建从 book_id 到 DataFrame索引 的映射 (保持不变)
indices = pd.Series(books_df.index, index=books_df['id'])

# 4. 保存“半成品”：Vectorizer模型、TF-IDF矩阵、和索引
output_dir = 'app/recommendations_data'
os.makedirs(output_dir, exist_ok=True)
print(f"正在将计算结果保存到 '{output_dir}' 目录...")

with open(os.path.join(output_dir, 'tfidf_vectorizer.pkl'), 'wb') as f:
    pickle.dump(tfidf, f)

with open(os.path.join(output_dir, 'tfidf_matrix.pkl'), 'wb') as f:
    pickle.dump(tfidf_matrix, f)

with open(os.path.join(output_dir, 'book_indices.pkl'), 'wb') as f:
    pickle.dump(indices, f)

print("成功保存 'tfidf_vectorizer.pkl', 'tfidf_matrix.pkl', 和 'book_indices.pkl'。")
print("预计算全部完成！")