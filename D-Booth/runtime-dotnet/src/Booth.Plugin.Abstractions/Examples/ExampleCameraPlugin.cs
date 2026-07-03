using Booth.Plugin.Abstractions.Camera;
using Booth.Plugin.Abstractions.Lifecycle;

namespace Booth.Plugin.Abstractions.Examples;

/// <summary>
/// Example camera plugin demonstrating the plugin interface implementation.
/// This is a stub implementation for reference purposes.
/// </summary>
public sealed class ExampleCameraPlugin : ICameraPlugin
{
    private CameraDescriptor? _connectedCamera;

    /// <inheritdoc />
    public string Id => "booth.plugin.camera.example";

    /// <inheritdoc />
    public string Name => "Example Camera Plugin";

    /// <inheritdoc />
    public string Version => "1.0.0";

    /// <inheritdoc />
    public bool IsConnected => _connectedCamera is not null;

    /// <inheritdoc />
    public CameraDescriptor? ConnectedCamera => _connectedCamera;

    /// <inheritdoc />
    public Task InitializeAsync(IPluginContext context, CancellationToken cancellationToken)
    {
        // Perform initialization: load drivers, check dependencies, etc.
        Console.WriteLine($"[{Name}] Initializing with runtime version {context.RuntimeVersion}");
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task ShutdownAsync(CancellationToken cancellationToken)
    {
        // Clean up resources
        Console.WriteLine($"[{Name}] Shutting down");
        _connectedCamera = null;
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task<IReadOnlyList<CameraDescriptor>> DiscoverAsync(CancellationToken cancellationToken)
    {
        // In a real implementation, query USB/PTP devices
        var cameras = new List<CameraDescriptor>
        {
            new("cam_example_001", "Example Corp", "Model X100", new[] { "live-view", "remote-trigger" })
        };

        return Task.FromResult<IReadOnlyList<CameraDescriptor>>(cameras);
    }

    /// <inheritdoc />
    public async Task<bool> ConnectAsync(string deviceId, CancellationToken cancellationToken)
    {
        var cameras = await DiscoverAsync(cancellationToken);
        _connectedCamera = cameras.FirstOrDefault(c => c.DeviceId == deviceId);
        return _connectedCamera is not null;
    }

    /// <inheritdoc />
    public Task DisconnectAsync(CancellationToken cancellationToken)
    {
        _connectedCamera = null;
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task<CaptureResult> CaptureAsync(CaptureConfig config, CancellationToken cancellationToken)
    {
        if (!IsConnected)
            return Task.FromResult(CaptureResult.Failed("No camera connected"));

        // In a real implementation:
        // 1. Send capture command to camera
        // 2. Download image to config.OutputPath
        // 3. Extract EXIF metadata
        // 4. Return success or failure

        var metadata = new Dictionary<string, object>
        {
            ["iso"] = config.Iso ?? 400,
            ["shutterSpeed"] = config.ShutterSpeed ?? 0.004,
            ["aperture"] = config.Aperture ?? 5.6
        };

        return Task.FromResult(CaptureResult.Successful(config.OutputPath, metadata));
    }
}
