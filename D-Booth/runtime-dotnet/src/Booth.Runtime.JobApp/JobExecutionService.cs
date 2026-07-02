using Booth.Infra.Storage.Sqlite;
using Booth.Shared.Contracts;
using System.Text.Json;

namespace Booth.Runtime.JobApp;

public sealed class JobExecutionService
{
    private readonly SqliteJobRepository _jobRepository;
    private readonly SqliteOutputAssetRepository _outputAssetRepository;
    private readonly string _outputsRoot;
    private readonly IReadOnlyDictionary<JobType, IJobExecutor> _executors;

    public JobExecutionService(
        SqliteJobRepository jobRepository,
        SqliteOutputAssetRepository outputAssetRepository,
        IEnumerable<IJobExecutor> executors,
        string outputsRoot)
    {
        _jobRepository = jobRepository;
        _outputAssetRepository = outputAssetRepository;
        _executors = executors.ToDictionary(x => x.SupportedJobType);
        _outputsRoot = outputsRoot;
    }

    public async Task<JobExecutionApiResponse?> ExecuteAsync(string jobId, CancellationToken cancellationToken)
    {
        var job = await _jobRepository.GetAsync(jobId, cancellationToken);
        if (job is null)
        {
            return null;
        }

        if (!Enum.TryParse<JobType>(job.JobType, out var jobType) || !_executors.TryGetValue(jobType, out var executor))
        {
            await _jobRepository.UpdateStatusAsync(jobId, JobStatus.Failed, cancellationToken, lastErrorCode: ErrorCodes.ConfigurationInvalid, lastErrorMessage: "Unsupported job type.");
            return new JobExecutionApiResponse(jobId, JobStatus.Failed.ToString().ToLowerInvariant(), null);
        }

        await _jobRepository.UpdateStatusAsync(jobId, JobStatus.Running, cancellationToken);

        var sessionOutputDirectory = Path.Combine(_outputsRoot, job.AggregateId);
        Directory.CreateDirectory(sessionOutputDirectory);
        var outputPath = Path.Combine(sessionOutputDirectory, $"{jobId}.{executor.OutputAssetType}.json");

        await executor.ExecuteAsync(job, outputPath, cancellationToken);

        var assetId = await _outputAssetRepository.CreateAsync(
            sessionId: job.AggregateId,
            assetType: executor.OutputAssetType,
            storageScope: "local",
            localPath: outputPath,
            remoteUrl: null,
            cancellationToken: cancellationToken);

        await _jobRepository.UpdateStatusAsync(jobId, JobStatus.Succeeded, cancellationToken, createdAssetId: assetId);

        return new JobExecutionApiResponse(
            jobId,
            JobStatus.Succeeded.ToString().ToLowerInvariant(),
            assetId);
    }
}
