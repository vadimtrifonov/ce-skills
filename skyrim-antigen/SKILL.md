---
name: skyrim-antigen
description: Run targeted Antigen diagnostics for Skyrim plugins in MO2 profiles. Use to detect or explain record, reference, asset, worldspace, NPC, quest, dialogue, scene, package, and leveled-list issues.
---

# Skyrim Antigen

Use this skill directory as the working directory.

Antigen reports known record and load-order problems as `Suggestion`, `Warning`, `Error`, or `CTD` topics.

## Analyzer coverage

- References and assets: unresolved FormLinks; missing referenced models and textures.
- Cells and world: placement, ownership, persistence, doors, markers, duplicate references, landscape seams, and navmesh triangles.
- NPCs: appearance, race, voice, inventory, factions, packages, merchants, trainers, and unique placement.
- Lists and crafting: circular or oversized leveled lists, duplicate constructibles, tempering, and recipe consistency.
- Quests and scripting: aliases, stages, conditions, dialogue links and speakers, scene actions, package data, and VMAD fragments.
- General record lint: required fields, flags, keywords, slots, values, text, and cross-record consistency.

## Setup

```powershell
mise trust mise.toml
mise run setup
```

## Targeted MO2 scan

Select the plugins under investigation.
Keep the complete profile active and blacklist every other active plugin.
Blacklisting suppresses isolated analysis and reports for those plugins without removing them from the contextual load order.

Create a temporary run configuration from the profile's active `loadorder.txt`:

```powershell
$mo2Root = "<MO2 root>"
$profile = "<profile>"
$game = "<SkyrimSE|SkyrimVR>"
$data = "<MO2 game Data>"
$targets = @("<Target.esp>", "<Target patch.esp>")

$profileDir = Join-Path $mo2Root "profiles\$profile"
$active = Get-Content (Join-Path $profileDir "loadorder.txt") |
  ForEach-Object { $_.Trim() } |
  Where-Object { $_ -and -not $_.StartsWith("#") }

$unknown = $targets | Where-Object { $_ -notin $active }
if ($unknown) {
  throw "Inactive or missing target plugins: $($unknown -join ', ')"
}

$blacklist = $active | Where-Object { $_ -notin $targets }
$unsupported = $blacklist | Where-Object { $_.Contains(",") }
if ($unsupported) {
  throw "Antigen cannot encode blacklisted plugin names containing commas: $($unsupported -join '; ')"
}

$work = Join-Path $env:TEMP "skyrim-antigen-$([Guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $work | Out-Null
$runConfig = Join-Path $work "scope.runconfig"
$report = Join-Path $work "report.csv"
$runConfigText = if ($blacklist) {
  "environment.blacklisted_mods = $($blacklist -join ',')"
} else {
  ""
}
$runConfigText | Set-Content -Path $runConfig -Encoding utf8
```

## Record-only scan

When the investigation excludes assets, disable the BSA-blind file-existence topics before launching the targeted scan:

```powershell
@("A82", "A84", "A85", "A87", "A89", "A90", "A91", "A92") |
  ForEach-Object { "diagnostic.$_.severity = None" } |
  Set-Content -Path (Join-Path $work ".topicconfig") -Encoding utf8
```

## Run

```powershell
$cli = (Resolve-Path "tools/cli/Mutagen.Bethesda.Analyzers.Cli.exe").Path
$arguments = 'run-analyzers -g {0} -s Error --DataFolder "{1}" --RunConfigPath "{2}" -o "{3}"' -f $game, $data, $runConfig, $report
& (Join-Path $mo2Root "ModOrganizer.exe") -p $profile run -a $arguments -c $work $cli
```

Start at `Error`.
Expand to `Warning` or `Suggestion` only after reviewing the error set.
Add `--PrintTopics` to list enabled topics.

MO2 can return before the analyzer exits.
Read `$report` only after `Mutagen.Bethesda.Analyzers.Cli` is no longer running.

## Interpretation boundaries

### Assets

Topics `A82`, `A84`, `A85`, `A87`, `A89`, `A90`, `A91`, and `A92` inspect loose files only. 
With active BSAs, these topics cannot establish that an asset is missing.

### Records

Antigen reports every non-deleted definition, including losing overrides. 
A finding identifies the definition that Antigen analyzed; it does not establish that the definition is active or that the target plugin introduced the condition.

### Languages

For findings that name a language, retain the profile's active `sLanguage` unless the investigation concerns localization.

## Broad scan

Run without `--RunConfigPath` only to establish a baseline, summarize topic counts, or investigate one analyzer.
Do not present raw broad-scan rows as an actionable load-order report.

## Results

- MO2 may not relay child stdout; use CSV output.
- CSV output is headerless and appended; use a new or cleared file.
- Exit code `0` means the scan completed, even when findings exist.

To explain an `A###` topic, find its numeric ID under `tools/Antigen/Mutagen.Bethesda.Analyzers.Skyrim` and read the analyzer and test when present.
