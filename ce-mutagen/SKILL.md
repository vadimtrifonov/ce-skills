---
name: ce-mutagen
description: Create temporary C# projects against the current Mutagen source. Use for Skyrim and Starfield record inspection, synthetic plugin fixtures, and plugin generation.
---

# Mutagen

Use this skill directory as the working directory.

## Setup

```powershell
mise trust mise.toml
mise install
mise run setup
```

Setup clones or updates Mutagen's `dev` branch under `tools/Mutagen`.
Mise exposes that checkout as `MUTAGEN_ROOT`.

## Create and run a scratch project

The scratch command prints the new project directory under `%TEMP%`.
Generated projects reference the selected game's source through `MUTAGEN_ROOT`.
Run builds sequentially: project references share the checkout's build outputs.

### Skyrim

The example accepts `SkyrimSE` or `SkyrimVR` followed by a plugin path.

```powershell
$work = (mise run scratch Skyrim "<task-name>").Trim()
mise exec -- dotnet build "$work\Scratch.csproj" --nologo "-clp:ErrorsOnly"
mise exec -- dotnet run --no-build --project "$work\Scratch.csproj" -- SkyrimVR "<plugin-path>"
```

### Starfield

The example accepts a plugin path and a Data directory containing its declared masters.
It reads their header flags to determine the master styles needed to resolve FormIDs.

```powershell
$work = (mise run scratch Starfield "<task-name>").Trim()
mise exec -- dotnet build "$work\Scratch.csproj" --nologo "-clp:ErrorsOnly"
mise exec -- dotnet run --no-build --project "$work\Scratch.csproj" -- "<plugin-path>" "<data-directory>"
```

## MO2 profiles

`GameEnvironment.Typical` reads the standard game installation and load-order locations.
For an MO2 profile, supply its ordered active listings and resolved physical plugin paths explicitly.
Directory enumeration is not MO2 priority order.

For localized plugins, select the target language and resolve the winning strings independently of the plugin path.
In MO2, the plugin and strings may have different providers.

## References

- [Skyrim Patterns](references/skyrim-patterns.md)
- [Starfield Patterns](references/starfield-patterns.md)
- [Shared API Entry Points](references/shared-api-entry-points.md)
