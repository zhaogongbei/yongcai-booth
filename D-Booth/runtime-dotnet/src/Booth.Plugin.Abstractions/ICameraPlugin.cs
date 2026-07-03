using Booth.Plugin.Abstractions.Camera;

namespace Booth.Plugin.Abstractions;

/// <summary>
/// Plugin interface for camera device integration.
/// Enables discovery, connection, and remote capture of photos.
/// </summary>
public interface ICameraPlugin : IBoothPlugin
{
    /// <summary>
    /// Discovers all available camera devices connected to the system.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>List of discovered camera descriptors.</returns>
    Task<IReadOnlyList<CameraDescriptor>> DiscoverAsync(CancellationToken cancellationToken);

    /// <summary>
    /// Connects to a specific camera device.
    /// </summary>
    /// <param name="deviceId">Unique identifier of the camera to connect to.</param>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>True if connection succeeded.</returns>
    Task<bool> ConnectAsync(string deviceId, CancellationToken cancellationToken);

    /// <summary>
    /// Disconnects from the currently connected camera.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>A task representing the disconnect operation.</returns>
    Task DisconnectAsync(CancellationToken cancellationToken);

    /// <summary>
    /// Captures a photo with the connected camera using the specified configuration.
    /// </summary>
    /// <param name="config">Configuration for the capture operation.</param>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>Result of the capture operation including file path or error.</returns>
    Task<CaptureResult> CaptureAsync(CaptureConfig config, CancellationToken cancellationToken);

    /// <summary>
    /// Gets the current connection status.
    /// </summary>
    bool IsConnected { get; }

    /// <summary>
    /// Gets the descriptor of the currently connected camera, if any.
    /// </summary>
    CameraDescriptor? ConnectedCamera { get; }
}
