# /BookRecommendSystem/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# 初始化插件实例，但此时不绑定到具体的app
db = SQLAlchemy()
login_manager = LoginManager()
# 当用户需要登录时，Flask-Login会重定向到这个路由
login_manager.login_view = 'main.login'
# 自定义需要登录时显示的提示消息
login_manager.login_message = "请先登录以访问此页面。"


def create_app(config_class=Config):
    """
    创建并配置Flask应用实例 (应用工厂)
    """
    app = Flask(__name__)

    # 从Config类加载配置
    app.config.from_object(config_class)

    # 将插件实例绑定到具体的app上
    db.init_app(app)
    login_manager.init_app(app)

    # 注册蓝图 (Blueprint)
    # 蓝图有助于我们将应用按功能模块化
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # 将 generate_svg_cover 函数注册为Jinja2的全局函数
    from .routes import generate_svg_cover_post
    app.jinja_env.globals.update(generate_svg_cover_post=generate_svg_cover_post)

    return app