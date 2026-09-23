---
name: ce-bsa
description: Inspect metadata, list files, and extract BSA and BA2 archives with BSArch64.
---

# BSA and BA2 Archives

Use this skill directory as the working directory.

## Setup

```bash
mise trust mise.toml
mise install
```

## Inspect

Show the archive metadata:

```bash
mise exec -- BSArch64.exe "<archive>"
```

Show the metadata and details for each file:

```bash
mise exec -- BSArch64.exe "<archive>" -dump
```

## List files

Print one file path per line:

```bash
mise exec -- python scripts/list_paths.py "<archive>"
```

The script keeps the path order and capitalization that BSArch reports.
It changes backslashes to forward slashes.

The script returns an error if the number of file paths differs from the `Files:` count.

## Extract

Treat the input archive as read-only.
If the user does not specify a destination, use a new, empty directory in `%TEMP%`.

BSArch requires an existing destination directory:

```bash
mkdir -p "<empty-output-directory>"
mise exec -- BSArch64.exe unpack "<archive>" "<empty-output-directory>" -mt
```

BSArch can overwrite files with matching paths in an existing destination.
Always give the destination argument.
Without it, BSArch extracts files beside the input archive.
