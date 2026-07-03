namespace Booth.Plugin.Abstractions.Printer;

/// <summary>
/// Describes a discovered printer device.
/// </summary>
/// <param name="DeviceId">Unique identifier for the printer device.</param>
/// <param name="Vendor">Printer manufacturer (e.g., "DNP", "Mitsubishi", "Canon").</param>
/// <param name="Model">Printer model name (e.g., "DS620", "CP-D90DW").</param>
/// <param name="ConnectionType">Connection type (e.g., "USB", "Network", "Bluetooth").</param>
/// <param name="SupportedSizes">List of supported print sizes (e.g., "4x6", "5x7", "6x8").</param>
public sealed record PrinterDescriptor(
    string DeviceId,
    string Vendor,
    string Model,
    string ConnectionType,
    IReadOnlyList<string> SupportedSizes)
{
    /// <summary>
    /// Checks if the printer supports a specific paper size.
    /// </summary>
    /// <param name="size">Paper size to check (e.g., "4x6").</param>
    /// <returns>True if the size is supported.</returns>
    public bool SupportsSize(string size) =>
        SupportedSizes.Contains(size, StringComparer.OrdinalIgnoreCase);
}

/// <summary>
/// Configuration for a print job.
/// </summary>
public sealed record PrintConfig
{
    /// <summary>
    /// Gets the path to the image file to print.
    /// </summary>
    public required string ImagePath { get; init; }

    /// <summary>
    /// Gets the paper size to use (e.g., "4x6", "5x7").
    /// </summary>
    public required string PaperSize { get; init; }

    /// <summary>
    /// Gets the number of copies to print.
    /// </summary>
    public int Copies { get; init; } = 1;

    /// <summary>
    /// Gets the print quality setting (e.g., "standard", "high", "glossy").
    /// </summary>
    public string Quality { get; init; } = "standard";

    /// <summary>
    /// Gets the color correction mode (e.g., "auto", "none", "vivid").
    /// </summary>
    public string ColorCorrection { get; init; } = "auto";

    /// <summary>
    /// Gets additional printer-specific options.
    /// </summary>
    public IReadOnlyDictionary<string, object> Options { get; init; } = new Dictionary<string, object>();
}

/// <summary>
/// Represents the status of a print job.
/// </summary>
public enum PrintJobStatus
{
    /// <summary>
    /// Print job is queued and waiting to start.
    /// </summary>
    Queued,

    /// <summary>
    /// Print job is currently printing.
    /// </summary>
    Printing,

    /// <summary>
    /// Print job completed successfully.
    /// </summary>
    Completed,

    /// <summary>
    /// Print job failed.
    /// </summary>
    Failed,

    /// <summary>
    /// Print job was cancelled.
    /// </summary>
    Cancelled
}

/// <summary>
/// Represents the result of a print operation.
/// </summary>
/// <param name="JobId">Unique identifier for the print job.</param>
/// <param name="Status">Current status of the print job.</param>
/// <param name="ErrorMessage">Error message if the job failed.</param>
public sealed record PrintResult(
    string JobId,
    PrintJobStatus Status,
    string? ErrorMessage)
{
    /// <summary>
    /// Creates a successful print result.
    /// </summary>
    public static PrintResult Successful(string jobId) =>
        new(jobId, PrintJobStatus.Completed, null);

    /// <summary>
    /// Creates a failed print result.
    /// </summary>
    public static PrintResult Failed(string jobId, string errorMessage) =>
        new(jobId, PrintJobStatus.Failed, errorMessage);
}

/// <summary>
/// Represents the current status of a printer device.
/// </summary>
public sealed record PrinterStatus
{
    /// <summary>
    /// Gets a value indicating whether the printer is online and ready.
    /// </summary>
    public required bool IsReady { get; init; }

    /// <summary>
    /// Gets the current paper level percentage (0-100), if available.
    /// </summary>
    public int? PaperLevel { get; init; }

    /// <summary>
    /// Gets the current ink/ribbon level percentage (0-100), if available.
    /// </summary>
    public int? InkLevel { get; init; }

    /// <summary>
    /// Gets any active error messages.
    /// </summary>
    public string? ErrorMessage { get; init; }

    /// <summary>
    /// Gets additional status information.
    /// </summary>
    public IReadOnlyDictionary<string, object> Details { get; init; } = new Dictionary<string, object>();
}
