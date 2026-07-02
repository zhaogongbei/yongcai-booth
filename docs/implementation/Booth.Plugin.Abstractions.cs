using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

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
    Task<ICameraSession> ConnectAsync(string deviceId, CancellationToken cancellationToken);
}

public interface ICameraSession
{
    Task StartPreviewAsync(CancellationToken cancellationToken);
    Task<CaptureResult> CaptureAsync(CancellationToken cancellationToken);
    Task DisconnectAsync(CancellationToken cancellationToken);
}

public interface ISharePlugin : IBoothPlugin
{
    Task<ShareExecutionResult> SendAsync(ShareExecutionRequest request, CancellationToken cancellationToken);
}

public interface IAiEffectPlugin : IBoothPlugin
{
    Task<bool> WarmupAsync(CancellationToken cancellationToken);
    Task<MediaFrame> ProcessAsync(MediaFrame frame, CancellationToken cancellationToken);
}

public sealed record CameraDescriptor(string DeviceId, string Vendor, string Model, IReadOnlyList<string> Capabilities);
public sealed record CaptureResult(string AssetId, string LocalPath, bool Success, string? ErrorCode);
public sealed record ShareExecutionRequest(string SessionId, string ChannelType, string Recipient);
public sealed record ShareExecutionResult(bool Success, string? ProviderMessageId, string? ErrorCode);
public sealed record MediaFrame(string FrameId, int Width, int Height, byte[] Buffer);
