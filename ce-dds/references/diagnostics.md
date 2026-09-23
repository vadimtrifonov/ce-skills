# Diagnostics

## Determine mip-chain completeness

Read `width`, `height`, `depth`, and `mipLevels` from `texdiag info`.
The maximum mip count is:

```text
floor(log2(max(width, height, depth))) + 1
```

This formula applies to power-of-two and non-power-of-two dimensions.
For arrays and cubemaps, `mipLevels` gives the count for each item or face.

- `mipLevels == maximum`: The chain reaches 1×1 or 1×1×1.
- `mipLevels < maximum`: The chain stops before the smallest level.
- `mipLevels == 1`: The DDS stores only the top level.

These results describe the stored subresources.
DDS does not record why a chain stops early.

## Quantify stored image data

`width`, `height`, and `depth` describe the top level.
`pixel size` is the total DirectXTex pixel-buffer size for all stored subresources.
It is not the DDS file size.

DDS metadata does not contain an intended resolution or size budget.

## Determine decoded alpha variation

Read the fourth component of each `Minimum`, `Average`, and `Maximum` tuple from `texdiag analyze`.
The component applies to the reported item and mip.

- Equal minimum and maximum values indicate constant alpha at the displayed precision.
- Different minimum and maximum values indicate varying alpha.
- For UNORM formats, `1` is the maximum representable alpha value.
- For UNORM formats, `0` is the minimum representable alpha value.

Stored `alpha mode` does not determine whether decoded alpha is constant or varying.
DDS does not record the shader's use of the alpha channel.

## Compare DDS files for the same game path

`info` and `analyze` expose related properties that MSE and PSNR do not describe:

- Dimensions
- Mip count
- Array size and topology
- Format and `_SRGB` suffix
- Stored alpha mode
- Decoded channel ranges
- `pixel size`.

`compare` measures decoded pixel error rather than complete DDS equivalence.
A zero decoded error does not prove that headers, formats, mip layouts, or compressed blocks match.

### MSE and PSNR

The first MSE value is the sum of the four values in parentheses.
The parenthesized values are the red, green, blue, and alpha MSE values.
PSNR uses the red, green, and blue MSE values.
It excludes alpha.
A larger MSE indicates more average squared error.
A larger PSNR indicates a closer RGB match.

DirectXTex linearizes RGB values from formats marked `_SRGB` before it calculates MSE.
The MSE values describe decoded floating-point channels, not compressed bytes.
`compare` prints six decimal places.
A displayed `0.000000` can hide a smaller nonzero MSE.
An infinite PSNR means that the calculated RGB error is zero.
Alpha can still differ.

A successful command can report nonzero error.
Exit code 0 means that DirectXTex calculated the metrics, not that the images match.

### Subresources

If depth, array size, mip count, and image count match, `compare` reports each stored subresource.
For multiple subresources, it also reports the minimum, average, and maximum metrics.
For 1D, 2D, array, and cubemap textures, `[item,mip]` identifies each result.
For 3D textures, `[mip,slice]` identifies each result.

If one of these values differs, `compare` uses only item 0, mip 0, and slice 0.
It prints a warning when it ignores additional subresources.

### Difference images

`diff` processes only item 0, mip 0, and slice 0.
It warns when it ignores additional subresources.
It writes absolute RGB differences and makes the output alpha opaque.
Thus, the output does not show alpha-channel differences.

An opaque `aaa1` PNG preview maps alpha into RGB and makes those differences visible to `diff`.
