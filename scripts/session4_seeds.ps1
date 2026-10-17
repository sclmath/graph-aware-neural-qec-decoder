<#
.SYNOPSIS
    Session 4：夜间续跑链（T6 收口 + 三组种子补点 + 表格重生成）。

.DESCRIPTION
    一次调用按固定顺序跑若干阶段，**全部幂等可续跑**（输出已存在即跳过，
    T9 的 --merge 按 arm 去重，网格本身按「结果目录存在即跳过」）：

      grid         T6 残点补齐（d=5/d=7 p=0.002 x3 seeds），走 scripts\t6_surface_grid.py
      postprocess  T6 收口三步：t10_multiseed_stats -> threshold_estimate -> engineering_table
      probes       T8 d=7 OSD-CS 探针升级为「模型 + 数据都换」：p in {0.003,0.005,0.008} x {s2,s3}
      probes-extra T8 d=7 p=0.01 探针（3 份独立测试集，s1 模型）
      ablation     表面码 d=3 消融补齐 3 条臂 x {s10,s20}（--merge 进已有 ablation.json）
      extra        M3 跨码距迁移 (d=3->d=5) 与 HGP 跨尺寸迁移的多种子
      aggregate    重生成 T8 两张表、T9 表面码多种子表与工程性能表

    用法（无人值守请一律 detached；前台窗口退出会带走子进程）：

      Start-Process -WindowStyle Hidden pwsh -ArgumentList '-NoProfile','-File','scripts\session4_seeds.ps1','-Stage','all'
      # 想跑完自动关机（300 s 宽限，期间 `shutdown /a` 可取消）：
      Start-Process -WindowStyle Hidden pwsh -ArgumentList '-NoProfile','-File','scripts\session4_seeds.ps1','-Stage','all','-ShutdownAfter'

    预演（只打印将执行的命令，不跑任何实验）：

      pwsh -File scripts\session4_seeds.ps1 -Stage all -DryRun

    日志：results\logs\session4.log（append-only；每个 python 步骤的 stdout/stderr 也写进去）

.NOTES
    * stage probes / extra 依赖 stage grid 训练出的 checkpoint：缺 checkpoint 时会跳过并
      在日志里说明，因此「网格还没跑完就重放本脚本」是安全的。
    * 旧的关机守望 scripts\shutdown_when_done.ps1 -Watch 仍可用；重新武装前必须先删
      results\logs\shutdown_issued.flag，且在 python 进程起来之后再启动守望。
#>
param(
    [ValidateSet('grid', 'postprocess', 'probes', 'probes-extra', 'ablation', 'extra', 'aggregate', 'all')]
    [string[]]$Stage = @('all'),
    [switch]$DryRun,
    [switch]$ShutdownAfter,
    [int]$ShutdownGraceSeconds = 300
)

$ErrorActionPreference = 'Continue'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONUTF8 = '1'
$py = Join-Path $PWD '.venv\Scripts\python.exe'
$script:log = 'results\logs\session4.log'

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Add-Content -Path $script:log -Value $line -Encoding utf8
}

function Invoke-Step {
    param([string[]]$Argv, [string]$Label)
    if ($DryRun) { Write-Log ("DRY-RUN  {0} :: {1}" -f $Label, ($Argv -join ' ')); return 0 }
    Write-Log ("{0} start :: python {1}" -f $Label, ($Argv -join ' '))
    $started = Get-Date
    & $py @Argv 2>&1 | Out-File -FilePath $script:log -Append -Encoding utf8
    $code = $LASTEXITCODE
    $minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    if ($code -eq 0) { Write-Log ("{0} done ({1} min)" -f $Label, $minutes) }
    else { Write-Log ("{0} FAILED exit={1} ({2} min) - see the log above" -f $Label, $code, $minutes) }
    return $code
}

function Get-FinishedRun([string]$Root, [string]$Name) {
    Get-ChildItem -Path $Root -Directory -Filter "${Name}__*" -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'results.json') } | Select-Object -First 1
}

function Test-AblationComplete([string]$Dir, [string[]]$Arms) {
    $file = Join-Path $Dir 'ablation.json'
    if (-not (Test-Path $file)) { return $false }
    $present = (Get-Content $file -Raw -Encoding UTF8 | ConvertFrom-Json).rows.arm
    $missing = @($Arms | Where-Object { $present -notcontains $_ })
    if ($missing.Count -eq 0) { return $true }
    Write-Log ("ablation {0}: still missing {1}" -f $Dir, ($missing -join ', '))
    return $false
}

$D7_SURFACE = 'results\m4_surface'
$SURFACE_D3_CFG = 'results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json'

function Invoke-GridStage {
    Write-Log '--- stage grid ---'
    # --print-plan 只读，不写结果目录；dry-run 下也照常打印，方便核对计划。
    $plan = & $py scripts\t6_surface_grid.py --print-plan 2>&1
    $pending = @($plan | Where-Object { $_ -match '\[pending\]' })
    Write-Log ("grid plan: {0} pending / {1} points" -f $pending.Count, @($plan).Count)
    foreach ($line in $pending) { Write-Log ("  pending: " + ($line -replace '^\s+', '')) }
    Invoke-Step -Argv @('scripts\t6_surface_grid.py', '--budget-minutes', '480') -Label 't6 grid' | Out-Null
}

function Invoke-PostprocessStage {
    Write-Log '--- stage postprocess ---'
    Invoke-Step -Argv @('scripts\t10_multiseed_stats.py', '--results-dir', 'results\m4_surface', '--output-dir', 'results\t10', '--min-test-shots', '4096') -Label 't10 multiseed' | Out-Null
    Invoke-Step -Argv @('scripts\threshold_estimate.py', '--inputs', 'results\t10\surface_sweep_mean.json', 'results\m4\surface_sweep.json', 'results\m4_threshold\surface_sweep.json', '--output', 'results\m4\THRESHOLD.md') -Label 'threshold estimate' | Out-Null
    Invoke-Step -Argv @('scripts\engineering_table.py', '--results-dir', 'results', '--output', 'results\m5\ENGINEERING_TABLE.md') -Label 'engineering table' | Out-Null
}

function Invoke-ProbeStage {
    Write-Log '--- stage probes (T8 d=7, model seeds) ---'
    foreach ($rate in @('p0p003', 'p0p005', 'p0p008')) {
        foreach ($seed in @(2, 3)) {
            $run = "$D7_SURFACE\m4_rotated_surface_code_circuit_level_d7_s${seed}__d7__circuit_level__$rate"
            $out = "results\t8\d7_${rate}_probe_s${seed}model"
            if (Test-Path (Join-Path $out 'STUDY.md')) { Write-Log "skip probe $rate s${seed}model (result exists)"; continue }
            if (-not (Test-Path (Join-Path $run 'model_state.pt'))) {
                Write-Log "skip probe $rate s${seed}model (no checkpoint in $run; run stage grid first)"; continue
            }
            Invoke-Step -Argv @('scripts\t8_osd_cs_study.py', '--config', "$run\config.json", '--checkpoint', "$run\model_state.pt",
                '--sweeps', '0', '4', '--test-shots', '1024', '--output-dir', $out) -Label "probe $rate s${seed}model" | Out-Null
        }
    }
}

function Invoke-ProbeExtraStage {
    Write-Log '--- stage probes-extra (T8 d=7 p=0.01, test splits) ---'
    $run = "$D7_SURFACE\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01"
    foreach ($offset in @(0, 10, 20)) {
        $out = if ($offset -eq 0) { 'results\t8\d7_p0p01_probe' } else { "results\t8\d7_p0p01_probe_s$offset" }
        if (Test-Path (Join-Path $out 'STUDY.md')) { Write-Log "skip probe p0p01 offset $offset (result exists)"; continue }
        if (-not (Test-Path (Join-Path $run 'model_state.pt'))) {
            Write-Log "skip probe p0p01 offset $offset (no checkpoint in $run; run stage grid first)"; continue
        }
        $argv = @('scripts\t8_osd_cs_study.py', '--config', "$run\config.json", '--checkpoint', "$run\model_state.pt",
            '--sweeps', '0', '4', '--test-shots', '1024', '--output-dir', $out)
        if ($offset -ne 0) { $argv += @('--seed-offset', "$offset") }
        Invoke-Step -Argv $argv -Label "probe p0p01 offset $offset" | Out-Null
    }
}

function Invoke-AblationStage {
    Write-Log '--- stage ablation (surface d=3, missing arms) ---'
    $arms = @('no_check_features', 'no_check_geometry', 'no_edge_degree')
    foreach ($offset in @(10, 20)) {
        $out = "results\t9\surface_d3_seed$offset"
        if (Test-AblationComplete $out $arms) { Write-Log "skip surface ablation seed$offset (all arms present)"; continue }
        $argv = @('scripts\t9_feature_ablation.py', '--config', $SURFACE_D3_CFG, '--output-dir', $out,
            '--arms') + $arms + @('--torch-threads', '2', '--seed-offset', "$offset", '--merge')
        Invoke-Step -Argv $argv -Label "surface ablation seed$offset" | Out-Null
    }
}

function Invoke-ExtraStage {
    Write-Log '--- stage extra (transfer multi-seeds) ---'

    # (a) M3 跨码距迁移 d=3 -> d=5：checkpoint 直接复用 M2 旗舰表的 s10/s20 运行。
    foreach ($offset in @(10, 20)) {
        $ckpt = "results\m2\m2_learned_basis_repetition_circuit_level_d3_s${offset}__d3__circuit_level__p0p01\model_state.pt"
        $tag = "m3_learned_basis_repetition_circuit_level_d3_s${offset}__from_d3__to_d5__circuit_level__p0p01"
        if (Test-Path (Join-Path "results\m3\$tag" 'results.json')) { Write-Log "skip m3 d3->d5 s$offset (result exists)"; continue }
        if (-not $DryRun -and -not (Test-Path $ckpt)) { Write-Log "skip m3 d3->d5 s$offset (missing checkpoint $ckpt)"; continue }
        Invoke-Step -Argv @('-m', 'graph_qec.m3', '--config', 'configs\m3_learned_basis_repetition_circuit_level_d3.json',
            '--checkpoint', $ckpt, '--output-dir', 'results\m3', '--tag', $tag,
            '--target-distance', '5', '--target-rounds', '5',
            '--test-seeds', "$(301 + $offset)", "$(302 + $offset)", '--test-shots', '16384',
            '--decoders', 'mwpm', 'bp', 'bp_osd', 'bp_gnn', 'bp_gnn_osd', '--timed-runs', '1') -Label "m3 transfer d3->d5 s$offset" | Out-Null
    }

    # (b) HGP 跨尺寸迁移 rep3x3 -> hamming7x7：源模型换 seed 重训，目标测试集同步换 seed。
    $srcBase = 'configs\m4_hgp_rep3x3_code_capacity_p0p05.json'
    $tgtBase = 'configs\m4_hgp_hamming7x7_code_capacity_p0p05.json'
    Invoke-Step -Argv @('scripts\m2_headline_multiseed.py', '--write-configs', '--base-config', $srcBase) -Label 'write rep3x3 seed configs' | Out-Null
    Invoke-Step -Argv @('scripts\m2_headline_multiseed.py', '--write-configs', '--base-config', $tgtBase) -Label 'write hamming7x7 seed configs' | Out-Null

    foreach ($offset in @(10, 20)) {
        $src = "configs\m4_hgp_rep3x3_code_capacity_p0p05_s$offset.json"
        $tgt = "configs\m4_hgp_hamming7x7_code_capacity_p0p05_s$offset.json"
        $tag = "hgp_rep3x3_s${offset}_to_hgp_hamming7x7"
        # 训练源模型（等价于 scripts\m2_headline_seeds.ps1 的单个 offset）。
        $runDir = Get-FinishedRun 'results\m4_hgp' "m4_hgp_rep3x3_code_capacity_p0p05_s$offset"
        if (-not $runDir) {
            if (-not $DryRun -and -not (Test-Path $src)) { Write-Log "skip hgp transfer s$offset (missing config $src)"; continue }
            Invoke-Step -Argv @('-m', 'graph_qec.m2', '--config', $src, '--output-dir', 'results\m4_hgp') -Label "train hgp rep3x3 s$offset" | Out-Null
            if (-not $DryRun) { $runDir = Get-FinishedRun 'results\m4_hgp' "m4_hgp_rep3x3_code_capacity_p0p05_s$offset" }
        } else {
            Write-Log "skip train hgp rep3x3 s$offset (exists: $($runDir.Name))"
        }
        if (Test-Path (Join-Path "results\m4\$tag" 'results.json')) { Write-Log "skip hgp transfer s$offset (result exists)"; continue }
        $ckpt = if ($runDir) { Join-Path $runDir.FullName 'model_state.pt' } else { "results\m4_hgp\m4_hgp_rep3x3_code_capacity_p0p05_s${offset}__d3__code_capacity__p0p05\model_state.pt" }
        Invoke-Step -Argv @('scripts\m4_transfer.py', '--source-config', $src, '--target-config', $tgt, '--checkpoint', $ckpt,
            '--output-dir', 'results\m4', '--tag', $tag) -Label "hgp transfer s$offset" | Out-Null
    }
}

function Invoke-AggregateStage {
    Write-Log '--- stage aggregate ---'
    Invoke-Step -Argv @('scripts\t8_d7_multiseed.py', '--probe-root', 'results\t8', '--output', 'results\t8\D7_MULTISEED.md',
        '--json', 'results\t8\d7_multiseed.json') -Label 't8 d7 test-split table' | Out-Null
    Invoke-Step -Argv @('scripts\t8_d7_model_seeds.py', '--probe-root', 'results\t8', '--output', 'results\t8\D7_MODEL_SEEDS.md') -Label 't8 d7 model-seed table' | Out-Null
    Invoke-Step -Argv @('scripts\t9_multiseed.py', '--results-dir', 'results\t9', '--prefix', 'surface_d3',
        '--output', 'results\t9\SURFACE_D3_MULTISEED.md') -Label 't9 surface d3 multiseed table' | Out-Null
    Invoke-Step -Argv @('scripts\engineering_table.py', '--results-dir', 'results', '--output', 'results\m5\ENGINEERING_TABLE.md') -Label 'engineering table' | Out-Null
}

$canonical = @('grid', 'postprocess', 'probes', 'probes-extra', 'ablation', 'extra', 'aggregate')
$selected = if ($Stage -contains 'all') { $canonical } else { @($canonical | Where-Object { $Stage -contains $_ }) }

New-Item -ItemType Directory -Force -Path 'results\logs' | Out-Null
$repoPath = (Get-Location).Path
$running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($repoPath) }).Count

Write-Log ("session4 start (pid $PID) stages=$($selected -join ',') dryrun=$($DryRun.IsPresent) shutdownAfter=$($ShutdownAfter.IsPresent)")
if ($running -gt 0) { Write-Log "WARNING: $running repo python process(es) already running - CPU contention, consider stopping them first" }

foreach ($name in $selected) {
    switch ($name) {
        'grid' { Invoke-GridStage }
        'postprocess' { Invoke-PostprocessStage }
        'probes' { Invoke-ProbeStage }
        'probes-extra' { Invoke-ProbeExtraStage }
        'ablation' { Invoke-AblationStage }
        'extra' { Invoke-ExtraStage }
        'aggregate' { Invoke-AggregateStage }
    }
}

if ($ShutdownAfter) {
    if ($DryRun) {
        Write-Log "DRY-RUN shutdown.exe /s /t $ShutdownGraceSeconds"
    } else {
        Write-Log "issuing shutdown.exe /s /t $ShutdownGraceSeconds (cancel with: shutdown /a)"
        shutdown.exe /s /t $ShutdownGraceSeconds /c 'QEC session4 chain finished - automatic shutdown'
    }
}

Write-Log 'session4 finished'