@echo off
echo 正在启动开发服务器（热重载模式）...
echo.
set FLASK_ENV=development
set FLASK_DEBUG=true
python run_dev.py
pause
