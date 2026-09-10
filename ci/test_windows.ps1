param(
    [Parameter(Mandatory = $true)]
    [string]$QgisPython,

    [Parameter(Mandatory = $true)]
    [string]$ProfileDirectory
)

$ErrorActionPreference = "Stop"

function Invoke-QgisPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $QgisPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (exit $LASTEXITCODE)"
    }
}

$repository = Split-Path -Path $PSScriptRoot -Parent
$qgisBin = Split-Path -Path $QgisPython -Parent
$qgisPath = Split-Path -Path $qgisBin -Parent
$pluginPath = Join-Path $env:APPDATA "QGIS\$ProfileDirectory\profiles\default\python\plugins"
$aeqPath = Join-Path $pluginPath "qaequilibrae"

Copy-Item (Join-Path $repository "qaequilibrae") -Destination $aeqPath -Recurse
Copy-Item (Join-Path $repository "test") -Destination (Join-Path $pluginPath "test") -Recurse

$env:PYTHONPATH = Join-Path $qgisPath "apps\qgis\python"
$env:QT_QPA_PLATFORM = "offscreen"

Invoke-QgisPython -Arguments @("-m", "pip", "install", "-r", (Join-Path $pluginPath "test\requirements_test.txt")) `
    -FailureMessage "Installing the test requirements failed"

Push-Location $aeqPath
try {
    Invoke-QgisPython -Arguments @("download_extra_packages_class.py") -FailureMessage "Downloading the plugin dependencies failed"
}
finally {
    Pop-Location
}

$aon = Get-ChildItem -Path (Join-Path $aeqPath "packages\aequilibrae\paths\cython") -Filter "AoN*.pyd" -ErrorAction SilentlyContinue
if (-not $aon) {
    throw "AequilibraE installed without its compiled extensions; import aequilibrae.paths will fail"
}

# uv can resolve wheels for another interpreter. Verify the extension ABI before collection.
$pyDir = (Get-ChildItem -Path (Join-Path $qgisPath "apps") -Filter "Python3*" -Directory | Select-Object -First 1).Name
$expected = "cp" + $pyDir.Substring(6)
if ($aon.Name -notlike "*$expected*") {
    throw "AequilibraE was built for the wrong Python: got $($aon.Name), but QGIS runs $pyDir (expected $expected)"
}
Write-Host "AequilibraE compiled extension present: $($aon.Name) (matches $pyDir)"

$env:PYTHONPATH = "$env:PYTHONPATH;$pluginPath;$aeqPath\packages"
Push-Location $pluginPath
try {
    Invoke-QgisPython -Arguments @("-m", "pytest", "test") -FailureMessage "Pytest failed"
}
finally {
    Pop-Location
}
