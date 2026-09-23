[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet('Skyrim', 'Starfield')]
    [string] $Game,

    [Parameter(Position = 1)]
    [string] $TaskName = 'scratch'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
    if ([string]::IsNullOrWhiteSpace($env:MUTAGEN_ROOT)) {
        throw 'MUTAGEN_ROOT is unset; run this command through mise'
    }

    $Game = if ($Game -eq 'Skyrim') { 'Skyrim' } else { 'Starfield' }
    $mutagenProject = Join-Path $env:MUTAGEN_ROOT "Mutagen.Bethesda.$Game/Mutagen.Bethesda.$Game.csproj"
    if (-not (Test-Path -LiteralPath $mutagenProject -PathType Leaf)) {
        throw "Mutagen is not set up; run 'mise run setup' in the skill directory"
    }

    $slug = [regex]::Replace($TaskName.Trim().ToLowerInvariant(), '[^a-z0-9]+', '-').Trim('-')
    if ($slug.Length -gt 48) {
        $slug = $slug.Substring(0, 48).TrimEnd('-')
    }
    if ([string]::IsNullOrEmpty($slug)) {
        $slug = 'scratch'
    }

    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 12)
    $destination = Join-Path ([IO.Path]::GetTempPath()) "ce-mutagen-$slug-$suffix"
    [IO.Directory]::CreateDirectory($destination) | Out-Null

    $templateRoot = Join-Path (Split-Path -Parent $PSScriptRoot) 'templates'
    try {
        $project = [IO.File]::ReadAllText((Join-Path $templateRoot 'Scratch.csproj'))
        [IO.File]::WriteAllText(
            (Join-Path $destination 'Scratch.csproj'),
            $project.Replace('__GAME__', $Game))
        Copy-Item -LiteralPath (Join-Path $templateRoot "Program.$Game.cs") `
            -Destination (Join-Path $destination 'Program.cs')
    }
    catch {
        Remove-Item -LiteralPath $destination -Recurse -Force -ErrorAction SilentlyContinue
        throw
    }

    Write-Output ([IO.Path]::GetFullPath($destination))
}
catch {
    [Console]::Error.WriteLine("ERROR: $($_.Exception.Message)")
    exit 2
}
