---
name: ce-dds
description: Inspect, compare, and preview DDS textures with DirectXTex. Use for metadata, decoded channel and alpha analysis, MSE and PSNR comparison, difference images, and PNG previews.
---

# DDS Textures

## Setup

```bash
mise trust mise.toml
mise install
```

At the legacy Windows path limit, ordinary paths can fail as not found.
Both tools accept `\\?\C:\...` extended-length paths.

## Metadata

`info` reports dimensions, mip and array counts, normalized DXGI format, topology, and stored alpha mode.

```bash
mise exec -- texdiag.exe info -nologo "<texture.dds>"
```

A newline-delimited path list produces the same report:

```bash
mise exec -- texdiag.exe info -nologo -flist "<dds-paths.txt>"
```

A file-list run stops at the first path that cannot be loaded.
Legacy FourCC formats are normalized to DXGI names, such as DXT1 to `BC1_UNORM` and DXT5 to `BC3_UNORM`; the original header form is not reported.
`alpha mode` is DDS metadata; `Unknown` does not mean decoded alpha is absent.

## Channel analysis

`analyze` reports decoded channel statistics for each array item and mip.

```bash
mise exec -- texdiag.exe analyze -nologo "<texture.dds>"
```

`Variance` is an unnormalized sum of squared deviations; `Std Dev` is its square root.
Population variance is `Variance / pixel count`.
The fourth component of each channel tuple is decoded alpha.

## DDS comparison

`compare` reports mean-squared error (MSE) for the decoded RGBA channels.
It also reports peak signal-to-noise ratio (PSNR) for RGB.

```bash
mise exec -- texdiag.exe compare -nologo "<first.dds>" "<second.dds>"
```

`diff` creates an image of the absolute RGB differences.

```bash
mise exec -- texdiag.exe diff -nologo -o "<difference.png>" "<first.dds>" "<second.dds>"
```

Both commands require equal top-level width and height.
Without `-y`, `diff` does not replace an existing output file.

## PNG preview

`texconv` decodes the top mip at its stored dimensions to PNG without modifying the DDS.
The output directory must exist.
Without `-y`, an existing output file is not replaced.

```bash
mise exec -- texconv.exe -nologo -ft png -m 1 -o "<output-directory>" "<texture.dds>"
```

`--swizzle aaa1` copies decoded alpha to RGB and makes the PNG opaque:

```bash
mise exec -- texconv.exe -nologo -ft png -m 1 --swizzle aaa1 -sx _alpha -o "<output-directory>" "<texture.dds>"
```

PNG represents only the first face or item of a cubemap or array.
It is an 8-bit display view rather than a lossless representation of floating-point or HDR data.

## Reference

- [Diagnostics](references/diagnostics.md) — Mip-chain completeness, stored image data, alpha interpretation, MSE and PSNR, and difference images.
