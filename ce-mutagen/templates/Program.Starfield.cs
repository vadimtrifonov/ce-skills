using Mutagen.Bethesda.Starfield;

if (args.Length != 2)
{
    Console.Error.WriteLine("Usage: Scratch <plugin-path> <data-directory>");
    return 2;
}

var pluginPath = Path.GetFullPath(args[0]);
if (!File.Exists(pluginPath))
{
    Console.Error.WriteLine($"Plugin does not exist: {pluginPath}");
    return 2;
}

var dataFolder = Path.GetFullPath(args[1]);
if (!Directory.Exists(dataFolder))
{
    Console.Error.WriteLine($"Data directory does not exist: {dataFolder}");
    return 2;
}

using var mod = StarfieldMod.Create(StarfieldRelease.Starfield)
    .FromPath(pluginPath)
    .WithLoadOrderFromHeaderMasters()
    .WithDataFolder(dataFolder)
    .Construct();

Console.WriteLine($"{mod.ModKey}\t{mod.StarfieldRelease}");
return 0;
