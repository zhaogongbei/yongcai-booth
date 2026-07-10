using Booth.Shared.Contracts;
namespace Booth.Runtime.JobApp;

public sealed class ShareJobExecutor : IJobExecutor
{
    public JobType SupportedJobType => JobType.Share;

    public string OutputAssetType => "share_package";

    public Task<string> ExecuteAsync(JobDetailsApiResponse job, string outputPath, CancellationToken cancellationToken)
    {
        throw new JobExecutionException(
            ErrorCodes.ShareChannelRejected,
            "Runtime share integration is not configured.");
    }
}
