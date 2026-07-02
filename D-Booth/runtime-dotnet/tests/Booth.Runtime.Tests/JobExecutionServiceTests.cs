using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.JobApp;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class JobExecutionServiceTests
{
    [Fact]
    public async Task ExecuteAsync_ShouldMarkJobSucceeded_AndCreateOutputAsset()
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
            new IJobExecutor[] { new PrintJobExecutor(), new ShareJobExecutor() },
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
}
