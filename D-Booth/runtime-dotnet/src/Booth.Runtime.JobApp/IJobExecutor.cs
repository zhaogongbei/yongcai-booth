using Booth.Shared.Contracts;

namespace Booth.Runtime.JobApp;

public interface IJobExecutor
{
    JobType SupportedJobType { get; }
    string OutputAssetType { get; }
    Task<string> ExecuteAsync(JobDetailsApiResponse job, string outputPath, CancellationToken cancellationToken);
}
