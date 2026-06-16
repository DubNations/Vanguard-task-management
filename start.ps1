# ============================================================
# 种子团队任务管理系统 — Windows 本地开发一键启动
# 用法: .\start.ps1
# 首次运行会自动创建虚拟环境、安装依赖、初始化数据库
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$VenvDir = Join-Path $ProjectRoot ".venv"

# 设置本地开发环境标识
$env:DJANGO_ENV = "local"

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "    种子团队任务管理系统 — 本地开发环境" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------------
# 辅助函数：查找真实 Python（跳过 Windows Store 别名）
# ----------------------------------------------------------
function Find-RealPython {
    # 1) 尝试 PATH 中的 python，但排除 WindowsApps 别名
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue).Source,
        (Get-Command python3 -ErrorAction SilentlyContinue).Source
    )
    foreach ($c in $candidates) {
        if ($c -and $c -notlike '*WindowsApps*') {
            $ver = & $c --version 2>&1
            if ($LASTEXITCODE -eq 0) { return $c }
        }
    }
    # 2) 搜索常见安装路径
    $searchPaths = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "C:\Python*",
        "C:\Program Files\Python*"
    )
    foreach ($sp in $searchPaths) {
        $found = Get-ChildItem $sp -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue |
                 Sort-Object FullName -Descending | Select-Object -First 1
        if ($found) {
            $ver = & $found.FullName --version 2>&1
            if ($LASTEXITCODE -eq 0) { return $found.FullName }
        }
    }
    # 3) 尝试 py launcher
    $pyLauncher = (Get-Command py -ErrorAction SilentlyContinue).Source
    if ($pyLauncher) {
        $ver = & $pyLauncher --version 2>&1
        if ($LASTEXITCODE -eq 0) { return $pyLauncher }
    }
    return $null
}

function Find-RealNode {
    $candidates = @(
        (Get-Command node -ErrorAction SilentlyContinue).Source,
        "C:\Program Files\nodejs\node.exe",
        "C:\Program Files (x86)\nodejs\node.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) {
            $ver = & $c --version 2>&1
            if ($LASTEXITCODE -eq 0) { return $c }
        }
    }
    return $null
}

function Find-RealNpm {
    $candidates = @(
        (Get-Command npm -ErrorAction SilentlyContinue).Source,
        "C:\Program Files\nodejs\npm.cmd",
        "C:\Program Files (x86)\nodejs\npm.cmd"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return $null
}

# ----------------------------------------------------------
# 1. 检查 Python
# ----------------------------------------------------------
Write-Host "[1/6] 检查 Python 环境..." -ForegroundColor Yellow
$RealPython = Find-RealPython
if ($RealPython) {
    $pyVersion = & $RealPython --version 2>&1
    Write-Host "  OK: $pyVersion ($RealPython)" -ForegroundColor Green
} else {
    Write-Host "  ERROR: 未找到 Python，请先安装 Python 3.11+" -ForegroundColor Red
    Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}

# ----------------------------------------------------------
# 2. 检查 Node.js
# ----------------------------------------------------------
Write-Host "[2/6] 检查 Node.js 环境..." -ForegroundColor Yellow
$RealNode = Find-RealNode
$RealNpm = Find-RealNpm
if ($RealNode) {
    $nodeVersion = & $RealNode --version 2>&1
    Write-Host "  OK: Node.js $nodeVersion ($RealNode)" -ForegroundColor Green
} else {
    Write-Host "  ERROR: 未找到 Node.js，请先安装 Node.js 18+" -ForegroundColor Red
    Write-Host "  下载地址: https://nodejs.org/" -ForegroundColor Gray
    exit 1
}

# ----------------------------------------------------------
# 3. 创建/激活 Python 虚拟环境 & 安装依赖
# ----------------------------------------------------------
Write-Host "[3/6] 准备 Python 虚拟环境..." -ForegroundColor Yellow

if (-not (Test-Path $VenvDir)) {
    Write-Host "  创建虚拟环境 .venv ..." -ForegroundColor Gray
    & $RealPython -m venv $VenvDir
}

# 激活虚拟环境
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    # 尝试 .bat 方式激活
    $ActivateBat = Join-Path $VenvDir "Scripts\activate.bat"
    if (Test-Path $ActivateBat) {
        & cmd /c "$ActivateBat"
    }
}

# 使用虚拟环境的 pip
$PipPath = Join-Path $VenvDir "Scripts\pip.exe"
$PythonPath = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PipPath)) {
    $PipPath = "pip"
    $PythonPath = "python"
}

Write-Host "  安装 Python 依赖 (首次运行较慢)..." -ForegroundColor Gray
& $PipPath install -r (Join-Path $BackendDir "requirements\local.txt") -q 2>&1 | Out-Null
Write-Host "  Python 依赖就绪" -ForegroundColor Green

# ----------------------------------------------------------
# 4. 安装前端依赖
# ----------------------------------------------------------
Write-Host "[4/6] 准备前端依赖..." -ForegroundColor Yellow

Push-Location $FrontendDir
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "  npm install (首次运行较慢)..." -ForegroundColor Gray
        & $RealNpm install 2>&1 | Out-Null
    }
    Write-Host "  前端依赖就绪" -ForegroundColor Green
} finally {
    Pop-Location
}

# ----------------------------------------------------------
# 5. 数据库迁移 & 种子数据
# ----------------------------------------------------------
Write-Host "[5/6] 初始化数据库..." -ForegroundColor Yellow

Push-Location $BackendDir
try {
    & $PythonPath manage.py migrate --noinput 2>&1 | Out-Null
    Write-Host "  数据库迁移完成" -ForegroundColor Green

    & $PythonPath manage.py seed_data 2>&1 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
} finally {
    Pop-Location
}

# ----------------------------------------------------------
# 6. 启动服务
# ----------------------------------------------------------
Write-Host "[6/6] 启动服务..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "    后端 API:  http://localhost:8000" -ForegroundColor Green
Write-Host "    前端页面:  http://localhost:5173" -ForegroundColor Green
Write-Host "    管理员:    admin@seedteam.local" -ForegroundColor Green
Write-Host "    密码:      seedteam2026" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  按 Ctrl+C 停止后端服务" -ForegroundColor Gray
Write-Host "  前端请在另一个终端运行: .\start-fe.ps1" -ForegroundColor Gray
Write-Host ""

# 启动后端 (前台运行)
Push-Location $BackendDir
try {
    & $PythonPath manage.py runserver 127.0.0.1:8000
} finally {
    Pop-Location
}
