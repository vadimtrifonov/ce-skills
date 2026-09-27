---
name: ce-nif
description: Inspect Skyrim and Starfield NIF structure, geometry, skinning, and dependencies with PyNifly. Render Skyrim PNG previews and export OBJ.
---

# NIF Inspection and Previews

Use this skill directory as the working directory.

- For Starfield inspection, read [Starfield geometry and materials](references/starfield.md).
- For Skyrim archive queries, PNG previews, or OBJ export, read [Skyrim tools](references/skyrim-tools.md).

The renderer and OBJ exporter do not support Starfield.

## Setup

```bash
mise trust mise.toml
mise install
```

## Structured report

Use the read-only PyNifly inspector on a loose Skyrim or Starfield NIF.

```bash
mise exec -- python scripts/inspect_nif.py "<input.nif>"
mise exec -- python scripts/inspect_nif.py "<input.nif>" -o "<report.json>"
```

Report outputs must use `.json`; existing files require `--force`.

Optional detail:

```bash
mise exec -- python scripts/inspect_nif.py "<input.nif>" --geometry --bones --nodes --blocks -o "<report.json>"
```

- `--geometry` loads geometry arrays and adds counts and axis-aligned mesh bounds in shape-local NIF coordinates, before node transforms.
- `--bones` includes bone names rather than counts only.
- `--nodes` includes the scene-node hierarchy.
- `--blocks` includes the ordered NIF block list.
- `--data-root "<Data>"` resolves dependencies as loose files under a supplied game or mod Data directory and supplies external geometry for `--geometry`.
  It does not search BSA/BA2 archives or material databases.

`geometry.status` is `not_loaded`, `loaded`, or `unavailable`; failures appear in `errors`.
Unknown geometry counts are `null`.
A summary vertex or triangle total is `null` if any shape's corresponding count is unknown.

Inspect both `_0.nif` and `_1.nif` members of a Skyrim weight-slider pair when relevant.
