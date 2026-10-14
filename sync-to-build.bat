@echo off
REM sync-to-build.bat —— 从中文路径源码同步到英文路径构建副本
REM 用法：在项目根目录执行 sync-to-build.bat
REM 排除缓存目录和工具状态文件，仅同步源码和配置

set SRC=%~dp0
set DST=C:\dev\lingyu\harmony-app

echo Syncing from: %SRC%
echo           to: %DST%
echo.

if not exist "%DST%" (
    echo Target directory does not exist. Creating...
    mkdir "%DST%"
)

robocopy "%SRC%" "%DST%" /E /XD node_modules oh_modules .hvigor .codeartsdoer /XF *.lock /NFL /NDL /NJH /NJS /NC /NS /R:1 /W:1

if %ERRORLEVEL% LSS 8 (
    echo.
    echo Sync completed successfully.
    echo Build command: cd %DST% ^&^& devecocli build --build-mode debug
) else (
    echo.
    echo Sync failed with error code %ERRORLEVEL%
)

exit /b %ERRORLEVEL%