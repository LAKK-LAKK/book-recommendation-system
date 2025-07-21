# /BookRecommendSystem/app/models.py
from datetime import datetime

from . import db
from flask_login import UserMixin
from . import login_manager
from sqlalchemy.sql import func
# 导入密码哈希工具
from werkzeug.security import generate_password_hash, check_password_hash


# Flask-Login 要求我们提供一个 user_loader 回调函数
# 这个函数用于根据用户ID从数据库中加载用户对象
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 定义多对多关系的关联表 ---
# --- 关联表定义 ---
favorites = db.Table('favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

post_likes = db.Table('post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    # --- 字段 ---
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    gender = db.Column(db.Enum('保密', '男', '女'), nullable=False, default='保密')
    age = db.Column(db.SmallInteger, nullable=True)
    profile = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # --- 关系 ---
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    favorites = db.relationship('Book', secondary=favorites, lazy='dynamic',
                                backref=db.backref('favorited_by', lazy='dynamic'),
                                order_by="favorites.c.created_at.desc()")
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    replies = db.relationship('Reply', backref='author', lazy='dynamic')
    liked_posts = db.relationship('Post', secondary=post_likes, lazy='dynamic',
                                  backref=db.backref('liked_by', lazy='dynamic'))
    notifications = db.relationship('Notification', foreign_keys='Notification.recipient_id',
                                    backref='recipient', lazy='dynamic')

    # --- 密码处理方法 ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- 权限检查方法 ---
    def is_admin(self):
        return self.role == 'admin'

    # --- 收藏书籍方法 ---
    def add_favorite(self, book):
        if not self.is_favorite(book):
            self.favorites.append(book)

    def remove_favorite(self, book):
        if self.is_favorite(book):
            self.favorites.remove(book)

    def is_favorite(self, book):
        return self.favorites.filter(favorites.c.book_id == book.id).count() > 0

    # --- 点赞帖子方法 ---
    def like_post(self, post):
        if not self.has_liked_post(post):
            self.liked_posts.append(post)

    def unlike_post(self, post):
        if self.has_liked_post(post):
            self.liked_posts.remove(post)

    def has_liked_post(self, post):
        return self.liked_posts.filter(post_likes.c.post_id == post.id).count() > 0

    # --- 消息通知方法 ---
    def unread_notifications_count(self):
        return Notification.query.filter_by(recipient_id=self.id, is_read=False).count()


class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    publication_time = db.Column(db.String(50), nullable=True)
    pages = db.Column(db.Integer, nullable=True)
    price = db.Column(db.String(50), nullable=True)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    review_count = db.Column(db.Integer, nullable=True)
    cover_image = db.Column(db.String(512), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    publication_date = db.Column(db.Date, nullable=True)  # 对应新字段
    summary_zh = db.Column(db.Text, nullable=True)  # 别忘了加上翻译字段

    # 定义关系: 一本书可以有多条评论
    comments = db.relationship('Comment', backref='book', lazy='dynamic')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # 定义外键
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


# --- 在文件末尾添加新的轮播图模型 ---
class CarouselItem(db.Model):
    __tablename__ = 'carousel_items'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    custom_title = db.Column(db.String(255))
    custom_summary = db.Column(db.Text)
    image_url = db.Column(db.String(512), nullable=False)
    target_url = db.Column(db.String(512), nullable=False)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # 建立与Book模型的关系
    book = db.relationship('Book')


# --- 在文件末尾添加新的Post模型 ---
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    replies = db.relationship('Reply', backref='post', lazy='dynamic', cascade='all, delete-orphan')


class Reply(db.Model):
    __tablename__ = 'replies'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    reply_id = db.Column(db.Integer, db.ForeignKey('replies.id'))
    notification_type = db.Column(db.String(50), nullable=False)  # 'like', 'reply'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    post = db.relationship('Post')
    reply = db.relationship('Reply')
