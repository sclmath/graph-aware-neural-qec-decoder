<#
.SYNOPSIS
    关机守卫：等工作全部结束后自动关机。

.DESCRIPTION
    由计划任务 Codex-QEC-ShutdownWhenDone 每 5 分钟调用一次。满足下面两个条件
    之一、**并且**本仓库的 .venv Python 已经没有在跑的进程时，发出关机指令：

      * results\DONE 哨兵文件存在（表示分析与报告工作已经收口并提交），或
      * 到达 -Deadline 兜底时间。

    关机前写入 results\logs\shutdown_issued.flag，重复调用不会再触发第二次。
    取消方式：见 docs/HANDOFF.md 或直接
        Unregister-ScheduledTask -TaskName 'Codex-QEC-ShutdownWhenDone' -Confirm:$false
        Remove-Item results\logs\shutdown_issued.flag -ErrorAction SilentlyContinue

.PARAMETER DryRun
    只写日志、不真的关机（用于验证）。
#>
param(
    [string]$Sentinel = 'results\DONE',
    [datetime]$Deadline = '2026-10-16 09:15',
    [int]$GraceSeconds = 300,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

$logDir = 'results\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'shutdown_watch.log'
$flag = Join-Path $logDir 'shutdown_issued.flag'

function Write-Log([string]$message) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message" | Out-File -FilePath $log -Append -Encoding utf8
}

if (Test-Path $flag) {
    Write-Log 'already issued; nothing to do'
    exit 0
}

try {
    $venvPython = (Resolve-Path '.venv\Scripts\python.exe').Path
} catch {
    $venvPython = $null
}

$running = 0
if ($venvPython) {
    try {
        $running = @(
            Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop |
                Where-Object { $_.ExecutablePath -eq $venvPython }
        ).Count
    } catch {
        $running = @(Get-Process python -ErrorAction SilentlyContinue).Count
    }
}

$sentinelReady = Test-Path $Sentinel
$pastDeadline = (Get-Date) -ge $Deadline

if (-not ($sentinelReady -or $pastDeadline)) {
    Write-Log "waiting (sentinel=$sentinelReady deadline=$pastDeadline running=$running)"
    exit 0
}

if ($running -gt 0) {
    Write-Log "ready to shut down but $running python process(es) still running; waiting"
    exit 0
}

Write-Log "conditions met (sentinel=$sentinelReady deadline=$pastDeadline); issuing shutdown in $GraceSeconds s"
if ($DryRun) {
    Write-Log 'dry run: no shutdown issued'
    exit 0
}

New-Item -ItemType File -Path $flag -Force | Out-Null
shutdown.exe /s /t $GraceSeconds /c "QEC work finished - automatic shutdown"
Write-Log 'shutdown.exe issued'
exit 0
