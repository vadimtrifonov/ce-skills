using Mutagen.Bethesda.Skyrim;

if (args.Length != 2)
{
    Console.Error.WriteLine("Usage: Scratch <SkyrimSE|SkyrimVR> <plugin-path>");
    return 2;
}

if (!Enum.TryParse<SkyrimRelease>(args[0], ignoreCase: true, out var release) ||
    release is not (SkyrimRelease.SkyrimSE or SkyrimRelease.SkyrimVR))
{
    Console.Error.WriteLine($"Unsupported Skyrim release: {args[0]}");
    return 2;
}

var pluginPath = Path.GetFullPath(args[1]);
if (!File.Exists(pluginPath))
{
    Console.Error.WriteLine($"Plugin does not exist: {pluginPath}");
    return 2;
}

using var mod = SkyrimMod.Create(release)
    .FromPath(pluginPath)
    .Construct();

Console.WriteLine($"{mod.ModKey}\t{release}");
return 0;
