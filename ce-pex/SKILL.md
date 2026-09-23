---
name: ce-pex
description: Inspect and decompile Skyrim and Starfield Papyrus PEX files with Champollion. Use for header metadata, PSC reconstruction, or PAS disassembly.
---

# Papyrus PEX

## Setup

```bash
mise trust mise.toml
mise install
```

## Inspect

`--print-info` prints PEX header metadata and writes no PSC or PAS.

```bash
mise exec -- Champollion.exe "<script.pex>" --print-info
```

## PSC and PAS

`--psc` reconstructs high-level Papyrus source.
PEX does not retain original formatting, parameter defaults, or comments; reconstructed quest-fragment PSC therefore lacks Creation Kit marker comments.
Expressions and control flow are inferred from PEX instructions, and Champollion 1.3.2 can omit parentheses required by the original arithmetic grouping.
For Starfield, lines marked `;***` contain guessed syntax for `Guard`, `TryGuard`, or `GetMatchingStructs`.

```bash
mise exec -- Champollion.exe "<script.pex>" --psc "<psc-output-directory>"
```

PAS is a human-readable rendering of the PEX structure and instructions.
`--asm` also emits PSC, so both output destinations are explicit here:

```bash
mise exec -- Champollion.exe "<script.pex>" --psc "<psc-output-directory>" --asm "<pas-output-directory>"
```

## Directories

Pass a directory as the input. 
Add `--recursive` to include PEX files in subdirectories. 
Add `--threaded` to process files in parallel.

```bash
mise exec -- Champollion.exe "<pex-input-directory>" --recursive --threaded --psc "<psc-output-directory>" --asm "<pas-output-directory>"
```

## Interpretation

Use reconstructed PSC to locate the properties, functions, events, and control flow that answer the current question.
Use PAS when exact instructions or native calls affect the conclusion.
A whole-file PSC text diff does not establish semantic equivalence.

Champollion derives output filenames from the PEX filename and overwrites existing same-name files.
Some parse failures return exit code `0` despite error text in stdout or stderr and no output file.
