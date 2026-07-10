using Booth.Shared.Contracts;
namespace Booth.Runtime.JobApp;

public sealed class PrintJobExecutor : IJobExecutor
{
    public JobType SupportedJobType => JobType.Print;

    public string OutputAssetType => "print_output";

    public Task<string> ExecuteAsync(JobDetailsApiResponse job, string outputPath, CancellationToken cancellationToken)
    {
        throw new JobExecutionException(
            ErrorCodes.PrintQueueUnavailable,
            "Runtime printer integration is not configured.");
    }
}
