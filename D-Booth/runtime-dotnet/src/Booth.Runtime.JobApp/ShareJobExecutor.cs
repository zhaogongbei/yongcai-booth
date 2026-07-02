using Booth.Shared.Contracts;
using System.Text.Json;

namespace Booth.Runtime.JobApp;

public sealed class ShareJobExecutor : IJobExecutor
{
    public JobType SupportedJobType => JobType.Share;

    public string OutputAssetType => "share_package";

    public async Task<string> ExecuteAsync(JobDetailsApiResponse job, string outputPath, CancellationToken cancellationToken)
    {
        var payload = job.PayloadJson is null
            ? new ShareJobPayload("unknown", "unknown", null)
            : JsonSerializer.Deserialize<ShareJobPayload>(job.PayloadJson) ?? new ShareJobPayload("unknown", "unknown", null);

        var output = new
        {
            job.JobId,
            job.AggregateId,
            payload.ChannelType,
            payload.Recipient,
            payload.ConsentToken,
            ExecutedAtUtc = DateTimeOffset.UtcNow.UtcDateTime.ToString("O"),
            OutputType = "share"
        };

        await File.WriteAllTextAsync(
            outputPath,
            JsonSerializer.Serialize(output, new JsonSerializerOptions { WriteIndented = true }),
            cancellationToken);

        return outputPath;
    }
}
