# /BookRecommendSystem/app/recommendation.py (内存优化版)

import pandas as pd
import pickle
from .models import Book, Comment, db
from sqlalchemy import func
import os
# 导入我们需要的函数
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. 在应用启动时，加载新的预计算文件 ---
vectorizer = None
tfidf_matrix = None
indices = None
data_path = 'app/recommendations_data'

try:
    with open(os.path.join(data_path, 'tfidf_vectorizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)
    with open(os.path.join(data_path, 'tfidf_matrix.pkl'), 'rb') as f:
        tfidf_matrix = pickle.load(f)
    with open(os.path.join(data_path, 'book_indices.pkl'), 'rb') as f:
        indices = pickle.load(f)
    print("推荐系统：成功加载预计算的TF-IDF数据。")
except FileNotFoundError:
    print("推荐系统警告：找不到预计算的数据文件。推荐功能将不可用。")
    print("请先运行 'precompute_recs.py' 脚本。")


def get_recommendations(book_id, num_recommendations=6):
    """为一个给定的book_id快速生成推荐列表（内存优化版）"""
    if tfidf_matrix is None or indices is None:
        return []

    try:
        target_idx = indices[book_id]
    except KeyError:
        return []

    # --- 2. 实时、轻量级地计算相似度 ---
    # 获取目标图书的TF-IDF向量
    target_vector = tfidf_matrix[target_idx]
    # 只计算目标向量与所有其他向量的相似度，这非常快！
    cosine_sim_vector = cosine_similarity(target_vector, tfidf_matrix).flatten()
    sim_scores = list(enumerate(cosine_sim_vector))

    # --- 3. 获取情感分并计算最终得分 (这部分保持不变) ---
    sentiment_scores = db.session.query(Comment.book_id,
                                        func.avg(Comment.sentiment_score).label('avg_sentiment')).group_by(
        Comment.book_id).all()
    avg_sentiments = {book_id: float(avg) for book_id, avg in sentiment_scores}

    final_scores = []
    for index, content_sim_score in sim_scores:
        current_book_id = indices.index[index]
        if current_book_id == book_id:
            continue

        avg_sentiment = avg_sentiments.get(current_book_id, 0.5)
        final_score = (0.7 * content_sim_score) + (0.3 * avg_sentiment)
        final_scores.append({'id': current_book_id, 'score': final_score})

    # --- 4. 排序并返回结果 (这部分保持不变) ---
    sorted_recommendations = sorted(final_scores, key=lambda x: x['score'], reverse=True)
    recommended_book_ids = [rec['id'] for rec in sorted_recommendations[:num_recommendations]]

    recommended_books = Book.query.filter(Book.id.in_(recommended_book_ids)).all()

    book_map = {book.id: book for book in recommended_books}
    sorted_books = [book_map[id] for id in recommended_book_ids if id in book_map]

    return sorted_books