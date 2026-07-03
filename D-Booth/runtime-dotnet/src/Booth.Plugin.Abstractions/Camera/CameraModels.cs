namespace Booth.Plugin.Abstractions.Camera;

/// <summary>
/// Describes a discovered camera device.
/// </summary>
/// <param name="DeviceId">Unique identifier for the camera device.</param>
/// <param name="Vendor">Camera manufacturer (e.g., "Canon", "Sony").</param>
/// <param name="Model">Camera model name (e.g., "EOS R5", "A7 III").</param>
/// <param name="Capabilities">List of supported capabilities (e.g., "live-view", "manual-focus", "remote-trigger").</param>
public sealed record CameraDescriptor(
    string DeviceId,
    string Vendor,
    string Model,
    IReadOnlyList<string> Capabilities)
{
    /// <summary>
    /// Checks if the camera supports a specific capability.
    /// </summary>
    /// <param name="capability">Capability name to check.</param>
    /// <returns>True if the capability is supported.</returns>
    public bool HasCapability(string capability) =>
        Capabilities.Contains(capability, StringComparer.OrdinalIgnoreCase);
}

/// <summary>
/// Represents the result of a photo capture operation.
/// </summary>
/// <param name="Success">Whether the capture succeeded.</param>
/// <param name="FilePath">Path to the captured image file, if successful.</param>
/// <param name="ErrorMessage">Error message if capture failed.</param>
/// <param name="Metadata">Camera metadata from the capture.</param>
public sealed record CaptureResult(
    bool Success,
    string? FilePath,
    string? ErrorMessage,
    IReadOnlyDictionary<string, object>? Metadata)
{
    /// <summary>
    /// Creates a successful capture result.
    /// </summary>
    public static CaptureResult Successful(string filePath, IReadOnlyDictionary<string, object>? metadata = null) =>
        new(true, filePath, null, metadata);

    /// <summary>
    /// Creates a failed capture result.
    /// </summary>
    public static CaptureResult Failed(string errorMessage) =>
        new(false, null, errorMessage, null);
}

/// <summary>
/// Configuration for a photo capture operation.
/// </summary>
public sealed record CaptureConfig
{
    /// <summary>
    /// Gets the output file path for the captured image.
    /// </summary>
    public required string OutputPath { get; init; }

    /// <summary>
    /// Gets the target image format (e.g., "jpeg", "raw").
    /// </summary>
    public string Format { get; init; } = "jpeg";

    /// <summary>
    /// Gets the JPEG quality (1-100), if applicable.
    /// </summary>
    public int Quality { get; init; } = 95;

    /// <summary>
    /// Gets the exposure compensation in stops (e.g., -2.0 to +2.0).
    /// </summary>
    public double? ExposureCompensation { get; init; }

    /// <summary>
    /// Gets the ISO sensitivity value, if manual control is desired.
    /// </summary>
    public int? Iso { get; init; }

    /// <summary>
    /// Gets the shutter speed in seconds, if manual control is desired.
    /// </summary>
    public double? ShutterSpeed { get; init; }

    /// <summary>
    /// Gets the aperture f-number, if manual control is desired.
    /// </summary>
    public double? Aperture { get; init; }

    /// <summary>
    /// Gets a value indicating whether to enable flash.
    /// </summary>
    public bool EnableFlash { get; init; }

    /// <summary>
    /// Gets additional plugin-specific options.
    /// </summary>
    public IReadOnlyDictionary<string, object> Options { get; init; } = new Dictionary<string, object>();
}
