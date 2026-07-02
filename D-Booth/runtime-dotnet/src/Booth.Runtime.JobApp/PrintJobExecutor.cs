using Booth.Shared.Contracts;
using System.Text.Json;

namespace Booth.Runtime.JobApp;

public sealed class PrintJobExecutor : IJobExecutor
{
    public JobType SupportedJobType => JobType.Print;

    public string OutputAssetType => "print_output";

    public async Task<string> ExecuteAsync(JobDetailsApiResponse job, string outputPath, CancellationToken cancellationToken)
    {
        var payload = job.PayloadJson is null
            ? new PrintJobPayload(1, null)
            : JsonSerializer.Deserialize<PrintJobPayload>(job.PayloadJson) ?? new PrintJobPayload(1, null);

        var output = new
        {
            job.JobId,
            job.AggregateId,
            Copies = payload.Copies,
            payload.PrinterProfileId,
            ExecutedAtUtc = DateTimeOffset.UtcNow.UtcDateTime.ToString("O"),
            OutputType = "print"
        };

        await File.WriteAllTextAsync(
            outputPath,
            JsonSerializer.Serialize(output, new JsonSerializerOptions { WriteIndented = true }),
            cancellationToken);

        return outputPath;
    }
}
