namespace Booth.Plugin.Abstractions;

public interface IBoothPlugin
{
    string Id { get; }
    string Name { get; }
    string Version { get; }
    Task InitializeAsync(IPluginContext context, CancellationToken cancellationToken);
    Task ShutdownAsync(CancellationToken cancellationToken);
}

public interface IPluginContext
{
    string RuntimeVersion { get; }
    IReadOnlyDictionary<string, string> Capabilities { get; }
}

public interface ICameraPlugin : IBoothPlugin
{
    Task<IReadOnlyList<CameraDescriptor>> DiscoverAsync(CancellationToken cancellationToken);
}

public sealed record CameraDescriptor(
    string DeviceId,
    string Vendor,
    string Model,
    IReadOnlyList<string> Capabilities);
