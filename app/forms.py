# /BookRecommendSystem/app/forms.py

from flask_wtf import FlaskForm
# 导入 TextAreaField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from .models import User, Book
from wtforms import IntegerField, TextAreaField
from wtforms.validators import Optional

# --- 登录表单 ---
class LoginForm(FlaskForm):
    # 1. 将字段名从 email 改为 username_or_email
    # 2. 修改标签为 '用户名或邮箱'
    # 3. 移除邮箱格式的Regexp验证器，只保留必填验证
    username_or_email = StringField('用户名或邮箱', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

# --- 注册表单 ---
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    # 使用Regexp代替Email验证器
    email = StringField('邮箱', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', message="请输入有效的邮箱地址。")
    ])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        '确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致！')])
    submit = SubmitField('立即注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被注册，请换一个。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册，请换一个。')

# --- 在文件末尾添加新的评论表单 ---
class CommentForm(FlaskForm):
    content = TextAreaField('发表评论', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('提交')


# --- 管理员编辑用户表单 ---
class AdminEditUserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('邮箱', validators=[DataRequired(), Regexp(r'...')]) # 正则表达式省略
    role = SelectField('角色', choices=[('user', '普通用户'), ('admin', '管理员')])
    submit = SubmitField('更新用户信息')

# --- 用户编辑个人信息表单 ---
class EditProfileForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    age = IntegerField('年龄', validators=[Optional()])  # Optional表示该字段可选
    profile = TextAreaField('个人简介', validators=[Length(max=500)])
    submit = SubmitField('保存更改')

from wtforms import IntegerField, BooleanField
# --- 轮播图管理表单 ---
class CarouselItemForm(FlaskForm):
    book_id = IntegerField('关联图书ID (可选)', validators=[Optional()])
    custom_title = StringField('自定义标题 (可选)')
    custom_summary = TextAreaField('自定义简介 (可选)')
    image_url = StringField('图片链接', validators=[DataRequired()])
    target_url = StringField('跳转链接', validators=[DataRequired()])
    display_order = IntegerField('显示顺序', default=0)
    is_active = BooleanField('是否激活', default=True)
    submit = SubmitField('保存')


from wtforms import IntegerField, FloatField
# --- 添加/编辑书籍表单 ---
class BookForm(FlaskForm):
    title = StringField('书名', validators=[DataRequired(), Length(max=255)])
    isbn = StringField('ISBN', validators=[Optional(), Length(max=20)])
    publication_time = StringField('出版时间', validators=[Optional(), Length(max=50)])
    pages = IntegerField('页数', validators=[Optional()])
    price = StringField('价格', validators=[Optional(), Length(max=50)])
    rating = FloatField('评分', validators=[Optional()])
    summary = TextAreaField('简介 (原文)', validators=[Optional()])
    summary_zh = TextAreaField('简介 (中文)', validators=[Optional()])
    cover_image = StringField('封面图片链接', validators=[Optional(), Length(max=512)])
    submit = SubmitField('保存书籍')

    # --- 新增的初始化方法和自定义验证 ---
    def __init__(self, original_isbn=None, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        self.original_isbn = original_isbn

    def validate_isbn(self, isbn):
        # 如果用户输入了ISBN，并且这个ISBN和原来的不一样
        if isbn.data and isbn.data != self.original_isbn:
            # 查询数据库中是否存在使用这个新ISBN的书籍
            book = Book.query.filter_by(isbn=isbn.data).first()
            if book:
                raise ValidationError('这个ISBN已经被另一本书使用，请输入唯一的ISBN。')


from flask_wtf.file import FileField, FileRequired, FileAllowed
class FileUploadForm(FlaskForm):
    file = FileField('选择Excel文件', validators=[
        FileRequired(),
        FileAllowed(['xlsx'], '只支持 .xlsx 格式的Excel文件！')
    ])
    submit = SubmitField('上传并导入')



class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(min=5, max=200)])
    body = TextAreaField('内容', validators=[DataRequired()])
    submit = SubmitField('发布帖子')

class ReplyForm(FlaskForm):
    body = TextAreaField('发表回复', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('提交')