# Instala o vigia de temperatura no Windows 10/11. Rode uma vez (ou "python instalar.py vigia"); ele pede administrador sozinho.
# 1) LibreHardwareMonitor em _sistema\_ferramentas: usa o zip que estiver lá ou baixa a última versão do GitHub do projeto;
# 2) .NET 10 Desktop Runtime, se faltar (instalador oficial da Microsoft, com a assinatura conferida);
# 3) tarefa agendada "Vigia de temperatura - cortes" (ao entrar no Windows, privilégios máximos) e a inicia.
# Por que administrador: o Windows só libera a leitura dos sensores e o congelamento de processos assim.
$ErrorActionPreference = 'Stop'
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$PSCommandPath`""; exit
}
$sis = $PSScriptRoot
# Python do cofre: config.json desta máquina, senão ~/.cortes-de-video.json
$pyc = $null
foreach ($f in @((Join-Path $sis 'config.json'), (Join-Path $env:USERPROFILE '.cortes-de-video.json'))) {
    if (-not $pyc -and (Test-Path $f)) { $j = Get-Content -Raw -Encoding UTF8 $f | ConvertFrom-Json; if ($j.python) { $pyc = $j.python } }
}
if (-not $pyc) { throw 'Não achei o Python do cofre (config.json ou ~/.cortes-de-video.json).' }
$py = Join-Path (Split-Path $pyc) 'pythonw.exe'
if (-not (Test-Path $py)) { $py = $pyc }
$fer = Join-Path $sis '_ferramentas'; $lhm = Join-Path $fer 'LibreHardwareMonitor'
New-Item -ItemType Directory -Force $fer | Out-Null
if (-not (Test-Path (Join-Path $lhm 'LibreHardwareMonitor.exe'))) {
    $zip = Get-ChildItem $fer -Filter 'LibreHardwareMonitor*.zip' -ErrorAction SilentlyContinue | Select -First 1
    if (-not $zip) {
        $dest = Join-Path $fer 'LibreHardwareMonitor.NET.10.zip'
        try { Invoke-WebRequest 'https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest/download/LibreHardwareMonitor.NET.10.zip' -OutFile $dest -UseBasicParsing; $zip = Get-Item $dest }
        catch { throw "Baixe o LibreHardwareMonitor em https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases e ponha o .zip em $fer" }
    }
    Expand-Archive $zip.FullName -DestinationPath $lhm -Force
}
Get-ChildItem $lhm -Recurse | Unblock-File
$cfgLhm = Get-Content -Raw (Join-Path $lhm 'LibreHardwareMonitor.runtimeconfig.json') -ErrorAction SilentlyContinue
if ($cfgLhm -match '"version":\s*"10\.') {
    $rt = & dotnet --list-runtimes 2>$null | Out-String
    if ($rt -notmatch 'WindowsDesktop\.App 10\.') {
        $exe = Join-Path $env:TEMP 'windowsdesktop-runtime-10-win-x64.exe'
        Invoke-WebRequest 'https://aka.ms/dotnet/10.0/windowsdesktop-runtime-win-x64.exe' -OutFile $exe -UseBasicParsing
        $s = Get-AuthenticodeSignature $exe
        if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Microsoft Corporation') { throw 'Assinatura do instalador do .NET inválida' }
        Start-Process $exe -ArgumentList '/install','/quiet','/norestart' -Wait
    }
}
$user = "$env:USERDOMAIN\$env:USERNAME"
$a  = New-ScheduledTaskAction -Execute $py -Argument "`"$(Join-Path $sis 'vigia_temperatura.py')`"" -WorkingDirectory $sis
$t  = New-ScheduledTaskTrigger -AtLogOn -User $user
$p  = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest
$st = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'Vigia de temperatura - cortes' -Action $a -Trigger $t -Principal $p -Settings $st -Force | Out-Null
Start-ScheduledTask -TaskName 'Vigia de temperatura - cortes'
