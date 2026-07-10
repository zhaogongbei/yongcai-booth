using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.JobApp;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class JobExecutionServiceTests
{
    [Fact]
    public async Task ExecuteAsync_ShouldMarkJobSucceeded_WhenExecutorCreatesOutputAsset()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-job-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var jobRepository = new SqliteJobRepository(databasePath);
        var assetRepository = new SqliteOutputAssetRepository(databasePath);
        var outputRoot = Path.Combine(tempRoot, "outputs");
        var service = new JobExecutionService(
            jobRepository,
            assetRepository,
            new IJobExecutor[] { new SuccessfulPrintExecutor() },
            outputRoot);

        var jobId = await jobRepository.QueueJobAsync(
            JobType.Print,
            "ses_test_002",
            100,
            CancellationToken.None,
            payload: new { Copies = 2, PrinterProfileId = "printer_default" });

        var result = await service.ExecuteAsync(jobId, CancellationToken.None);
        var job = await jobRepository.GetAsync(jobId, CancellationToken.None);
        var assets = await assetRepository.ListBySessionAsync("ses_test_002", CancellationToken.None);

        Assert.NotNull(result);
        Assert.Equal("succeeded", result!.Status);
        Assert.Equal("Succeeded", job!.Status);
        Assert.Single(assets);
        Assert.Equal(result.CreatedAssetId, assets[0].AssetId);
        Assert.NotNull(job.PayloadJson);
        Assert.Equal(result.CreatedAssetId, job.CreatedAssetId);
        Assert.NotNull(assets[0].LocalPath);
        Assert.True(File.Exists(assets[0].LocalPath));

        var fileContent = await File.ReadAllTextAsync(assets[0].LocalPath!);
        Assert.Contains(jobId, fileContent);
        Assert.Contains("Copies", fileContent);
    }

    [Theory]
    [InlineData(JobType.Print, ErrorCodes.PrintQueueUnavailable)]
    [InlineData(JobType.Share, ErrorCodes.ShareChannelRejected)]
    public async Task ExecuteAsync_ShouldFailClosed_WhenRuntimeIntegrationIsNotConfigured(
        JobType jobType,
        string expectedErrorCode)
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-job-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var jobRepository = new SqliteJobRepository(databasePath);
        var assetRepository = new SqliteOutputAssetRepository(databasePath);
        var service = new JobExecutionService(
            jobRepository,
            assetRepository,
            new IJobExecutor[] { new PrintJobExecutor(), new ShareJobExecutor() },
            Path.Combine(tempRoot, "outputs"));

        var payload = jobType == JobType.Print
            ? (object)new PrintJobPayload(1, "printer_default")
            : new ShareJobPayload("email", "guest@example.com", "consent_test");
        var jobId = await jobRepository.QueueJobAsync(
            jobType,
            "ses_test_failed",
            100,
            CancellationToken.None,
            payload);

        var result = await service.ExecuteAsync(jobId, CancellationToken.None);
        var job = await jobRepository.GetAsync(jobId, CancellationToken.None);
        var assets = await assetRepository.ListBySessionAsync("ses_test_failed", CancellationToken.None);

        Assert.NotNull(result);
        Assert.Equal("failed", result!.Status);
        Assert.Null(result.CreatedAssetId);
        Assert.Equal("Failed", job!.Status);
        Assert.Equal(expectedErrorCode, job.LastErrorCode);
        Assert.Null(job.CreatedAssetId);
        Assert.Empty(assets);
    }

    [Fact]
    public async Task ExecuteAsync_ShouldPersistGenericFailure_WhenExecutorThrowsUnexpectedException()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-job-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var jobRepository = new SqliteJobRepository(databasePath);
        var assetRepository = new SqliteOutputAssetRepository(databasePath);
        var service = new JobExecutionService(
            jobRepository,
            assetRepository,
            new IJobExecutor[] { new ThrowingPrintExecutor() },
            Path.Combine(tempRoot, "outputs"));
        var jobId = await jobRepository.QueueJobAsync(
            JobType.Print,
            "ses_test_exception",
            100,
            CancellationToken.None,
            payload: new PrintJobPayload(1, null));

        var result = await service.ExecuteAsync(jobId, CancellationToken.None);
        var job = await jobRepository.GetAsync(jobId, CancellationToken.None);

        Assert.NotNull(result);
        Assert.Equal("failed", result!.Status);
        Assert.Equal("Failed", job!.Status);
        Assert.Equal(ErrorCodes.ConfigurationInvalid, job.LastErrorCode);
        Assert.Equal("Job execution failed.", job.LastErrorMessage);
        Assert.Null(job.CreatedAssetId);
    }

    private sealed class SuccessfulPrintExecutor : IJobExecutor
    {
        public JobType SupportedJobType => JobType.Print;

        public string OutputAssetType => "print_output";

        public async Task<string> ExecuteAsync(
            JobDetailsApiResponse job,
            string outputPath,
            CancellationToken cancellationToken)
        {
            var output = $"{job.JobId}{Environment.NewLine}{job.PayloadJson}";
            await File.WriteAllTextAsync(outputPath, output, cancellationToken);
            return outputPath;
        }
    }

    private sealed class ThrowingPrintExecutor : IJobExecutor
    {
        public JobType SupportedJobType => JobType.Print;

        public string OutputAssetType => "print_output";

        public Task<string> ExecuteAsync(
            JobDetailsApiResponse job,
            string outputPath,
            CancellationToken cancellationToken)
        {
            throw new InvalidOperationException("internal device detail");
        }
    }
}
