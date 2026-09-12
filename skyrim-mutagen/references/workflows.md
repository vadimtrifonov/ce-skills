# Common Mutagen Patterns

## Read a plugin

A read-only overlay parses records lazily and keeps the input open:

```csharp
using Mutagen.Bethesda.Skyrim;

using var mod = SkyrimMod.Create(SkyrimRelease.SkyrimVR)
    .FromPath(pluginPath)
    .Construct();
```

Add `.Mutable()` before `.Construct()` only when modifying the imported plugin.
Mutable import parses the complete file.

## Read localized strings

```csharp
using Mutagen.Bethesda.Strings;
using Mutagen.Bethesda.Skyrim;

using var mod = SkyrimMod.Create(SkyrimRelease.SkyrimVR)
    .FromPath(pluginPath)
    .WithStringsFolder(stringsFolder)
    .WithTargetLanguage(Language.English)
    .Construct();
```

`WithStringsFolder` overrides the loose strings directory but does not disable BSA lookup.
`WithBsaFolder` overrides the directory searched for applicable BSAs.

For an MO2 profile, resolve the plugin, loose string files, and applicable archives according to profile priority; they can have different providers.

## Use stable record identities

```csharp
using Mutagen.Bethesda.Plugins;

var modKey = ModKey.FromFileName("Skyrim.esm");
var formKey = FormKey.Factory("03372B:Skyrim.esm");
```

A FormKey contains the originating ModKey and local FormID.
It does not contain a runtime load-order index.

## Build and query a link cache

Create an immutable link cache when its backing mods will not gain or lose records:

```csharp
var linkCache = listedMods.ToImmutableLinkCache();
```

When plugins come from different directories, open the resolved `ModPath` values in load-order order:

```csharp
using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins;
using Mutagen.Bethesda.Plugins.Order;
using Mutagen.Bethesda.Skyrim;

var listings = orderedProviders
    .Select(provider => SkyrimMod.Create(release).FromPath(provider).Construct())
    .Select(mod => new ModListing<ISkyrimModGetter>(mod))
    .ToArray();

using var loadOrder = new LoadOrder<ModListing<ISkyrimModGetter>>(listings);
var linkCache = loadOrder.ToImmutableLinkCache();
```

Here, `orderedProviders` is a sequence of `ModPath` values.
Disposing the load order disposes its plugin overlays.

- `TryResolve` reports an unresolved optional link without throwing.
- `Resolve` throws when the record is absent.
- `ResolveAllContexts` returns the selected record's definitions and their provider ModKeys.
- Use context APIs to preserve provider and nesting information when overriding nested records such as cells and placed references.

Use a mutable link cache when adding or removing records from an output mod included in the cache.

### Location reference lists

`LocationExt.All*` can omit references added by the provider you pass in and retain references removed by later overrides.
It skips `highestOverrideModKey` and processes preceding definitions newest-first.

## Create records and overrides

Polymorphic groups require a concrete record variant.
For example, create a Skyrim GLOB with `AddNewShort`, `AddNewFloat`, or `AddNewInt`; equal displayed values can have different binary types.

```csharp
using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins;
using Mutagen.Bethesda.Skyrim;

var output = new SkyrimMod(
    ModKey.FromFileName("My Patch.esp"),
    SkyrimRelease.SkyrimVR);

var patchedNpc = output.Npcs.GetOrAddAsOverride(sourceNpc);
patchedNpc.Name = "New Name";
```

`GetOrAddAsOverride` preserves the source FormKey.
Duplication creates a new FormKey instead.

## Write a plugin

For a patch, supply the load order that should determine master ordering:

```csharp
await output.BeginWrite
    .ToPath(outputPath)
    .WithLoadOrder(loadOrder)
    .WriteAsync();
```

Mutagen derives required masters from emitted records unless the write builder is configured otherwise.

For a masterless synthetic plugin, choose `WithNoLoadOrder()`:

```csharp
await output.BeginWrite
    .ToPath(outputPath)
    .WithNoLoadOrder()
    .WriteAsync();
```

## Check written plugins

Checks against the in-memory output do not exercise binary serialization.
Reopen the written plugin before checking it:

```csharp
using var written = SkyrimMod.Create(release)
    .FromPath(outputPath)
    .Construct();
```

For localized output, also provide its strings folder and target language before `.Construct()`.

## Compare records

Mutagen documents generated equality and translation masks as work in progress.
Generated traversal can be incomplete for nested records.

Do not use `Equals`, `GetEqualsMask`, or a `TranslationMask` as a generic compatibility test.
Compare the required fields directly.
If generated equality is required, inspect its implementation for the exact record type.
