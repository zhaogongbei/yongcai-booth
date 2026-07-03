using Booth.Plugin.Abstractions.Printer;

namespace Booth.Plugin.Abstractions;

/// <summary>
/// Plugin interface for printer device integration.
/// Enables discovery, connection, and photo printing operations.
/// </summary>
public interface IPrinterPlugin : IBoothPlugin
{
    /// <summary>
    /// Discovers all available printer devices.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>List of discovered printer descriptors.</returns>
    Task<IReadOnlyList<PrinterDescriptor>> DiscoverAsync(CancellationToken cancellationToken);

    /// <summary>
    /// Connects to a specific printer device.
    /// </summary>
    /// <param name="deviceId">Unique identifier of the printer to connect to.</param>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>True if connection succeeded.</returns>
    Task<bool> ConnectAsync(string deviceId, CancellationToken cancellationToken);

    /// <summary>
    /// Disconnects from the currently connected printer.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>A task representing the disconnect operation.</returns>
    Task DisconnectAsync(CancellationToken cancellationToken);

    /// <summary>
    /// Submits a print job to the connected printer.
    /// </summary>
    /// <param name="config">Configuration for the print job.</param>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>Result of the print operation including job ID or error.</returns>
    Task<PrintResult> PrintAsync(PrintConfig config, CancellationToken cancellationToken);

    /// <summary>
    /// Gets the current status of the connected printer.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>Current printer status including readiness and supply levels.</returns>
    Task<PrinterStatus> GetStatusAsync(CancellationToken cancellationToken);

    /// <summary>
    /// Cancels a pending or in-progress print job.
    /// </summary>
    /// <param name="jobId">Unique identifier of the job to cancel.</param>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>True if the job was successfully cancelled.</returns>
    Task<bool> CancelJobAsync(string jobId, CancellationToken cancellationToken);

    /// <summary>
    /// Gets the current connection status.
    /// </summary>
    bool IsConnected { get; }

    /// <summary>
    /// Gets the descriptor of the currently connected printer, if any.
    /// </summary>
    PrinterDescriptor? ConnectedPrinter { get; }
}
