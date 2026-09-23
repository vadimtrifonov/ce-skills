---
name: ce-psc
description: Compile Skyrim and Starfield Papyrus PSC files to PEX.
---

# Papyrus PSC

Use this skill directory as the working directory.

## Prepare

```bash
mise trust mise.toml
mise install
```

## Source imports

Use `-i` for referenced mod APIs and script-extender sources.
Common source layouts are `Scripts/Source` and `Source/Scripts`.
The helper supplies the selected game's vanilla sources and flags.

Import precedence is the input PSC's directory (the namespace root for Starfield), `-i` directories in command order, then vanilla sources.
When PSC names collide, the first provider wins.
Keep source providers separate and put active API overrides before the declarations they replace.
Match script-extender sources to the target executable, not to master-file versions.
Use mod API sources matching the installed mod version.

Imported PSCs supply declarations; their runtime implementations come from installed PEX files and native code.

### Skyrim

Skyrim uses Caprica with SE vanilla sources.
Pass the applicable sources with `-i` in this order:

1. Active API override sources.
2. Matching SKSE64 or SKSEVR sources.
3. Referenced mod API sources.
4. Referenced Creation content sources.

Script-extender sources supply declarations for extender APIs and selected core scripts.
Vanilla sources supply the remaining game declarations.
For VR, use VR-compatible native mod API sources and put overrides such as Skyrim VR ESL Support before SKSEVR sources.

### Starfield

Starfield uses Bethesda's Papyrus compiler.
For `Scriptname Example:Main`, use `Source/Example/Main.psc`.
The helper imports `Source` and writes `<output-directory>/Example/Main.pex`.

## Compile

```bash
mise exec -- python -X utf8 scripts/compile_psc.py \
  "<script.psc>" --game <skyrim|starfield> \
  -i "<highest-priority-source-directory>" \
  -i "<next-source-directory>" \
  -o "<output-directory>"
```

The helper prints the import order and emits one PEX for the input PSC.
Use `--flags` for a custom flags file.
`--force` replaces an existing PEX after successful compilation.

## References

- [Skyrim compiler limitations](references/caprica-limitations.md)
