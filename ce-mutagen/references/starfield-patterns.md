# Starfield Patterns

## Read a plugin

A read-only overlay parses records lazily and keeps the input open.
Starfield imports require each master's `Full`, `Medium`, or `Small` style to resolve FormIDs.
With masters in one Data directory, read their styles from the files listed in the plugin header:

```csharp
using Mutagen.Bethesda.Starfield;

using var mod = StarfieldMod.Create(StarfieldRelease.Starfield)
    .FromPath(pluginPath)
    .WithLoadOrderFromHeaderMasters()
    .WithDataFolder(dataFolder)
    .Construct();
```

Add `.Mutable()` before `.Construct()` only when modifying the imported plugin.
Mutable import parses the complete file.

At source revision `4fd4f9c64`, `CombatStyle.OffensiveMult` and `DefensiveMult` decode float32 bytes as UInt-normalized percentages.

### Masters in separate directories

For an MO2 profile, read master styles from its resolved `ModPath` values:

```csharp
using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins.Records;
using Mutagen.Bethesda.Starfield;

var masterStyles = orderedProviders
    .Select(path => KeyedMasterStyle.FromPath(path, GameRelease.Starfield))
    .ToArray();

using var mod = StarfieldMod.Create(StarfieldRelease.Starfield)
    .FromPath(pluginPath)
    .WithKnownMasters(masterStyles)
    .Construct();
```

Master styles come from header flags, not filename extensions.
The style list must cover every declared master of the imported plugin.

## Read localized strings

```csharp
using Mutagen.Bethesda.Strings;
using Mutagen.Bethesda.Starfield;

using var mod = StarfieldMod.Create(StarfieldRelease.Starfield)
    .FromPath(pluginPath)
    .WithLoadOrderFromHeaderMasters()
    .WithDataFolder(dataFolder)
    .WithStringsFolder(stringsFolder)
    .WithTargetLanguage(Language.English)
    .Construct();
```

`WithStringsFolder` overrides the loose strings directory but does not disable archive lookup.
`WithBsaFolder` overrides the directory searched for applicable archives.

For an MO2 profile, resolve the plugin, loose string files, and applicable archives according to profile priority; they can have different providers.

## Use stable record identities

```csharp
using Mutagen.Bethesda.Plugins;

var modKey = ModKey.FromFileName("Source.esm");
var formKey = FormKey.Factory("000800:Source.esm");
```

A FormKey contains the originating ModKey and local FormID.
It does not contain a runtime load-order index.

## Build and query a link cache

Create an immutable link cache when its backing mods will not gain or lose records.
Here, `orderedProviders` is a sequence of resolved `ModPath` values in load-order order:

```csharp
using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins.Order;
using Mutagen.Bethesda.Plugins.Records;
using Mutagen.Bethesda.Starfield;

var masterStyles = orderedProviders
    .Select(path => KeyedMasterStyle.FromPath(path, GameRelease.Starfield))
    .ToArray();
var listings = orderedProviders
    .Select(provider => StarfieldMod.Create(StarfieldRelease.Starfield)
        .FromPath(provider)
        .WithKnownMasters(masterStyles)
        .Construct())
    .Select(mod => new ModListing<IStarfieldModGetter>(mod))
    .ToArray();

using var loadOrder = new LoadOrder<ModListing<IStarfieldModGetter>>(listings);
var linkCache = loadOrder.ToImmutableLinkCache();
```

Disposing the load order disposes its plugin overlays.

- `TryResolve` reports an unresolved optional link without throwing.
- `Resolve` throws when the record is absent.
- `ResolveAllContexts` returns the selected record's definitions and their provider ModKeys.
- Use context APIs to preserve provider and nesting information when overriding nested records such as cells and placed references.

Use a mutable link cache when adding or removing records from an output mod included in the cache.

## Create records and overrides

```csharp
using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins;
using Mutagen.Bethesda.Starfield;

var output = new StarfieldMod(
    ModKey.FromFileName("My Patch.esm"),
    StarfieldRelease.Starfield);

var patchedNpc = output.Npcs.GetOrAddAsOverride(sourceNpc);
patchedNpc.Name = "New Name";
```

`GetOrAddAsOverride` preserves the source FormKey.
Duplication creates a new FormKey instead.

## Write a plugin

For a patch, supply the load order that should determine master ordering.
Use mod objects carrying master styles, such as the load order constructed above:

```csharp
await output.BeginWrite
    .ToPath(outputPath)
    .WithLoadOrder(loadOrder)
    .WriteAsync();
```

When supplying only ModKeys, add `WithDataFolder` so the writer can read the master flags.
Mutagen derives required masters from emitted records unless the write builder is configured otherwise.
`Atmosphere.REFL` and `ReflectionDiff` contain opaque bytes; changing the master list does not remap embedded FormIDs.

For a masterless synthetic plugin, choose `WithNoLoadOrder()`:

```csharp
await output.BeginWrite
    .ToPath(outputPath)
    .WithNoLoadOrder()
    .WriteAsync();
```

## Check written plugins

Checks against the in-memory output do not exercise binary serialization.
Reopen the written plugin with the master-style context used for its inputs:

```csharp
using var written = StarfieldMod.Create(StarfieldRelease.Starfield)
    .FromPath(outputPath)
    .WithKnownMasters(masterStyles)
    .Construct();
```

For localized output, also provide its strings folder and target language before `.Construct()`.

## Compare records

Mutagen documents generated equality and translation masks as work in progress.
Generated traversal can be incomplete for nested records.

Do not use `Equals`, `GetEqualsMask`, or a `TranslationMask` as a generic compatibility test.
Compare the required fields directly.
If generated equality is required, inspect its implementation for the exact record type.
