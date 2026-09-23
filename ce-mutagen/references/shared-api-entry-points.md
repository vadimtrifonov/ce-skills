# Shared API Entry Points

These APIs apply to Skyrim and Starfield.
In model names and paths, `<Game>` means `Skyrim` or `Starfield`.
The canonical documentation is under `tools/Mutagen/docs`; start with `Big-Cheat-Sheet.md`.

| Task | Entry points | Why they matter | Reference |
| --- | --- | --- | --- |
| Read one plugin | `<Game>Mod.Create`, `FromPath`, `Construct`, `Mutable` | Read-only construction creates a lazy overlay; `Mutable` imports the complete plugin for editing. | `plugins/Importing.md` |
| Read localized strings | `WithStringsFolder`, `WithBsaFolder`, `WithTargetLanguage`, `TranslatedString` | Controls loose-string and archive lookup locations and selects the language returned by translated fields. | `plugins/Importing.md`, `Strings.md`, `Mutagen.Bethesda.Core/Plugins/Binary/Translations/BinaryReadBuilder.cs` |
| Read only header masters | `MasterReferenceCollection.FromPath` | Retrieves the current ModKey and master list without importing the complete plugin. | `Big-Cheat-Sheet.md` |
| Build a single-Data-folder environment | `GameEnvironment.Typical.Builder`, `WithTargetDataFolder`, `WithLoadOrder`, `TransformLoadOrderListings`, `WithOutputMod` | Supplies Data-folder, load-order, filtering, and output-mod context. | `environment/Environment-Construction.md` |
| Build a load order from resolved plugin files | `ModPath`, `ModListing<T>`, `LoadOrder<T>`, `ToImmutableLinkCache` | Combines plugins from different physical directories after provider resolution. | `Mutagen.Bethesda.Core/Plugins/Order/ModListing.cs`, `Mutagen.Bethesda.Core/Plugins/Order/LoadOrder.cs` |
| Enumerate plugin records | `EnumerateMajorRecords`, `EnumerateMajorRecordContexts` | Walks top-level and nested major records without selecting every record group separately. | Generated `<Game>Mod_Generated.cs` |
| Select active definitions | `WinningOverrides`, `WinningContextOverrides` | Returns one winner per FormKey; context variants retain the provider and nested-record path. | `loadorder/Winning-Overrides.md`, `linkcache/ModContexts.md` |
| Resolve links and chains | `ToImmutableLinkCache`, `ToMutableLinkCache`, `TryResolve`, `Resolve`, `ResolveAll`, `ResolveAllContexts` | Resolves FormKeys and FormLinks against listed mods or retrieves a selected override chain. | `linkcache/index.md`, `linkcache/Record-Resolves.md`, `linkcache/Previous-Override-Iteration.md` |
| Read definitions before a provider | `GetPreviousOverrides`, `GetPreviousOverrideSimpleContexts`, `GetPreviousOverrideContexts` | Returns records before the supplied provider, newest-to-oldest by default; context variants retain provider identity. | `Mutagen.Bethesda.Core/Plugins/Cache/LinkCacheOverridesMixIn.cs` |
| Create or copy records | Group `AddNew`, `DuplicateInAsNewRecord`, `Duplicate`, `GetOrAddAsOverride`, `DeepCopy` | Distinguishes new FormKeys, duplicates, and overrides that preserve the source FormKey. | `plugins/Create,-Duplicate,-and-Override.md` |
| Keep generated FormKeys stable | `TextFileFormKeyAllocator`, `TextFileSharedFormKeyAllocator` | Persists EditorID-to-FormID assignments between runs. This API is marked experimental. | `plugins/FormKey-Allocation-and-Persistence.md` |
| Write a plugin | `BeginWrite`, `ToPath`, `WithLoadOrder`, `WithNoLoadOrder`, `WithExtraIncludedMasters`, `WithExplicitOverridingMasterList` | Controls destination, required-master discovery, and master ordering; `WithNoLoadOrder` is the explicit choice for a masterless synthetic plugin. | `plugins/Exporting.md`, `Mutagen.Bethesda.Core/Plugins/Binary/Translations/BinaryWriteBuilder.cs` |
| Inspect record equality | `Equals`, `GetEqualsMask`, generated `TranslationMask` classes | Compares generated fields or limits comparison to selected fields. Equality is work in progress, and nested traversal can be incomplete. | `plugins/Equality-Checks.md`, `plugins/Translation-Masks.md` |
| Enumerate record asset paths | `EnumerateAllAssetLinks`, `EnumerateListedAssetLinks`, `AssetLinkQuery`, `CreateImmutableAssetLinkCache` | Exposes listed, inferred, and FormLink-resolved assets as Data-relative paths. | `plugins/AssetLink.md` |

## Record source

Record source is under `tools/Mutagen/Mutagen.Bethesda.<Game>`.
Search `<RecordName>_Generated.cs` for exact interfaces, property types, and concrete variants.
Projects ending in `.UnitTests` contain examples of behavior not specified by the documentation.

When an interface accepts several concrete implementations, inspect those implementations before constructing a replacement value.
Equal displayed values can have different binary types.
