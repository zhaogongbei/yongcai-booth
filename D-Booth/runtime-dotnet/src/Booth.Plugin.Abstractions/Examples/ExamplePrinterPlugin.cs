using Booth.Plugin.Abstractions.Lifecycle;
using Booth.Plugin.Abstractions.Printer;

namespace Booth.Plugin.Abstractions.Examples;

/// <summary>
/// Example printer plugin demonstrating the plugin interface implementation.
/// This is a stub implementation for reference purposes.
/// </summary>
public sealed class ExamplePrinterPlugin : IPrinterPlugin
{
    private PrinterDescriptor? _connectedPrinter;
    private readonly Dictionary<string, PrintJobStatus> _jobs = [];

    /// <inheritdoc />
    public string Id => "booth.plugin.printer.example";

    /// <inheritdoc />
    public string Name => "Example Printer Plugin";

    /// <inheritdoc />
    public string Version => "1.0.0";

    /// <inheritdoc />
    public bool IsConnected => _connectedPrinter is not null;

    /// <inheritdoc />
    public PrinterDescriptor? ConnectedPrinter => _connectedPrinter;

    /// <inheritdoc />
    public Task InitializeAsync(IPluginContext context, CancellationToken cancellationToken)
    {
        Console.WriteLine($"[{Name}] Initializing with runtime version {context.RuntimeVersion}");
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task ShutdownAsync(CancellationToken cancellationToken)
    {
        Console.WriteLine($"[{Name}] Shutting down");
        _connectedPrinter = null;
        _jobs.Clear();
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task<IReadOnlyList<PrinterDescriptor>> DiscoverAsync(CancellationToken cancellationToken)
    {
        // In a real implementation, query available printers via USB/network
        var printers = new List<PrinterDescriptor>
        {
            new("printer_example_001", "Example Corp", "PhotoPrint 4000", "USB", new[] { "4x6", "5x7" })
        };

        return Task.FromResult<IReadOnlyList<PrinterDescriptor>>(printers);
    }

    /// <inheritdoc />
    public async Task<bool> ConnectAsync(string deviceId, CancellationToken cancellationToken)
    {
        var printers = await DiscoverAsync(cancellationToken);
        _connectedPrinter = printers.FirstOrDefault(p => p.DeviceId == deviceId);
        return _connectedPrinter is not null;
    }

    /// <inheritdoc />
    public Task DisconnectAsync(CancellationToken cancellationToken)
    {
        _connectedPrinter = null;
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task<PrintResult> PrintAsync(PrintConfig config, CancellationToken cancellationToken)
    {
        if (!IsConnected)
            return Task.FromResult(PrintResult.Failed("no-job", "No printer connected"));

        if (!_connectedPrinter!.SupportsSize(config.PaperSize))
            return Task.FromResult(PrintResult.Failed("no-job", $"Paper size {config.PaperSize} not supported"));

        // In a real implementation:
        // 1. Validate image file exists
        // 2. Send print job to printer
        // 3. Monitor job status
        // 4. Return job ID and status

        var jobId = Guid.NewGuid().ToString("N");
        _jobs[jobId] = PrintJobStatus.Completed;

        return Task.FromResult(PrintResult.Successful(jobId));
    }

    /// <inheritdoc />
    public Task<PrinterStatus> GetStatusAsync(CancellationToken cancellationToken)
    {
        if (!IsConnected)
        {
            return Task.FromResult(new PrinterStatus
            {
                IsReady = false,
                ErrorMessage = "Printer not connected"
            });
        }

        // In a real implementation, query printer status via SDK
        return Task.FromResult(new PrinterStatus
        {
            IsReady = true,
            PaperLevel = 80,
            InkLevel = 60
        });
    }

    /// <inheritdoc />
    public Task<bool> CancelJobAsync(string jobId, CancellationToken cancellationToken)
    {
        if (_jobs.TryGetValue(jobId, out var status) && status == PrintJobStatus.Printing)
        {
            _jobs[jobId] = PrintJobStatus.Cancelled;
            return Task.FromResult(true);
        }

        return Task.FromResult(false);
    }
}
