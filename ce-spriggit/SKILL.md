---
name: ce-spriggit
description: Serialize or rebuild Skyrim and Starfield plugins with Spriggit. Use to list major records, retrieve complete records by FormKey, or compare override definitions that share a FormKey.
---

# Spriggit

Use this skill directory as the working directory.

## Setup

```bash
mise trust mise.toml
mise install
```

## Serialize

Use a clean, dedicated output directory.
Use `<ModName>.spriggit` as the directory name.

```bash
mise exec -- Spriggit.CLI.exe serialize --InputPath "<plugin>" --OutputPath "<ModName>.spriggit" --GameRelease <SkyrimSE|SkyrimVR|Starfield> --PackageName Spriggit.Json --PackageVersion <version>
```

For Starfield, add `--DataFolder "<data-directory>"` containing the masters and their dependencies.
Alternatively, specify their `Full`, `Medium`, or `Small` styles in a [`.spriggit` configuration](https://mutagen-modding.github.io/Spriggit/spriggit-file/#known-masters).
Place that file above the output directory, not inside it.

Starfield reflection data such as `ATMO.REFL` remains opaque hex.
Changing the master list does not automatically remap FormIDs inside those bytes.

Spriggit stores translation-package executables under `%TEMP%\Spriggit`.
An incomplete cache can cause a missing `Spriggit.Json.<Game>.exe` error.
If the missing executable path is under `%TEMP%\Spriggit`, remove the cache.
Spriggit restores the translation package during the next serialization.

## List records

```bash
mise exec -- python scripts/list_records.py "<ModName>.spriggit" > "<ModName>.records.jsonl"
```

The output includes records embedded in cells and worldspaces, such as placed references, landscapes, and navigation meshes.

Each line contains these fields:

- `type`
- `formKey`
- `editorId`
- `kind`: `new` or `override`
- `deleted`

The helper does not load masters or identify conflicts.

## Get records

Get one record:

```bash
mise exec -- python scripts/get_record.py "<ModName>.spriggit" "<FormKey>"
```

Get many records:

```bash
mise exec -- python scripts/get_record.py "<ModName>.spriggit" --formkeys-from "<path|->"
```

Batch input contains one FormKey per line.
`-` reads standard input.

Batch mode preserves input order and emits JSONL.
If an input or lookup error occurs, batch mode produces no output.

Each result contains the source file, its internal path, and the complete record object.
Lookup matches the object's own `FormKey`, not references.

## Deserialize

Package and game metadata are read from the serialized tree.
Starfield requires the same master context as serialization.

```bash
mise exec -- Spriggit.CLI.exe deserialize --InputPath "<ModName>.spriggit" --OutputPath "<plugin>"
```

## References

- [Record Comparison](references/record-comparison.md) - Compare override definitions with one FormKey.
