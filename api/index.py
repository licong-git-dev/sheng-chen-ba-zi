from app import app

# Vercel入口点
def handler(request, response):
    return app(request, response)

# 也支持WSGI接口
application = app