# ============================================================
# 种子团队任务管理系统 — 前端独立启动
# 用法: .\start-fe.ps1
# 在另一个终端窗口运行，配合 start.ps1 的后端服务
# ============================================================

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host ""
Write-Host "  种子团队 — 前端开发服务器" -ForegroundColor Cyan
Write-Host "  访问地址: http://localhost:5173" -ForegroundColor Green
Write-Host ""

Push-Location $FrontendDir
try {
    $NpmCmd = (Get-Command npm -ErrorAction SilentlyContinue).Source
    if (-not $NpmCmd -or -not (Test-Path $NpmCmd)) {
        $NpmCmd = "C:\Program Files\nodejs\npm.cmd"
    }
    if (-not (Test-Path "node_modules")) {
        Write-Host "  npm install..." -ForegroundColor Yellow
        & $NpmCmd install
    }
    & $NpmCmd run dev
} finally {
    Pop-Location
}
