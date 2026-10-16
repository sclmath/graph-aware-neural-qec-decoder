<#
.SYNOPSIS
    关机守卫：等本仓库的后台任务跑完（且没有本仓库的 Python 进程在跑）后自动关机。

.DESCRIPTION
    两种用法：

    1) 常驻守望（2026-10-16 起用这种）——以 detached 进程启动：
       .\scripts\shutdown_when_done.ps1 -Watch -HardDeadline '2026-10-16 23:30'
       每 PollSeconds 秒检查一次，条件满足就 shutdown.exe /s /t <GraceSeconds>。

    2) 不带 -Watch 跑一次：只做一次条件检查并写日志（原计划任务的用法，不会关机）。

    触发条件（-Watch）：
      * 不存在属于本仓库的 python.exe 进程，且
        results\logs\t6_progress.log 最后一行是网格收尾行（grid finished / stopping），或
      * results\DONE 哨兵文件存在，或
      * 已过 -HardDeadline（兜底：即使还有 Python 在跑也关机——网格可断点续跑，
        最多损失当前一个点，而"机器该关而没关"在无人值守时是更糟的结果）。

    取消方式：
      * 关机指令带 GraceSeconds 秒宽限，期间 shutdown /a 可取消；
      * 或杀掉守望进程（PID 记在 shutdown_watch.log 的 "watcher started" 行）；
      * 已发出关机后想避免重启后再次触发：删除 results\logs\shutdown_issued.flag。
#>
param(
    [string]$Sentinel = 'results\DONE',
    [datetime]$HardDeadline = '2026-10-16 23:30',
    [int]$GraceSeconds = 300,
    [int]$PollSeconds = 60,
    [switch]$Watch,
    [switch]$DryRun,
    [switch]$AllowPastDeadline
)

$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)

$logDir = 'results\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'shutdown_watch.log'
$flag = Join-Path $logDir 'shutdown_issued.flag'
$progress = Join-Path $logDir 't6_progress.log'

function Write-Log([string]$message) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message" | Out-File -FilePath $log -Append -Encoding utf8
}

function Get-WorkerCount {
    # 数「venv 启动器」与「真正的解释器」两类：Windows 的 venv python.exe 会再拉起一个 base
    # 解释器子进程，两者命令行里都带本仓库的绝对路径，按命令行匹配最稳。
    $repo = (Get-Location).Path
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue
    if (-not $procs) { return 0 }
    return @($procs | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($repo) }).Count
}

function Get-ShutdownReason {
    if (Test-Path $Sentinel) { return 'sentinel' }
    if (-not $script:IgnoreDeadline -and (Get-Date) -ge $HardDeadline) { return 'hard deadline' }

    if ((Get-WorkerCount) -gt 0) { return $null }

    if (Test-Path $progress) {
        $last = (Get-Content $progress -Tail 1 -ErrorAction SilentlyContinue) -join ''
        if ($last -match 'grid finished|: stopping') { return 'grid finished and no python running' }
    }
    return $null
}

# 防呆：日期传错（例如被空格拆成两段）会得到一个已经过去的"截止时间"，
# 那会在启动瞬间触发关机。除非显式 -AllowPastDeadline，否则直接忽略它。
$script:IgnoreDeadline = $false
if ((Get-Date) -ge $HardDeadline) {
    if ($AllowPastDeadline) {
        Write-Log "hard deadline $HardDeadline is in the past and -AllowPastDeadline was given: it will fire immediately"
    } else {
        $script:IgnoreDeadline = $true
        Write-Log "refusing past hard deadline $HardDeadline (pass -AllowPastDeadline to use it): deadline trigger disabled"
    }
}

if (Test-Path $flag) {
    Write-Log 'already issued; nothing to do'
    exit 0
}

if (-not $Watch) {
    $reason = Get-ShutdownReason
    if ($reason) {
        Write-Log "ready ($reason) but -Watch not given: refusing to shut down"
    } else {
        Write-Log "waiting (python=$(Get-WorkerCount), sentinel exists=$(Test-Path $Sentinel))"
    }
    exit 0
}

Write-Log ("watcher started (pid " + $PID + "), cwd " + (Get-Location).Path + ", sentinel " + $Sentinel +
           " exists=" + (Test-Path $Sentinel) + ", hard deadline $HardDeadline, poll ${PollSeconds}s, grace ${GraceSeconds}s")

while ($true) {
    $reason = Get-ShutdownReason
    if ($reason) {
        Write-Log "conditions met ($reason); issuing shutdown in $GraceSeconds s"
        if ($DryRun) {
            Write-Log 'dry run: no shutdown issued'
            exit 0
        }
        New-Item -ItemType File -Path $flag -Force | Out-Null
        shutdown.exe /s /t $GraceSeconds /c 'QEC decoding run finished - automatic shutdown'
        Write-Log 'shutdown.exe issued (cancel with: shutdown /a)'
        exit 0
    }
    Write-Log "waiting (python=$(Get-WorkerCount), sentinel exists=$(Test-Path $Sentinel), deadline $HardDeadline, ignore-deadline=$script:IgnoreDeadline)"
    Start-Sleep -Seconds $PollSeconds
}
