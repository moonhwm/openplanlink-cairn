@echo off
REM 铃语数据管道服务器 - Windows启动脚本
REM 用法：双击运行，或放入 shell:startup 文件夹实现开机自启

set NODE_EXE=C:\Users\欧阳宏俊\nodejs\node-v22.11.0-win-x64\node.exe
set SERVER_SCRIPT=C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app\feed-server\server.mjs

REM 检查端口8000是否已被占用
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [铃语管道] 端口8000已被占用，服务器可能已在运行
    timeout /t 3 >nul
    exit /b 0
)

echo [铃语管道] 启动数据管道服务器...
start /min "" "%NODE_EXE%" "%SERVER_SCRIPT%"
echo [铃语管道] 服务器已启动（端口8000）
timeout /t 2 >nul