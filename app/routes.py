# /BookRecommendSystem/app/routes.py
import random
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from snownlp import SnowNLP
from sqlalchemy import func, case, or_, extract # 确保 extract 也被导入
from .models import (db, User, Book, Comment, CarouselItem, Post, Reply,
                     Notification, post_likes)
from .forms import (LoginForm, RegistrationForm, CommentForm, AdminEditUserForm,
                    CarouselItemForm, PostForm, EditProfileForm, BookForm,
                    FileUploadForm, ReplyForm) # 整理了一下导入
from flask_login import login_user, logout_user, current_user, login_required
import base64
from functools import wraps
from flask import abort
import pandas as pd
import os
import io
from flask import send_file
from werkzeug.utils import secure_filename
import textwrap # 用于处理文本换行

# --- 自定义管理员权限装饰器 ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)  # 抛出403 Forbidden错误
        return f(*args, **kwargs)
    return decorated_function


main = Blueprint('main', __name__)

# ... generate_svg_cover 函数保持不变 ...
def generate_svg_cover(title):
    display_title = title[:4] if len(title) > 4 else title
    svg_template = f"""
    <svg width="200" height="260" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="#f0f0f0"/>
      <rect x="10" y="10" width="180" height="240" fill="none" stroke="#cccccc" stroke-width="2"/>
      <text x="50%" y="50%" font-family="SimHei, sans-serif" font-size="24" fill="#333" 
            text-anchor="middle" dominant-baseline="middle">{display_title}</text>
      <text x="50%" y="90%" font-family="sans-serif" font-size="12" fill="#aaa"
            text-anchor="middle">图书封面</text>
    </svg>
    """
    svg_base64 = base64.b64encode(svg_template.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{svg_base64}"


def generate_svg_cover_post(title):
    """
    生成具有多种随机主题和自动换行功能的SVG帖子封面。
    """
    title = title[:45] if len(title) > 4 else title
    # --- 1. 定义多种设计主题 ---
    themes = [
        {'bg': '#f8f9fa', 'text': '#343a40', 'font': 'SimHei, sans-serif'},
        {'bg': '#e9ecef', 'text': '#212529', 'font': 'KaiTi, serif'},
        {'bg': '#6c757d', 'text': '#ffffff', 'font': 'FangSong, sans-serif'},
        {'bg': '#343a40', 'text': '#f8f9fa', 'font': 'LiSu, cursive'},
        {'bg': '#4f9da6', 'text': '#ffffff', 'font': 'YouYuan, sans-serif'},
        {'bg': '#ffc107', 'text': '#343a40', 'font': 'SimHei, sans-serif'},
        {'bg': '#fd7e14', 'text': '#ffffff', 'font': 'KaiTi, serif'},
    ]

    # 随机选择一个主题
    theme = random.choice(themes)

    # --- 2. 智能文本换行处理 ---
    # 根据经验，一个400px宽的画布，每行大约能容纳12-15个中文字符
    wrapped_lines = textwrap.wrap(title, width=13)
    # 将换行后的文本用<br>标签连接起来
    formatted_title = '<br/>'.join(wrapped_lines)

    # 根据行数动态调整字体大小和行高，防止文字溢出
    line_count = len(wrapped_lines)
    if line_count <= 2:
        font_size = 42
        line_height = 1.5
    elif line_count == 3:
        font_size = 36
        line_height = 1.4
    else:  # 超过3行
        font_size = 30
        line_height = 1.3

    # --- 3. 生成最终的SVG代码 ---
    svg_template = f"""
    <svg width="400" height="500" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="{theme['bg']}"/>

      <foreignObject x="25" y="25" width="350" height="450">
        <div xmlns="http://www.w3.org/1999/xhtml" 
             style="display: flex; align-items: center; justify-content: center; height: 100%; text-align: center; overflow: hidden;">

          <p style="font-family: {theme['font']}; 
                    font-size: {font_size}px; 
                    color: {theme['text']}; 
                    font-weight: bold; 
                    margin: 0; 
                    line-height: {line_height};">
            {formatted_title}
          </p>

        </div>
      </foreignObject>
    </svg>
    """
    svg_base64 = base64.b64encode(svg_template.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{svg_base64}"


# /BookRecommendSystem/app/routes.py
# ... (其他导入保持不变)

@main.route('/')
@main.route('/index')
def index():
    # 1. 轮播图数据 (建议在后台设置5项以上，效果更好)
    carousel_items = CarouselItem.query.filter_by(is_active=True).order_by(CarouselItem.display_order).limit(7).all()

    # 2. 新书速递
    new_releases_raw = Book.query.filter(Book.publication_time.isnot(None)).order_by(
        Book.publication_time.desc()).limit(8).all()

    # 3. 最新入库
    latest_additions_raw = Book.query.order_by(Book.id.desc()).limit(8).all()

    # 4. 高分榜 (右侧边栏)
    order_logic = case((Book.rating.is_(None), 0), else_=1).desc()
    high_score_books = Book.query.order_by(order_logic, Book.rating.desc()).limit(10).all()

    # 5. 热搜榜 (右侧边栏) - 随机选取10本书模拟
    hot_search_books_raw = Book.query.order_by(func.random()).limit(10).all()
    # 为热搜榜书籍生成虚拟的“搜索指数”
    hot_search_books = []
    for book in hot_search_books_raw:
        hot_search_books.append({
            'book': book,
            'search_index': random.randint(100000, 999999)  # 生成6位数的随机热度
        })

    # 6. 热门标签 (右侧边栏)
    popular_tags = ['小说', '历史', '编程', '科幻', '悬疑', '经济学', '心理学', '传记']

    # --- 为需要显示封面的列表进行安全的数据预处理 ---
    def prepare_book_data(books):
        data = []
        for book in books:
            data.append({
                'id': book.id,
                'title': book.title,
                'cover_image': book.cover_image if book.cover_image else generate_svg_cover(book.title)
            })
        return data

    new_releases_data = prepare_book_data(new_releases_raw)
    latest_additions_data = prepare_book_data(latest_additions_raw)

    return render_template('index.html',
                           carousel_items=carousel_items,
                           new_releases=new_releases_data,
                           latest_additions=latest_additions_data,
                           high_score_books=high_score_books,
                           hot_search_books=hot_search_books,
                           popular_tags=popular_tags)


@main.route('/book/<int:book_id>', methods=['GET', 'POST'])
def book_detail(book_id):
    # --- 这是关键的修正：将导入语句放在函数内部 ---
    from .recommendation import get_recommendations

    book = Book.query.get_or_404(book_id)
    form = CommentForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('请先登录再发表评论。', 'warning')
            return redirect(url_for('main.login', next=request.url))
        comment = Comment(content=form.content.data, sentiment_score=SnowNLP(form.content.data).sentiments,
                          author=current_user, book_id=book.id)
        db.session.add(comment)
        db.session.commit()
        flash('您的评论已成功发表！', 'success')
        return redirect(url_for('main.book_detail', book_id=book_id))

    cover_url = book.cover_image if book.cover_image else generate_svg_cover(book.title)
    comments = book.comments.order_by(Comment.created_at.desc()).all()

    recommended_books_raw = get_recommendations(book_id)
    recommended_books_for_template = []
    for rec_book in recommended_books_raw:
        recommended_books_for_template.append({
            'id': rec_book.id,
            'title': rec_book.title,
            'cover_image': rec_book.cover_image if rec_book.cover_image else generate_svg_cover(rec_book.title)
        })

    return render_template('book_detail.html',
                           book=book,
                           comments=comments,
                           cover_image=cover_url,
                           form=form,
                           recommended_books=recommended_books_for_template)

# --- 新增路由 ---

@main.route('/register', methods=['GET', 'POST'])
def register():
    # 如果用户已登录，则重定向到首页
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # 创建用户实例并设置密码
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        # 添加到数据库会话并提交
        db.session.add(user)
        db.session.commit()
        # 显示成功消息
        flash('恭喜您，注册成功！现在可以登录了。', 'success')
        # 重定向到登录页面
        return redirect(url_for('main.login'))
    return render_template('register.html', title='注册', form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()

    if form.validate_on_submit():
        # 获取用户输入
        user_input = form.username_or_email.data

        # --- 核心修改：使用 or_ 查询 ---
        # 查询用户表中，username等于输入 或 email等于输入 的第一条记录
        user = User.query.filter(
            or_(User.username == user_input, User.email == user_input)
        ).first()

        # 验证用户存在且密码正确
        if user is None or not user.check_password(form.password.data):
            flash('用户名/邮箱或密码无效，请重试。', 'danger')
            return redirect(url_for('main.login'))

        login_user(user, remember=form.remember_me.data)
        flash('登录成功！', 'success')

        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.index'))

    return render_template('login.html', title='登录', form=form)


@main.route('/logout')
def logout():
    logout_user()
    flash('您已成功退出登录。', 'info')
    return redirect(url_for('main.index'))


@main.route('/profile')
@login_required
def profile():
    # 查询用户发表过的所有书评
    user_comments = current_user.comments.order_by(Comment.created_at.desc()).all()

    # --- 新增查询 ---
    # 查询用户发布过的所有帖子
    user_posts = current_user.posts.order_by(Post.created_at.desc()).all()
    # 查询用户发表过的所有回复
    user_replies = current_user.replies.order_by(Reply.created_at.desc()).all()
    # ----------------

    return render_template('profile.html',
                           title='个人主页',
                           user=current_user,
                           comments=user_comments,
                           posts=user_posts,
                           replies=user_replies)


@main.route('/search')
def search():
    # 从URL参数中获取查询关键字 'q'
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)

    # 使用 aSQLAlchemy 的 like 操作符进行模糊查询
    # %...% 表示匹配任意字符
    search_pattern = f"%{query}%"
    pagination = Book.query.filter(Book.title.like(search_pattern)).paginate(
        page=page, per_page=12, error_out=False
    )

    books_for_template = []
    for book in pagination.items:
        books_for_template.append({
            'id': book.id,
            'title': book.title,
            'rating': book.rating,
            'cover_image': book.cover_image if book.cover_image else generate_svg_cover(book.title)
        })

    return render_template('search_results.html',
                           title=f"搜索: {query}",
                           query=query,
                           books=books_for_template,
                           pagination=pagination)

# --- 管理员仪表盘 ---
@main.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # 查询统计数据
    user_count = User.query.count()
    book_count = Book.query.count()
    comment_count = Comment.query.count()

    # 查询所有用户
    users = User.query.order_by(User.id).all()

    return render_template('admin/dashboard.html',
                           title='管理员后台',
                           users=users,
                           user_count=user_count,
                           book_count=book_count,
                           comment_count=comment_count)

# --- 管理员编辑用户 ---
@main.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminEditUserForm()
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        db.session.commit()
        flash('用户信息已更新！', 'success')
        return redirect(url_for('main.admin_dashboard'))
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role
    return render_template('admin/edit_user.html', title='编辑用户', form=form, user=user)

# --- 管理员删除用户 (使用POST请求防止CSRF攻击) ---
@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin():
        flash('不能删除管理员账户！', 'danger')
        return redirect(url_for('main.admin_dashboard'))
    db.session.delete(user)
    db.session.commit()
    flash('用户已删除。', 'success')
    return redirect(url_for('main.admin_dashboard'))

# --- 用户编辑个人信息 ---
@main.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.age = form.age.data
        current_user.profile = form.profile.data
        db.session.commit()
        flash('您的个人信息已更新！', 'success')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.age.data = current_user.age
        form.profile.data = current_user.profile
    return render_template('edit_profile.html', title='编辑个人信息', form=form)


@main.route('/favorite/<int:book_id>', methods=['POST'])
@login_required
def favorite(book_id):
    book = Book.query.get_or_404(book_id)
    current_user.add_favorite(book)
    db.session.commit()
    flash('已成功收藏本书！', 'success')
    return redirect(url_for('main.book_detail', book_id=book_id))

@main.route('/unfavorite/<int:book_id>', methods=['POST'])
@login_required
def unfavorite(book_id):
    book = Book.query.get_or_404(book_id)
    current_user.remove_favorite(book)
    db.session.commit()
    flash('已取消收藏。', 'info')
    return redirect(url_for('main.book_detail', book_id=book_id))


# --- 轮播图管理 ---
@main.route('/admin/carousel')
@login_required
@admin_required
def carousel_management():
    items = CarouselItem.query.order_by(CarouselItem.display_order).all()
    return render_template('admin/carousel_management.html', items=items)

@main.route('/admin/carousel/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_carousel_item():
    form = CarouselItemForm()
    if form.validate_on_submit():
        item = CarouselItem(
            book_id=form.book_id.data,
            custom_title=form.custom_title.data,
            custom_summary=form.custom_summary.data,
            image_url=form.image_url.data,
            target_url=form.target_url.data,
            display_order=form.display_order.data,
            is_active=form.is_active.data
        )
        db.session.add(item)
        db.session.commit()
        flash('轮播项已添加！', 'success')
        return redirect(url_for('main.carousel_management'))
    return render_template('admin/carousel_form.html', form=form, title='添加轮播项')

@main.route('/admin/carousel/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_carousel_item(item_id):
    item = CarouselItem.query.get_or_404(item_id)
    form = CarouselItemForm(obj=item)
    if form.validate_on_submit():
        item.book_id = form.book_id.data
        item.custom_title = form.custom_title.data
        item.custom_summary = form.custom_summary.data
        item.image_url = form.image_url.data
        item.target_url = form.target_url.data
        item.display_order = form.display_order.data
        item.is_active = form.is_active.data
        db.session.commit()
        flash('轮播项已更新！', 'success')
        return redirect(url_for('main.carousel_management'))
    return render_template('admin/carousel_form.html', form=form, title='编辑轮播项')

@main.route('/admin/carousel/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def delete_carousel_item(item_id):
    item = CarouselItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('轮播项已删除。', 'success')
    return redirect(url_for('main.carousel_management'))


@main.route('/admin/books')
@login_required
@admin_required
def book_management():
    page = request.args.get('page', 1, type=int)
    # 从URL参数中获取搜索关键字 'q'
    query = request.args.get('q', '')

    # 基础查询对象
    books_query = Book.query

    # 如果存在搜索关键字，则应用过滤
    if query:
        search_pattern = f"%{query}%"
        # 同时在书名和ISBN中进行模糊搜索
        books_query = books_query.filter(
            or_(Book.title.like(search_pattern), Book.isbn.like(search_pattern))
        )

    # 对查询结果进行排序和分页
    pagination = books_query.order_by(Book.id.desc()).paginate(
        page=page,
        per_page=15,  # 每页显示15条
        error_out=False
    )

    books = pagination.items

    # 将 pagination 对象和 query 字符串都传递给模板
    return render_template('admin/book_management.html',
                           books=books,
                           pagination=pagination,
                           query=query)



@main.route('/admin/book/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        # 检查ISBN是否已存在
        if form.isbn.data and Book.query.filter_by(isbn=form.isbn.data).first():
            flash('该ISBN已存在，请勿重复添加。', 'danger')
        else:
            new_book = Book(
                title=form.title.data,
                isbn=form.isbn.data,
                publication_time=form.publication_time.data,
                pages=form.pages.data,
                price=form.price.data,
                rating=form.rating.data,
                summary=form.summary.data,
                summary_zh=form.summary_zh.data,
                cover_image=form.cover_image.data
            )
            db.session.add(new_book)
            db.session.commit()
            flash('新书籍已成功添加！', 'success')
            return redirect(url_for('main.book_management'))
    return render_template('admin/book_form.html', form=form, title='添加新书籍')


# --- 模板下载路由 ---
@main.route('/admin/download_template')
@login_required
@admin_required
def download_template():
    # 定义模板的列名
    template_columns = ['title', 'isbn', 'publication_time', 'pages', 'price', 'rating', 'summary', 'cover_image']
    df = pd.DataFrame(columns=template_columns)

    # 将DataFrame保存到内存中的BytesIO对象
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    output.seek(0)

    # 通过send_file发送文件
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name='book_template.xlsx')


# --- 批量添加路由 ---
@main.route('/admin/batch_add_books', methods=['GET', 'POST'])
@login_required
@admin_required
def batch_add_books():
    form = FileUploadForm()
    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        # 建议创建一个uploads文件夹存放临时文件
        upload_path = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        f.save(upload_path)

        try:
            df = pd.read_excel(upload_path)
            added_count = 0
            skipped_count = 0
            for index, row in df.iterrows():
                # 简单的数据验证
                if pd.isna(row['title']):
                    continue

                isbn = str(row['isbn']) if pd.notna(row['isbn']) else None
                if isbn and Book.query.filter_by(isbn=isbn).first():
                    skipped_count += 1
                    continue

                new_book = Book(
                    title=row.get('title'),
                    isbn=isbn,
                    publication_time=str(row.get('publication_time')),
                    pages=int(row['pages']) if pd.notna(row['pages']) else None,
                    price=str(row.get('price')),
                    rating=float(row['rating']) if pd.notna(row['rating']) else None,
                    summary=row.get('summary'),
                    cover_image=row.get('cover_image')
                )
                db.session.add(new_book)
                added_count += 1

            db.session.commit()
            flash(f'批量导入完成！成功添加 {added_count} 本书，跳过 {skipped_count} 本（因ISBN重复）。', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'处理文件时发生错误: {e}', 'danger')
        finally:
            os.remove(upload_path)  # 删除临时文件

        return redirect(url_for('main.book_management'))

    return render_template('admin/batch_add_form.html', form=form)


# --- 新增的书籍编辑路由 ---
@main.route('/admin/book/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    # 根据ID查询需要编辑的书籍，如果不存在则返回404
    book = Book.query.get_or_404(book_id)
    # 创建表单实例，并将书籍原来的ISBN传入
    form = BookForm(original_isbn=book.isbn)

    # 如果是POST请求（即用户提交了表单）
    if form.validate_on_submit():
        # 将表单中的数据更新到book对象上
        book.title = form.title.data
        book.isbn = form.isbn.data
        book.publication_time = form.publication_time.data
        book.pages = form.pages.data
        book.price = form.price.data
        book.rating = form.rating.data
        book.summary = form.summary.data
        book.summary_zh = form.summary_zh.data
        book.cover_image = form.cover_image.data
        db.session.commit()  # 提交数据库会话以保存更改
        flash('书籍信息已成功更新！', 'success')
        return redirect(url_for('main.book_management'))

    # 如果是GET请求（即用户刚点进编辑页面）
    elif request.method == 'GET':
        # 用书籍的现有数据填充表单
        form.title.data = book.title
        form.isbn.data = book.isbn
        form.publication_time.data = book.publication_time
        form.pages.data = book.pages
        form.price.data = book.price
        form.rating.data = book.rating
        form.summary.data = book.summary
        form.summary_zh.data = book.summary_zh
        form.cover_image.data = book.cover_image

    # 渲染同一个表单模板，并传入“编辑书籍”的标题
    return render_template('admin/book_form.html', form=form, title='编辑书籍')


# --- 新增路由：数据统计看板 ---
# --- 新增路由：数据统计看板 ---
@main.route('/stats')
def stats():
    # 1. 按出版年份统计书籍数量 (已有)
    year_counts = db.session.query(
        extract('year', Book.publication_date).label('year'),
        func.count(Book.id).label('count')
    ).filter(Book.publication_date.isnot(None)) \
        .group_by('year') \
        .order_by('year') \
        .all()
    years_data = {
        'labels': [str(y.year) for y in year_counts if y.year],
        'data': [y.count for y in year_counts if y.year]
    }

    # 2. 评分区间分布 (已有)
    rating_distribution = db.session.query(
        case(
            (Book.rating >= 9.0, '9-10分'),
            (Book.rating >= 8.0, '8-9分'),
            (Book.rating >= 7.0, '7-8分'),
            (Book.rating >= 6.0, '6-7分'),
            else_='6分以下'
        ).label('rating_range'),
        func.count(Book.id).label('count')
    ).filter(Book.rating.isnot(None)) \
        .group_by('rating_range') \
        .order_by('rating_range') \
        .all()
    rating_data = {
        'labels': [r.rating_range for r in rating_distribution],
        'data': [r.count for r in rating_distribution]
    }

    # --- 3. 新增：书籍页数分布 ---
    page_distribution = db.session.query(
        case(
            (Book.pages <= 100, '100页以下'),
            (Book.pages <= 300, '101-300页'),
            (Book.pages <= 500, '301-500页'),
            (Book.pages <= 800, '501-800页'),
            else_='800页以上'
        ).label('page_range'),
        func.count(Book.id).label('count')
    ).filter(Book.pages.isnot(None)) \
        .group_by('page_range') \
        .all()
    page_data = {
        'labels': [p.page_range for p in page_distribution],
        'data': [p.count for p in page_distribution]
    }

    # --- 4. 新增：评论最活跃的用户Top 10 ---
    active_users = db.session.query(
        User.username,
        func.count(Comment.id).label('comment_count')
    ).join(User, Comment.user_id == User.id) \
        .group_by(User.username) \
        .order_by(func.count(Comment.id).desc()) \
        .limit(10) \
        .all()
    active_users_data = {
        'labels': [u.username for u in active_users],
        'data': [u.comment_count for u in active_users]
    }

    return render_template('stats.html',
                           title='书海统计',
                           years_data=years_data,
                           rating_data=rating_data,
                           page_data=page_data,
                           active_users_data=active_users_data)



# # --- 论坛页面路由 ---
# @main.route('/forum')
# def forum():
#     posts = Post.query.order_by(Post.created_at.desc()).all()
#     return render_template('forum.html', title='畅聊空间', posts=posts)

# @main.route('/forum/new', methods=['GET', 'POST'])
# @login_required
# def new_post():
#     form = PostForm()
#     if form.validate_on_submit():
#         post = Post(title=form.title.data, body=form.body.data, author=current_user)
#         db.session.add(post)
#         db.session.commit()
#         flash('您的帖子已发布！', 'success')
#         return redirect(url_for('main.forum'))
#     return render_template('new_post.html', title='发布新帖', form=form)

# --- 新增路由：关于我们 ---
@main.route('/about')
def about():
    return render_template('about.html', title='关于我们')


# --- 论坛相关路由 (全新) ---
@main.route('/forum')
def forum():
    return render_template('forum.html', title='畅聊空间')


@main.route('/api/posts')
def api_posts():
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'time')

    query = Post.query
    if sort_by == 'likes':
        query = query.outerjoin(post_likes).group_by(Post.id).order_by(func.count(post_likes.c.user_id).desc(),
                                                                       Post.created_at.desc())
    elif sort_by == 'replies':
        query = query.outerjoin(Reply).group_by(Post.id).order_by(func.count(Reply.id).desc(), Post.created_at.desc())
    else:  # 'time' or default
        query = query.order_by(Post.created_at.desc())

    posts = query.paginate(page=page, per_page=12, error_out=False).items

    # 渲染成HTML片段返回
    return render_template('_post_cards.html', posts=posts)


@main.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    form = ReplyForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        reply = Reply(body=form.body.data, author=current_user, post=post)
        db.session.add(reply)
        # 添加消息通知
        if post.author != current_user:
            notification = Notification(recipient=post.author, sender=current_user,
                                        post=post, reply=reply, notification_type='reply')
            db.session.add(notification)
        db.session.commit()
        return redirect(url_for('main.post_detail', post_id=post_id))

    replies = post.replies.order_by(Reply.created_at.asc()).all()
    return render_template('post_detail.html', post=post, form=form, replies=replies)


@main.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.has_liked_post(post):
        current_user.like_post(post)
        if post.author != current_user:
            notification = Notification(recipient=post.author, sender=current_user,
                                        post=post, notification_type='like')
            db.session.add(notification)
        db.session.commit()
    return jsonify({'status': 'ok', 'likes': post.liked_by.count()})


@main.route('/post/<int:post_id>/unlike', methods=['POST'])
@login_required
def unlike_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.has_liked_post(post):
        current_user.unlike_post(post)
        db.session.commit()
    return jsonify({'status': 'ok', 'likes': post.liked_by.count()})


@main.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_admin():
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('帖子已删除。', 'success')
    return redirect(url_for('main.forum'))


@main.route('/reply/<int:reply_id>/delete', methods=['POST'])
@login_required
def delete_reply(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if reply.author != current_user and not current_user.is_admin():
        abort(403)
    post_id = reply.post_id
    db.session.delete(reply)
    db.session.commit()
    flash('回复已删除。', 'success')
    return redirect(url_for('main.post_detail', post_id=post_id))


@main.route('/forum/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, body=form.body.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('您的帖子已发布！', 'success')
        return redirect(url_for('main.post_detail', post_id=post.id))
    return render_template('new_post.html', title='发布新帖', form=form)


# --- 消息通知路由 (全新) ---
@main.route('/notifications')
@login_required
def notifications():
    # 首次进入页面时，将所有未读消息标记为已读
    current_user.notifications.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()

    user_notifications = current_user.notifications.order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications)
