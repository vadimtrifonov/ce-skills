using Mutagen.Bethesda;
using Mutagen.Bethesda.Plugins;
using Mutagen.Bethesda.Plugins.Records;
using Mutagen.Bethesda.Starfield;

if (args.Length != 1)
{
    return 2;
}

var directory = Path.GetFullPath(args[0]);
var release = StarfieldRelease.Starfield;
var masters = new[]
{
    new StarfieldMod(ModKey.FromFileName("Full.esm"), release),
    new StarfieldMod(ModKey.FromFileName("Medium.esm"), release) { IsMediumMaster = true },
    new StarfieldMod(ModKey.FromFileName("Small.esm"), release) { IsSmallMaster = true },
};
foreach (var master in masters)
{
    var keyword = master.Keywords.AddNew();
    keyword.EditorID = "Source" + master.ModKey.Name;
    await master.BeginWrite
        .ToPath(Path.Combine(directory, master.ModKey.FileName))
        .WithNoLoadOrder()
        .WriteAsync();
}

var patch = new StarfieldMod(ModKey.FromFileName("WriteSmokePatch.esm"), release)
{
    IsSmallMaster = true,
};
var sourceKeyword = masters[0].Keywords.Single();
var patchedKeyword = patch.Keywords.GetOrAddAsOverride(sourceKeyword);
patchedKeyword.EditorID = "PatchedFull";
var localKeyword = patch.Keywords.AddNew();
localKeyword.EditorID = "LocalKeyword";
var expectedLinks = masters.Select(mod => mod.Keywords.Single().FormKey)
    .Append(localKeyword.FormKey).ToArray();
var list = patch.FormLists.AddNew();
foreach (var key in expectedLinks)
{
    list.Items.Add(new FormLink<IStarfieldMajorRecordGetter>(key));
}

var patchPath = Path.Combine(directory, patch.ModKey.FileName);
await patch.BeginWrite
    .ToPath(patchPath)
    .WithLoadOrder(masters)
    .WriteAsync();

void Check(IStarfieldModGetter imported)
{
    var links = imported.FormLists.Single().Items.Select(item => item.FormKey).ToArray();
    if (!links.SequenceEqual(expectedLinks))
    {
        throw new InvalidOperationException($"FormKey mismatch: {string.Join(", ", links)}");
    }
    if (imported.Keywords.Single(item => item.FormKey == sourceKeyword.FormKey).EditorID != "PatchedFull"
        || imported.Keywords.Single(item => item.FormKey == localKeyword.FormKey).EditorID != "LocalKeyword")
    {
        throw new InvalidOperationException("Written keyword identity or content mismatch");
    }
    if (!imported.IsSmallMaster
        || !imported.ModHeader.MasterReferences.Select(item => item.Master)
            .SequenceEqual(masters.Select(mod => mod.ModKey)))
    {
        throw new InvalidOperationException("Written master flags or order mismatch");
    }
}

using (var imported = StarfieldMod.Create(release)
    .FromPath(patchPath)
    .WithLoadOrderFromHeaderMasters()
    .WithDataFolder(directory)
    .Construct())
{
    Check(imported);
}

var orderedProviders = masters.Select(mod =>
    new ModPath(mod.ModKey, Path.Combine(directory, mod.ModKey.FileName))).ToArray();
var masterStyles = orderedProviders
    .Select(path => KeyedMasterStyle.FromPath(path, GameRelease.Starfield))
    .ToArray();
if (!masterStyles.Select(master => master.MasterStyle)
    .SequenceEqual(new[] { MasterStyle.Full, MasterStyle.Medium, MasterStyle.Small }))
{
    throw new InvalidOperationException("Fixture master styles were not preserved");
}
using (var imported = StarfieldMod.Create(release)
    .FromPath(patchPath)
    .WithKnownMasters(masterStyles)
    .Construct())
{
    Check(imported);
}

Console.WriteLine("write smoke passed");
return 0;
