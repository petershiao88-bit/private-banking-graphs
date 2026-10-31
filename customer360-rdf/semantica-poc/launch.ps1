param(
    [ValidateSet('securities', 'business', 'ontology', 'full')]
    [string]$View = 'full',
    [int]$Port = 8866,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
& $pythonPath -X utf8 -B (Join-Path $PSScriptRoot 'export_graph.py')
if ($LASTEXITCODE -ne 0) { throw 'Graph export failed.' }
$serveArgs = @('-X', 'utf8', '-B', (Join-Path $PSScriptRoot 'serve.py'), '--view', $View, '--port', $Port)
if (-not $NoBrowser) { $serveArgs += '--open-browser' }
& $pythonPath @serveArgs
exit $LASTEXITCODE
