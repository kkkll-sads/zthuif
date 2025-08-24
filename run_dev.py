#!/usr/bin/env python
"""
开发环境运行脚本 - 启用热重载
"""
import os
import sys

# 设置开发环境变量
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = 'true'
os.environ['FLASK_HOST'] = '127.0.0.1'
os.environ['FLASK_PORT'] = '5000'

# 运行应用
if __name__ == '__main__':
    # 导入并运行应用
    from app import app, db
    
    with app.app_context():
        db.create_all()
        print("数据库已初始化")
        print("-" * 50)
        print("开发服务器已启动（热重载已启用）")
        print("访问地址: http://127.0.0.1:5000")
        print("按 CTRL+C 停止服务器")
        print("-" * 50)
    
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=True)
