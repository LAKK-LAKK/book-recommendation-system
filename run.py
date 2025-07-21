# /BookRecommendSystem/run.py

from app import create_app

# 调用应用工厂创建app实例
app = create_app()

if __name__ == '__main__':
    # 启动Flask内置的Web服务器，debug=True开启调试模式
    # 调试模式下，代码修改后服务器会自动重启，并提供详细的错误页面
    app.run(debug=True)