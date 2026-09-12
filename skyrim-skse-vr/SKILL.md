---
name: skyrim-skse-vr
description: Implement and port SKSE plugins for Skyrim VR, including engine hooks and functions missing from the VR Address Library.
---

# SKSE Plugins for Skyrim VR

An SKSE plugin is a native DLL loaded into the game process.
It can use SKSE interfaces and call or modify Skyrim's engine code.

| Component | Role |
|---|---|
| [SKSEVR](https://skse.silverlock.org/) | The VR edition of Skyrim Script Extender. Its loader starts the game with SKSEVR; the runtime loads plugin DLLs and provides interfaces such as messaging and task scheduling. |
| [CommonLibSSE-NG](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/README.md) | A C++ library compiled into the plugin, providing reverse-engineered engine types, function wrappers, and runtime-specific address and layout helpers. |
| [VR Address Library](https://github.com/alandtse/skyrim_vr_address_library#release-csvs) | Runtime data mapping IDs to offsets inside `SkyrimVR.exe`, used by CommonLib to resolve engine addresses. |
| [VR Address Tools](https://github.com/alandtse/vr_address_tools#description) | Development-time tools for scanning relocation uses in source and generating address-library CSVs. |

## Runtime and initialization

Skyrim VR `1.4.15` uses SKSEVR and the VR Address Library's `Data/SKSE/Plugins/version-1-4-15-0.csv`.
The SE/AE Address Library packages do not supply that file.

The VR loader requires `SKSEPlugin_Query` and `SKSEPlugin_Load`; AE's `SKSEPlugin_Version` metadata alone is insufficient.
Keep `Query` to compatibility checks and plugin information.
Initialize CommonLib with `SKSE::Init` in `Load`, before installing hooks or using SKSE interfaces.
Optional initialization settings use [`SKSE::InitInfo`](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/include/SKSE/API.h); the boolean `Init` overload and `AllocTrampoline` are deprecated.
Request a trampoline through `InitInfo` with `trampoline = true` and `trampolineSize` set to the required byte count.
The `PreLoadInterface` overload is AE-only, not a replacement for VR's `Load` initialization.
See the [SKSEVR plugin API](https://github.com/SkyrimAlternativeDevelopers/sksevr-mirror/blob/76e8afaf2253851ca22a209e456620430df16fc2/skse64/PluginAPI.h#L303-L351) for the export contract.

A hook that intercepts record loading must be installed before records load; `DataLoaded` is too late.
Work that consumes populated form data can wait for `DataLoaded`.
When replacing an existing plugin, preserve any DLL filename and exported ABI used by consumers; the SKSE metadata name is a separate identity.

The CommonLib references in this skill use `v7.5.4`.
For build integration and runtime selection, see [CommonLib usage](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/README.md#usage) and [Runtime Targeting](https://github.com/CharmedBaryon/CommonLibSSE-NG/wiki/Runtime-Targeting).

## Addresses and relocations

An address-library ID is a lookup key, not a memory address.
The runtime's mapping supplies an RVA (relative virtual address): the offset added to the executable's loaded base to obtain the live address.

VR Address Library keys normally reuse SE `1.5.97` IDs.
An SE ID can therefore resolve to a different address in VR without needing a third ID.

| CommonLib expression | Meaning on VR |
|---|---|
| `REL::RelocationID(seID, aeID)` | Look up `seID` in the VR database |
| `REL::RelocationID(seID, aeID, vrID)` | Look up the explicitly supplied VR database key |
| `REL::VariantID(seID, aeID, vrRVA)` | Use a module-relative VR address, without a VR ID lookup |
| `REL::Offset(rva)` | Add the RVA to the loaded module base |
| `REL::VariantOffset(se, ae, vr)` | Select the VR offset value |

A `VariantOffset` passed as the sole argument to `REL::Relocation<T>` is relative to the module base.
Passed after an ID, it is relative to that ID's resolved address.
This expresses a containing function plus a separately verified interior offset.
The two-argument `REL::Relocate(seAndVR, ae)` also groups VR with SE; use three arguments when VR needs a distinct value.
See [ID constructors](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/include/REL/ID.h) for the ID/RVA distinction.

Missing-ID lookup is not an availability probe: [CommonLib's lookup](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/src/REL/IDDB.cpp#L156-L180) takes a fatal error path in production.
A subsequent null check or `try/catch` does not provide a fallback.
Check the mapping data before resolving an uncertain ID.
Likewise, [`Offset2ID`](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/src/REL/Offset2ID.cpp#L37-L56) requires an exact offset match; it does not find the function containing an arbitrary instruction.

## ABI and object layout

Relocations select addresses, not function signatures or object layouts.
Recover arguments and any `this` adjustment from callers and the callee before declaring an unpublished function's type.
For register arguments, stack arguments, shadow space, and alignment, use Microsoft's [x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention).

### Virtual calls and members

A vtable hook changes a particular table and slot, not every call to a function body.
Check the actual object's vtable and the caller's dispatch before choosing between a slot replacement and a function detour.
On x64, divide the vtable byte displacement by 8: `[vtable + 0x190]` uses slot 50 (`0x32`).

Cross-VR builds can replace real inheritance with `As...` accessors and virtual dispatch with `REL::RelocateVirtual` wrappers.
Use the class's runtime accessors instead of assuming a direct member or `static_cast` has the same layout on VR.
For conditional inheritance and pointer-versus-reference access, see [Runtime Cast Accessors](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/docs/RuntimeDataAccessors.md#runtime-cast-accessors) and [Pointer Member Accessors](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/docs/RuntimeDataAccessors.md#pointer-member-accessors).
AE-enabled builds use `BSGraphics::State::GetFrameCount()` and `GetUseEarlyZ()` instead of direct access to those fields.
In CommonLib 7.5.4, `GetInsideFrame()` accesses `compiledShaderThisFrame` at `0x54` on VR, not `insideFrame` at `0x50`.

For plugin-owned menu input handlers, [`RE::MenuEventHandlerEx`](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/include/RE/M/MenuEventHandlerEx.h) provides runtime-specific dispatch.
Pass its `Handler()` result, not the adapter's `this` pointer, to `MenuControls::RegisterHandler` and `RemoveHandler`.

## Query mappings and audit source

For an SE ID recovered from a CommonLib declaration or another implementation:

```powershell
$tools = 'C:\Path\To\vr_address_tools'
$db = Join-Path $tools 'skyrim_vr_address_library'
$seID = '50180'
Import-Csv "$db\database.csv" | Where-Object id -eq $seID
Import-Csv "$db\addrlib.csv" | Where-Object id -eq $seID
```

`database.csv` supplies the maintained mapping and its confidence status.
`addrlib.csv` and `sse_vr.csv` provide additional, partly automated candidate associations.
The source database is not necessarily the release CSV loaded by the active game profile.

Address units differ:

- `database.csv`, `addrlib.csv`, and `sse_vr.csv` use analysis VAs based at `0x140000000`.
- `offsets-1.5.97.0.csv` and the runtime release CSV use hexadecimal RVAs.

For example, analysis VA `0x140886DF0` means RVA `0x886DF0`.
The release CSV has a metadata row after its header; skip that row when treating it as an ID table.
See the [CSV format documentation](https://github.com/alandtse/skyrim_vr_address_library#csv-files) for field definitions and the status scale.
Only status `4` asserts byte identity; a weaker function match does not justify carrying an interior offset unchanged.
Even status `4` does not describe changes made by other loaded plugins.

To scan source, run from this skill directory:

```powershell
mise trust mise.toml
mise install
mise exec -- python -m pip install --upgrade --editable "$tools"
mise exec -- python -m vr_address_tools 'C:\Path\To\Plugin\src' analyze
```

`analyze` reports recognized relocation uses and candidate mappings.
Its exit code is the number of reported items, including mapped items; nonzero does not necessarily mean the scan failed.
Named C++ constants can hide IDs from the scanner: `RELOCATION_ID(50180, 51110)` is recognized, while passing equivalent named constants can produce no result.
Follow wrapper implementations and constant definitions when the scan misses a target.
The [analyze documentation](https://github.com/alandtse/vr_address_tools#analyze) explains its output and database-row export option.

## Inspect engine code

A Steam `SkyrimVR.exe` with a `.bind` stub may not expose the executed code at the expected disk RVAs.
Use an unpacked image for offline analysis or inspect the launched process.
[Runtime Byte Inspector](https://github.com/vadimtrifonov/runtime-byte-inspector/blob/master/SKILL.md) can be used to capture bounded live-memory ranges, disassemble from an explicit origin, and compare saved before/after captures.

Capture original code before installing the hook; another plugin may already have changed the site.
Across launches, RVAs remain useful under ASLR, but absolute pointers embedded in captured windows can change.
A patched instruction can also span an address that used to start a separate instruction; account for that when choosing the decoding origin.

## When the mapping is missing

For a discovered `SkyrimVR.exe` RVA, use `REL::Offset(vrRVA)` in a VR-only plugin or `VariantID` to combine the VR RVA with SE/AE IDs in a multi-runtime plugin.
To contribute a mapping, use the [VR database conventions](https://github.com/alandtse/skyrim_vr_address_library#address-ids), including their SE-address-derived keys for symbols without a formal SE ID.

### Follow live registrations

A runtime table can expose a function pointer even when the function has no published ID.
For a named console command:

```cpp
auto* command = RE::SCRIPT_FUNCTION::LocateConsoleCommand("Help");
auto handler = command ? command->executeFunction : nullptr;
```

This obtains the live execute handler, not an interior patch offset.
The command table itself is relocated by CommonLib; see [CommandTable.cpp](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/src/RE/C/CommandTable.cpp).
Disassemble the handler to locate the required operation.

For accepted console input, the active `RE::Console` menu's `fxDelegate->callbacks.GetAlt("ExecuteCommand")` exposes the registered Scaleform callback.
That callback receives the command string in `FxDelegateArgs[0]`.
The callback table belongs to the menu instance: obtain it while the console is open, and perform menu/callback work on the game thread.
Replace the entry's `callback` pointer with a wrapper that forwards the arguments to the saved original callback.
To verify the registration and payload, log argument zero's type and value in the forwarding wrapper, then enter `help skse_vr_probe 0`; expect a string containing that exact line.

### Follow import references

For a six-byte RIP-relative indirect call:

```text
FF 15 <disp32>                 call qword ptr [rip + disp32]
slotVA   = callVA + 6 + signed(disp32)
calleeVA = pointer stored at slotVA
```

The slot address is not the callee address.
Starting from a known imported call, locate other decoded calls that reference the same slot, then inspect their argument setup.
Matching `FF 15` alone identifies neither the import nor the intended behavior.

For [`__stdio_common_vsprintf`](https://github.com/huangqinjin/ucrt/blob/d6e817a4cc90f6f1fe54f8a0aa4af4fff0bb647d/include/stdio.h#L1338-L1445), the destination buffer is in `RDX` and its size argument is in `R8`.
The same import serves bounded and unbounded callers.
Trace the buffer allocation and size argument at each site before choosing a replacement bound.
A bounded formatting call can leave truncated output without a NUL terminator; check termination separately from the write limit.
The [`vsnprintf` and `_vsnprintf` wrappers](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/vsnprintf-vsnprintf-vsnprintf-l-vsnwprintf-vsnwprintf-l#remarks) select different options and have different termination guarantees.

### Match containing functions

Use SE/VR binary comparison when registrations or known callees do not identify the function.
The maintainer's [Ghidra/IDA guidance](https://github.com/alandtse/skyrim_vr_address_library/discussions/28) describes matching both executables and checking callers and callees.
A nearby mapped address narrows the search; it does not establish a constant translation delta for the surrounding code.
Compare control flow, arguments, and referenced data before selecting the VR-local instruction window.

If a signature is needed, search the relevant executable region and check the candidate's calls and surrounding instructions.
An ambiguous match is not a usable patch target.
`REL::make_pattern` matches at a supplied location; it is not a scanner.

## Instruction patches

Overwrite whole instructions.
For copied or reordered instructions, recompute relative branch and RIP-relative memory operands from the new instruction end.
Preserve external destinations; remap branches whose target instructions also moved.

```text
new displacement = target VA - new instruction end VA
```

Check that the displacement fits its signed 8- or 32-bit field, and that branches still land on the intended instructions.
Trampoline allocation and branch-writing helpers do not relocate arbitrary copied instructions for you.

Validate the original window before writing, including enough surrounding code to distinguish repeated call sequences.
On mismatch, leave the affected feature uninstalled and log the runtime, module RVA, and expected/observed bytes.
When several sites are jointly required for one feature, validate the entire required set before the first write; otherwise a subset can be applied even though the feature cannot be enabled.

Verification helpers read memory directly; establish that a derived window is readable in the expected module section before comparing bytes.
`REL::safe_write` without expected bytes changes page protection but does not verify the site.
The raw expected-byte overload rejects verification longer than the overwrite.
The pattern overload starts at the write address and can verify bytes beyond the overwrite.
Check a preceding prefix with `verify_code` at the prefix's address before writing.
See the [write implementation](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/src/REL/Relocation.cpp) and [verification overloads](https://github.com/alandtse/CommonLibSSE-NG/blob/v7.5.4/include/REL/Relocation.h) for the exact behavior in this version.

## Verify execution and behavior

Keep byte-write confirmation, hook execution, and behavior results distinct.
A patch can install successfully in code the tested gameplay path never calls.
Use a breakpoint or targeted hit trace when an unchanged result leaves reachability uncertain.

For behavior comparisons, account for other plugins that can supply the same result and inspect the consumer's actual API route.
For example, `TESForm::LookupByEditorID` and `form->GetFormEditorID()` test opposite lookup directions; a helper library can instead obtain EditorIDs through another plugin's export.
A successful helper lookup alone does not establish that either native path was restored.
