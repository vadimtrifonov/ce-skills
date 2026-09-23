[CmdletBinding()]
param(
    [switch] $Integration
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$skillRoot = Split-Path -Parent $PSScriptRoot
$scratchScript = Join-Path $skillRoot 'scripts/New-Scratch.ps1'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source

function Assert-True {
    param(
        [bool] $Condition,
        [string] $Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-Checked {
    param(
        [string] $FilePath,
        [string[]] $ArgumentList = @(),
        [int] $ExpectedExitCode = 0
    )

    $output = & $FilePath @ArgumentList 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne $ExpectedExitCode) {
        throw "Command failed with exit code $exitCode (expected $ExpectedExitCode): $FilePath $($ArgumentList -join ' ')`n$output"
    }
    return $output
}

function New-TestScratch {
    param([string] $Game, [string] $TaskName)

    $output = Invoke-Checked -FilePath $pwsh -ArgumentList @(
        '-NoProfile', '-NonInteractive', '-File', $scratchScript, $Game, $TaskName
    )
    return [IO.Path]::GetFullPath($output.Trim())
}

$cleanup = [Collections.Generic.List[string]]::new()
try {
    foreach ($game in 'Skyrim', 'Starfield') {
        $work = New-TestScratch -Game $game -TaskName 'Record Audit'
        $cleanup.Add($work)

        $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd([IO.Path]::DirectorySeparatorChar)
        $parent = (Split-Path -Parent $work).TrimEnd([IO.Path]::DirectorySeparatorChar)
        Assert-True ($parent -eq $tempRoot) 'Scratch project was not created directly under the system temp directory'
        Assert-True ((Split-Path -Leaf $work).StartsWith('ce-mutagen-record-audit-')) 'Scratch directory name does not contain the task slug'

        $actualNames = @(
            Get-ChildItem -LiteralPath $work -File |
                Sort-Object Name |
                Select-Object -ExpandProperty Name
        )
        Assert-True (($actualNames -join ',') -eq 'Program.cs,Scratch.csproj') "Unexpected scaffold files: $($actualNames -join ', ')"
        $project = Join-Path $work 'Scratch.csproj'
        $program = Join-Path $work 'Program.cs'
        $inspectionSource = [IO.File]::ReadAllText($program)
        [xml] $projectXml = [IO.File]::ReadAllText($project)
        $expectedReference = '$(MUTAGEN_ROOT)/Mutagen.Bethesda.{0}/Mutagen.Bethesda.{0}.csproj' -f $game
        Assert-True ($projectXml.Project.ItemGroup.ProjectReference.Include -ceq $expectedReference) 'Wrong game project reference'
        Assert-True ($inspectionSource.Contains("using Mutagen.Bethesda.$game;")) 'Wrong game inspection template'
        Write-Output "PASS: $game scratch scaffold"

        if (-not $Integration) {
            continue
        }

        $dotnet = (Get-Command dotnet -ErrorAction Stop).Source
        $artifacts = Join-Path $work 'artifacts'
        $buildArgs = @('build', $project, '--nologo', '-clp:ErrorsOnly',
            '--artifacts-path', $artifacts, '-p:GeneratePackageOnBuild=false')
        $runArgs = @('run', '--no-build', '--project', $project, '--artifacts-path', $artifacts)
        Invoke-Checked -FilePath $dotnet -ArgumentList $buildArgs | Out-Null
        $usage = Invoke-Checked -FilePath $dotnet -ExpectedExitCode 2 -ArgumentList $runArgs
        Assert-True ($usage -match 'Usage: Scratch') 'Inspection template did not print its usage message'

        $writeSmoke = Join-Path $PSScriptRoot "fixtures/WriteSmoke.$game.cs"
        [IO.File]::WriteAllText($program, [IO.File]::ReadAllText($writeSmoke))
        Invoke-Checked -FilePath $dotnet -ArgumentList $buildArgs | Out-Null
        $writeResult = Invoke-Checked -FilePath $dotnet -ArgumentList ($runArgs + @('--', $work))
        Assert-True ($writeResult -match 'write smoke passed') 'Write smoke test did not report success'

        [IO.File]::WriteAllText($program, $inspectionSource)
        Invoke-Checked -FilePath $dotnet -ArgumentList $buildArgs | Out-Null
        if ($game -eq 'Skyrim') {
            foreach ($release in 'SkyrimSE', 'SkyrimVR') {
                $result = Invoke-Checked -FilePath $dotnet -ArgumentList (
                    $runArgs + @('--', $release, (Join-Path $work 'WriteSmokePatch.esp')))
                Assert-True ($result -match "WriteSmokePatch\.esp\s+$release") "$release inspection failed"
            }
        }
        else {
            $result = Invoke-Checked -FilePath $dotnet -ArgumentList (
                $runArgs + @('--', (Join-Path $work 'WriteSmokePatch.esm'), $work))
            Assert-True ($result -match 'WriteSmokePatch\.esm\s+Starfield') 'Starfield inspection failed'
        }
        Write-Output "PASS: $game inspection and write workflows"
    }
}
finally {
    foreach ($path in $cleanup) {
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}
