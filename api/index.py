# Vercel入口文件
import sys
import os

# 确保可以导入app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel的标准入口点
def handler(request):
    return app(request.environ, lambda *args: None)

# Flask WSGI应用
application = app