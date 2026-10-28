$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python 虚拟环境不存在，请先运行: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e '.[dev]'"
}

& $python (Join-Path $root "run.py")
