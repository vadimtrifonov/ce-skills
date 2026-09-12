using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins;
using Mutagen.Bethesda.Plugins.Cache;
using Mutagen.Bethesda.Plugins.Order;
using Mutagen.Bethesda.Skyrim;

if (args.Length != 1)
{
    return 2;
}

var directory = Path.GetFullPath(args[0]);
var release = SkyrimRelease.SkyrimVR;
var sourceKey = ModKey.FromFileName("WriteSmoke.esm");
var patchKey = ModKey.FromFileName("WriteSmokePatch.esp");
var sourcePath = Path.Combine(directory, sourceKey.FileName);
var patchPath = Path.Combine(directory, patchKey.FileName);

var source = new SkyrimMod(sourceKey, release);
var sourceNpc = source.Npcs.AddNew();
sourceNpc.EditorID = "WriteSmokeNpc";
sourceNpc.Name = "Write Smoke Source";

await source.BeginWrite
    .ToPath(sourcePath)
    .WithNoLoadOrder()
    .WriteAsync();

var formKey = sourceNpc.FormKey;
using (var imported = SkyrimMod.Create(release).FromPath(sourcePath).Construct())
{
    var importedNpc = imported.Npcs.Single(record => record.FormKey == formKey);
    var patch = new SkyrimMod(patchKey, release);
    var patchedNpc = patch.Npcs.GetOrAddAsOverride(importedNpc);
    patchedNpc.EditorID = "WriteSmokeNpcPatched";
    patchedNpc.Name = "Write Smoke Patched";

    await patch.BeginWrite
        .ToPath(patchPath)
        .WithLoadOrder(new ISkyrimModGetter[] { imported })
        .WriteAsync();
}

using (var written = SkyrimMod.Create(release).FromPath(patchPath).Construct())
{
    var writtenNpc = written.Npcs.Single(record => record.FormKey == formKey);
    if (writtenNpc.EditorID != "WriteSmokeNpcPatched"
        || writtenNpc.Name?.String != "Write Smoke Patched")
    {
        Console.Error.WriteLine(
            $"written NPC mismatch: EditorID={writtenNpc.EditorID ?? "<null>"}, "
            + $"Name={writtenNpc.Name?.String ?? "<null>"}");
        return 1;
    }

    var masters = written.ModHeader.MasterReferences.Select(master => master.Master).ToArray();
    if (!masters.SequenceEqual(new[] { sourceKey }))
    {
        Console.Error.WriteLine(
            $"master mismatch: expected [{sourceKey}], actual [{string.Join(", ", masters)}]");
        return 1;
    }
}

var providers = new[]
{
    new ModPath(sourceKey, sourcePath),
    new ModPath(patchKey, patchPath),
};
var listings = providers
    .Select(provider => SkyrimMod.Create(release).FromPath(provider).Construct())
    .Select(mod => new ModListing<ISkyrimModGetter>(mod))
    .ToArray();

using var loadOrder = new LoadOrder<ModListing<ISkyrimModGetter>>(listings);
var linkCache = loadOrder.ToImmutableLinkCache();
var winner = linkCache.Resolve<INpcGetter>(formKey);
if (winner.EditorID != "WriteSmokeNpcPatched"
    || winner.Name?.String != "Write Smoke Patched")
{
    Console.Error.WriteLine(
        $"winner mismatch: EditorID={winner.EditorID ?? "<null>"}, "
        + $"Name={winner.Name?.String ?? "<null>"}");
    return 1;
}

var previous = linkCache.GetPreviousOverrides<INpcGetter>(formKey, patchKey).ToArray();
var previousContexts = linkCache.GetPreviousOverrideSimpleContexts<INpcGetter>(
    formKey, patchKey, ResolveTarget.Origin).ToArray();
if (previous.Length != 1
    || previous[0].EditorID != "WriteSmokeNpc"
    || previousContexts.Length != 1
    || previousContexts[0].ModKey != sourceKey
    || linkCache.GetPreviousOverrides<INpcGetter>(formKey, sourceKey).Any())
{
    Console.Error.WriteLine("previous-override boundary mismatch");
    return 1;
}

Console.WriteLine("write smoke passed");
return 0;
