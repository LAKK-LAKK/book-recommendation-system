import pymysql
import random
from snownlp import SnowNLP

# --- 数据库配置 (与之前相同) ---
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'LAKK001',
    'database': 'douban_book_recommendation',
    'charset': 'utf8mb4'
}

# --- 评论语法字典 (核心) ---
# 学生可以尽情扩充这个字典，增加多样性！
COMMENT_GRAMMAR = {
    "positive": {
        "opening": ["刚读完，感觉", "不得不说，", "这本书", "《{book_title}》", "整体来看，"],
        "aspect": {
            "情节": ["情节很棒", "故事线很吸引人", "叙事节奏恰到好处", "情节设计得太巧妙了"],
            "人物": ["人物塑造非常立体", "主角形象很丰满", "每个角色都令人印象深刻", "人物关系处理得很好"],
            "文笔": ["作者文笔流畅优美", "文字功底深厚", "语言风格我很喜欢", "描写非常细腻"],
            "思想": ["思想深刻，引人深思", "给了我很多启发", "世界观设定很宏大", "充满了智慧和洞见"],
        },
        "closing": ["，强烈推荐！", "，绝对是年度佳作。", "，值得每个爱书的人阅读。", "，会推荐给朋友们。", "，让人回味无穷。"]
    },
    "negative": {
        "opening": ["坦白说，有点失望，", "读完感觉很一般，", "这本书", "《{book_title}》", "期望太高了，结果"],
        "aspect": {
            "情节": ["情节有点拖沓", "故事线太老套了", "叙事节奏很奇怪", "剧情发展莫名其妙"],
            "人物": ["人物塑造得有点扁平", "主角形象立不起来", "角色动机很模糊", "感觉是工具人"],
            "文笔": ["作者的文笔比较晦涩", "文字太啰嗦了", "语言风格很枯燥", "描写不够生动"],
            "思想": ["思想内核比较空洞", "没什么新意", "观点有些陈词滥调", "逻辑上有些硬伤"],
        },
        "closing": ["，不太推荐。", "，感觉浪费了时间。", "，不会再读第二遍了。", "，拔草了。", "，远没有传说中那么好。"]
    },
    "conjunction": ["，而且", "，并且", "，同时", "。另外，"]
}


def generate_single_comment(book_title):
    """
    使用组合文法生成一条随机评论
    """
    # 75%的概率生成纯粹的好评或差评，25%生成混合评价
    if random.random() < 0.75:
        # --- 生成纯粹评价 ---
        sentiment_type = "positive" if random.random() > 0.3 else "negative"  # 70%好评
        grammar = COMMENT_GRAMMAR[sentiment_type]

        # 随机选择1-2个方面进行评论
        num_aspects = random.randint(1, 2)
        selected_aspects_keys = random.sample(list(grammar["aspect"].keys()), num_aspects)

        comment_parts = [random.choice(grammar["opening"])]

        # 拼接评论
        for i, key in enumerate(selected_aspects_keys):
            comment_parts.append(random.choice(grammar["aspect"][key]))
            if i < num_aspects - 1:  # 如果不是最后一个方面，加连接词
                comment_parts.append(random.choice(COMMENT_GRAMMAR["conjunction"]))

        comment_parts.append(random.choice(grammar["closing"]))

    else:
        # --- 生成混合评价 (e.g., "文笔很好，但是情节太差了") ---
        pos_grammar = COMMENT_GRAMMAR["positive"]
        neg_grammar = COMMENT_GRAMMAR["negative"]

        # 随机选择一个正面和一个负面方面
        pos_key = random.choice(list(pos_grammar["aspect"].keys()))
        neg_key = random.choice(list(neg_grammar["aspect"].keys()))

        pos_part = random.choice(pos_grammar["aspect"][pos_key])
        neg_part = random.choice(neg_grammar["aspect"][neg_key])

        # 随机组合顺序
        if random.random() > 0.5:
            comment_parts = [pos_part, "，但是", neg_part, "。"]
        else:
            comment_parts = [neg_part, "，但好在", pos_part, "。"]

    # 替换书名占位符并拼接成最终字符串
    final_comment = "".join(comment_parts)
    return final_comment.format(book_title=book_title)


def generate_comments_main():
    """主函数，执行用户创建和评论生成"""
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # --- 步骤1: 创建或获取具有详细信息的模拟用户 ---
        print("正在创建或加载具有详细信息的模拟用户...")
        users_to_create = [
            {'username': '爱读书的小明', 'age': 25, 'gender': '男'},
            {'username': '文艺青年小红', 'age': 22, 'gender': '女'},
            {'username': '路人甲', 'age': 30, 'gender': '保密'},
            {'username': '书虫小刚', 'age': 19, 'gender': '男'},
            {'username': '评论家小李', 'age': 45, 'gender': '男'},
            {'username': '深夜书房', 'age': None, 'gender': '保密'},
            {'username': 'kindle不离手', 'age': 28, 'gender': '女'}
        ]

        user_ids = []
        for user_data in users_to_create:
            username = user_data['username']
            try:
                # 为新用户生成模拟数据
                # 注意：在真实应用中，密码哈希应由后端框架（如Flask+Werkzeug）生成
                password_hash = 'placeholder_hash_for_testing_purpose'
                email = f'{username}@example.com'  # 生成一个唯一的模拟邮箱

                sql = """
                INSERT INTO users (username, password_hash, email, gender, age) 
                VALUES (%s, %s, %s, %s, %s)
                """
                params = (username, password_hash, email, user_data['gender'], user_data['age'])
                cursor.execute(sql, params)
                user_ids.append(cursor.lastrowid)

            except pymysql.err.IntegrityError:
                # 如果用户已存在，就查询出他的ID
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                user_ids.append(cursor.fetchone()[0])

        connection.commit()
        print(f"创建或加载了 {len(user_ids)} 个用户。")

        # --- 步骤2: 获取所有图书 (此部分及后续代码保持不变) ---
        cursor.execute("SELECT id, title FROM books")
        books = cursor.fetchall()
        if not books:
            print("错误：数据库中没有图书，请先运行 `1_import_books.py`。")
            return

        print(f"准备为 {len(books)} 本书生成大量评论...")

        # --- 步骤3: 循环生成并插入评论 (此部分及后续代码保持不变) ---
        TOTAL_COMMENTS_TO_GENERATE = 20000

        insert_count = 0
        for i in range(TOTAL_COMMENTS_TO_GENERATE):
            book_id, book_title = random.choice(books)
            user_id = random.choice(user_ids)
            comment_text = generate_single_comment(book_title)
            sentiment_score = SnowNLP(comment_text).sentiments

            sql = "INSERT INTO comments (book_id, user_id, content, sentiment_score) VALUES (%s, %s, %s, %s)"
            params = (book_id, user_id, comment_text, sentiment_score)
            cursor.execute(sql, params)
            insert_count += 1

            if (i + 1) % 500 == 0:
                print(f"已生成 {i + 1} / {TOTAL_COMMENTS_TO_GENERATE} 条评论...")

        connection.commit()
        print(f"\n评论生成完毕！总共创建了 {insert_count} 条多样化的评论。")

    except pymysql.MySQLError as e:
        print(f"数据库连接或操作失败: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == '__main__':
    generate_comments_main()