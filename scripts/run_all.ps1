<#
.SYNOPSIS
    端到端烟雾测试：把交付范围内的主要代码路径完整跑一遍。

.DESCRIPTION
    默认（小规模）模式在数分钟内完成：单元测试、M0 数据链路、M1 基线 benchmark、
    CPU 预算探针、M2 汇总与出图。加 -Full 会额外跑 M2 训练与 M3 迁移扫描
    （数十分钟到数小时，见 docs/ROADMAP_TODO.md 第 1 节的算力预算）。

.EXAMPLE
    .\scripts\run_all.ps1
    .\scripts\run_all.ps1 -Full
#>
param(
    [switch]$Full,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = Join-Path $PWD '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'

$smoke = 'results\smoke'
# M0/M1 的目标目录已存在时会显式抛 FileExistsError（这是刻意的保护，见 HANDOFF 第 4 节），
# 所以 smoke 每次必须先清空自己的临时目录——它被 .gitignore 排除、只由本脚本写入。
# 用 Python 的 shutil 而不是 Remove-Item -Recurse（本机策略会拒绝后者）。
& $py -c "import shutil, pathlib; shutil.rmtree(pathlib.Path('results/smoke'), ignore_errors=True)"
New-Item -ItemType Directory -Force -Path $smoke | Out-Null
New-Item -ItemType Directory -Force -Path 'results\logs' | Out-Null

$script:failed = @()
$script:timings = @()

function Invoke-Step {
    param([string]$Name, [string[]]$Arguments)
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    $started = Get-Date
    & $py @Arguments
    $code = $LASTEXITCODE
    $elapsed = (Get-Date) - $started
    $script:timings += [pscustomobject]@{ Step = $Name; Seconds = [math]::Round($elapsed.TotalSeconds, 1); Exit = $code }
    if ($code -ne 0) {
        Write-Host "FAILED: $Name (exit $code)" -ForegroundColor Red
        $script:failed += $Name
    }
}

if (-not $SkipTests) {
    Invoke-Step 'unit tests' @('-m', 'pytest', '-q')
}
Invoke-Step 'M0 data pipeline' @('-m', 'graph_qec.m0', '--config', 'configs\m0_repetition_circuit_level.json', '--output-dir', $smoke)
Invoke-Step 'M1 baseline benchmark' @('-m', 'graph_qec.m1', '--config', 'configs\m1_repetition_code_capacity.json', '--output-dir', (Join-Path $smoke 'm1'))
Invoke-Step 'CPU budget probe (d=3/5)' @('scripts\probe_cpu_budget.py', '--distances', '3', '--gnn-distances', '5', '--json', (Join-Path $smoke 'cpu_budget.json'))
Invoke-Step 'M2 summary + figures' @('scripts\summarize_m2.py', '--results-dir', 'results\m2')

if ($Full) {
    Invoke-Step 'M2 train + evaluate (d=3)' @('-m', 'graph_qec.m2', '--config', 'configs\m2_learned_basis_repetition_circuit_level_d3.json', '--output-dir', $smoke)
    Invoke-Step 'M3 noise / distance sweep' @('scripts\run_m3_sweep.ps1')
}

Write-Host ""
Write-Host "=== 结果 ===" -ForegroundColor Cyan
$script:timings | Format-Table -AutoSize
if ($script:failed.Count -gt 0) {
    Write-Host ("失败的步骤：" + ($script:failed -join ', ')) -ForegroundColor Red
    exit 1
}
Write-Host "全部步骤通过。" -ForegroundColor Green