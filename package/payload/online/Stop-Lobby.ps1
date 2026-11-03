param([switch]$ListOnly)
$ErrorActionPreference='Stop'
$onlineHome=[IO.Path]::GetFullPath($PSScriptRoot)
$onlinePython=[IO.Path]::GetFullPath((Join-Path $onlineHome 'runtime\python.exe'))
$onlineBroker=[IO.Path]::GetFullPath((Join-Path $onlineHome 'broker.py'))
$onlinePrefix='"'+$onlinePython+'" -I -u "'+$onlineBroker+'"'
$onlineTargets=Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
    $_.ExecutablePath -and $_.CommandLine -and
    [string]::Equals($_.ExecutablePath,$onlinePython,[StringComparison]::OrdinalIgnoreCase) -and
    $_.CommandLine.StartsWith($onlinePrefix,[StringComparison]::OrdinalIgnoreCase) -and
    ($_.CommandLine.Length -eq $onlinePrefix.Length -or [char]::IsWhiteSpace($_.CommandLine[$onlinePrefix.Length]))
}
foreach($onlineTarget in $onlineTargets) {
    if($ListOnly) { Write-Output ('Serwer tej instalacji: PID '+$onlineTarget.ProcessId);continue }
    # Stop only this installation's private image with its exact broker argument.
    $onlineProcess=Get-Process -Id $onlineTarget.ProcessId -ErrorAction SilentlyContinue
    if($onlineProcess -and [string]::Equals($onlineProcess.Path,$onlinePython,[StringComparison]::OrdinalIgnoreCase)) {
        Stop-Process -InputObject $onlineProcess -ErrorAction Stop
        Write-Output ('Zamknieto serwer tej instalacji: PID '+$onlineTarget.ProcessId)
    }
}
if(!$onlineTargets){Write-Output 'Serwery tej instalacji sa juz zamkniete.'}
