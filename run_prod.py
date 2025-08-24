#!/usr/bin/env python
"""
生产环境运行脚本 - 禁用热重载和调试模式
"""
import os

# 设置生产环境变量
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'false'
os.environ['FLASK_HOST'] = '0.0.0.0'
os.environ['FLASK_PORT'] = '5000'

if __name__ == '__main__':
    from app import app, db
    
    with app.app_context():
        db.create_all()
        print("数据库已初始化")
        print("-" * 50)
        print("生产服务器已启动")
        print("访问地址: http://0.0.0.0:5000")
        print("局域网访问: http://[您的IP地址]:5000")
        print("按 CTRL+C 停止服务器")
        print("-" * 50)
    
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
