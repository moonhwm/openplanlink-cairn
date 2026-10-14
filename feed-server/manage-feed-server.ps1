# 铃语数据管道服务器 - PowerShell管理脚本
# 用法：
#   .\manage-feed-server.ps1 start    — 启动服务器
#   .\manage-feed-server.ps1 stop     — 停止服务器
#   .\manage-feed-server.ps1 status   — 查看状态
#   .\manage-feed-server.ps1 restart  — 重启服务器

param([Parameter(Position=0)][string]$Action = "status")

$NODE_EXE = "C:\Users\欧阳宏俊\nodejs\node-v22.11.0-win-x64\node.exe"
$SERVER_SCRIPT = "C:\Users\欧阳宏俊\Documents\kimi\tasks\2026-08-27\22-20-45-c3ffff44\harmony-app\feed-server\server.mjs"
$PORT = 8000

function Get-ServerPid {
    $line = netstat -ano | Select-String ":$PORT.*LISTENING"
    if ($line) {
        $parts = $line -split '\s+'
        return [int]$parts[-1]
    }
    return $null
}

function Start-Server {
    $serverPid = Get-ServerPid
    if ($serverPid) {
        Write-Host "[铃语管道] 服务器已在运行 (PID: $serverPid)" -ForegroundColor Yellow
        return
    }
    Write-Host "[铃语管道] 启动数据管道服务器..." -ForegroundColor Green
    Start-Process -FilePath $NODE_EXE -ArgumentList $SERVER_SCRIPT -WindowStyle Minimized
    Start-Sleep -Seconds 2
    $serverPid = Get-ServerPid
    if ($serverPid) {
        Write-Host "[铃语管道] 服务器已启动 (PID: $serverPid, 端口: $PORT)" -ForegroundColor Green
    } else {
        Write-Host "[铃语管道] 启动失败，请检查日志" -ForegroundColor Red
    }
}

function Stop-Server {
    $serverPid = Get-ServerPid
    if (-not $serverPid) {
        Write-Host "[铃语管道] 服务器未运行" -ForegroundColor Yellow
        return
    }
    Write-Host "[铃语管道] 停止服务器 (PID: $serverPid)..." -ForegroundColor Yellow
    taskkill /PID $serverPid /F
    Write-Host "[铃语管道] 服务器已停止" -ForegroundColor Green
}

function Get-Status {
    $serverPid = Get-ServerPid
    if ($serverPid) {
        Write-Host "[铃语管道] 服务器运行中 (PID: $serverPid, 端口: $PORT)" -ForegroundColor Green
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:$PORT/api/alerts/latest" -TimeoutSec 5
            Write-Host "[铃语管道] 数据接口正常，当前异动数: $($response.items.Count)" -ForegroundColor Green
        } catch {
            Write-Host "[铃语管道] 数据接口无响应" -ForegroundColor Red
        }
    } else {
        Write-Host "[铃语管道] 服务器未运行" -ForegroundColor Yellow
    }
}

switch ($Action) {
    "start"   { Start-Server }
    "stop"    { Stop-Server }
    "status"  { Get-Status }
    "restart" { Stop-Server; Start-Sleep -Seconds 1; Start-Server }
    default   { Write-Host "用法: .\manage-feed-server.ps1 [start|stop|status|restart]" }
}