param(
    [Parameter(Mandatory=$true)]
    [string]$Library,

    [Parameter(Mandatory=$false)]
    [string]$Version= "",

    [Parameter(Mandatory=$false)]
    [string]$NugetPath = "nuget",
    
    [Parameter(Mandatory=$false)]
    [string]$WorkspacePath = $PWD.Path
)

# Check if NugetPath is a file path or command name
if ($NugetPath -match '[\\/]') {
    if (-not (Test-Path $NugetPath -PathType Leaf)) {
        Write-Error "nuget.exe not found at: $NugetPath"
        exit 1
    }
} else {
    # No path separators, assume it's a command in PATH
    $command = Get-Command $NugetPath -ErrorAction SilentlyContinue
    if (-not $command) {
        Write-Error "Command '$NugetPath' not found in PATH"
        exit 1
    }
}

if (-not (Test-Path $WorkspacePath -PathType Container)) {
    Write-Error "Workspace directory not found at: $WorkspacePath"
    exit 1
}

$tempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_.FullName }
$originalLocation = Get-Location

try {
    Set-Location $tempDir
    Write-Host "Installing package ${Library}_x64..."
    
     if ($Version) {
        &$NugetPath install "${Library}_x64" -version $Version
    } else {
        &$NugetPath install "${Library}_x64"
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "NuGet install failed with exit code $LASTEXITCODE"
    }
    
    $addonSourcePath = Join-Path "${tempDir}/${Library}*" "*addon" -Resolve
    $addonDestPath = Join-Path $WorkspacePath "addon/globalPlugins/HumanwareBrailleTranslation/$Library"

    Write-Host "Moving library content from $addonSourcePath to $addonDestPath"
    if (Test-Path $addonDestPath) {
        Remove-Item $addonDestPath -Recurse -Force
    }

    Move-Item $addonSourcePath -Destination $addonDestPath -Force    
    Write-Host "$Library installed successfully!"
} 
catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    Write-Host "Error details: $error"
    exit 1
} 
finally {
    Set-Location $originalLocation
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
}