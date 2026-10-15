<#
.SYNOPSIS
    T6 收尾：等网格跑完后自动生成 T10 / T7 / 工程性能表。

.DESCRIPTION
    由计划任务 Codex-QEC-T6Postprocess 每 10 分钟调用一次。幂等：完成后写入
    results\logs\t6_postprocess.done，之后调用直接退出。

    触发条件（全部满足）：
      * results\logs\t6_progress.log 里出现 "grid finished"（网格驱动已结束）
      * 本仓库 .venv 的 python 一个都不在跑
      * 尚未写过 done 标记

    然后依次执行：
      scripts\t10_multiseed_stats.py  -> results\t10\（含 surface_sweep_mean.json）
      scripts\threshold_estimate.py   -> results\m4\THRESHOLD.md（补线路级阈值）
      scripts\engineering_table.py    -> results\m5\ENGINEERING_TABLE.md

    日志：results\logs\t6_postprocess.log
#>
param([switch]$Force)

$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$logDir = 'results\logs'
$log = Join-Path $logDir 't6_postprocess.log'
$done = Join-Path $logDir 't6_postprocess.done'
$progress = Join-Path $logDir 't6_progress.log'

function Write-Log([string]$message) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message" | Out-File -FilePath $log -Append -Encoding utf8
}

if ((Test-Path $done) -and (-not $Force)) { exit 0 }

# The grid is done only when the LAST line of the progress log is the driver's
# "grid finished" summary. (Earlier dry runs also leave such a line in the file,
# so searching the whole log produced a false positive.)
$finished = $false
if (Test-Path $progress) {
    $last = Get-Content $progress -Tail 1 -ErrorAction SilentlyContinue
    if ($last -and ($last -match 'grid finished')) { $finished = $true }
}
if (-not $finished) { Write-Log 'grid still running; waiting'; exit 0 }

$running = 0
try {
    $running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -eq $py }).Count
} catch {
    $running = @(Get-Process python -ErrorAction SilentlyContinue).Count
}
if ($running -gt 0) { Write-Log "grid finished but $running python process(es) still running; waiting"; exit 0 }

Write-Log 'running the T6 post-processing chain'
& $py scripts\t10_multiseed_stats.py --results-dir results\m4_surface --output-dir results\t10 --min-test-shots 4096 *>> $log
Write-Log "t10 exit=$LASTEXITCODE"

& $py scripts\threshold_estimate.py --inputs results\t10\surface_sweep_mean.json results\m4\surface_sweep.json results\m4_threshold\surface_sweep.json --output results\m4\THRESHOLD.md *>> $log
Write-Log "threshold exit=$LASTEXITCODE"

& $py scripts\engineering_table.py --results-dir results --output results\m5\ENGINEERING_TABLE.md *>> $log
Write-Log "engineering table exit=$LASTEXITCODE"

New-Item -ItemType File -Path $done -Force | Out-Null
Write-Log 'post-processing complete'
exit 0
