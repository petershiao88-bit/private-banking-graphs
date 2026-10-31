$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$stateDir = Join-Path $projectRoot '.local_runtime\graph'
Set-Location -LiteralPath $projectRoot
python -X utf8 local_graph/bootstrap.py
if ($LASTEXITCODE -ne 0) { throw 'Local graph startup failed.' }
try { $bridgeReady = (Invoke-RestMethod 'http://127.0.0.1:18780/health').status -eq 'ready' } catch { $bridgeReady = $false }
if (-not $bridgeReady) {
    $pythonPath = (Get-Command python).Source
    $bridge = Start-Process -FilePath $pythonPath -ArgumentList @('-X','utf8','local_graph/query_service.py') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $stateDir 'bridge.stdout.log') -RedirectStandardError (Join-Path $stateDir 'bridge.stderr.log') -PassThru
    $bridge.Id | Set-Content (Join-Path $stateDir 'bridge.pid')
}
$tunnelPath = Join-Path $stateDir 'tunnel.json'
$tunnelReady = $false
if (Test-Path -LiteralPath $tunnelPath) {
    $savedTunnel = Get-Content -LiteralPath $tunnelPath -Raw | ConvertFrom-Json
    try { $tunnelReady = (Invoke-RestMethod ($savedTunnel.url + '/health') -TimeoutSec 10).status -eq 'ready' } catch {}
}
if (-not $tunnelReady) {
    $logPath = Join-Path $stateDir ('tunnel-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    $cloudflared = Join-Path $projectRoot '.local_runtime\tools\cloudflared.exe'
    $tunnel = Start-Process -FilePath $cloudflared -ArgumentList @('tunnel','--no-autoupdate','--protocol','http2','--url','http://127.0.0.1:18780','--logfile',$logPath) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    $tunnel.Id | Set-Content (Join-Path $stateDir 'tunnel.pid')
    $bridgeUrl = $null
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        if (Test-Path -LiteralPath $logPath) {
            $logText = Get-Content -LiteralPath $logPath -Raw
            if ($logText -match 'https://[a-z0-9-]+\.trycloudflare\.com') { $bridgeUrl=$Matches[0]; break }
        }
        Start-Sleep -Seconds 1
    }
    if (-not $bridgeUrl) { throw 'Tunnel URL was not available. Check the private tunnel log.' }
    @{url=$bridgeUrl;userApproved=$true;temporaryUrl=$true} | ConvertTo-Json | Set-Content -LiteralPath $tunnelPath -Encoding utf8
} else { $bridgeUrl=$savedTunnel.url }
python -X utf8 local_graph/build_cloud_workflow.py --bridge-url $bridgeUrl
if ($LASTEXITCODE -ne 0) { throw 'Workflow generation failed.' }
Write-Host 'Local graph and bridge are running.'
Write-Host 'If the tunnel URL changed, import .local_runtime/graph/workflow.bridge-single.json into the existing n8n workflow.'
