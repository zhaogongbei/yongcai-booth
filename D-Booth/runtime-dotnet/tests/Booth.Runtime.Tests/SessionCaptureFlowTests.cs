using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class SessionCaptureFlowTests
{
    [Fact]
    public async Task CaptureShot_ShouldPersistShot_AndCreateRawCaptureFile()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-shot-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var capturesRoot = Path.Combine(tempRoot, "captures");

        var sessionRepository = new SqliteSessionRepository(databasePath);
        var shotRepository = new SqliteShotRepository(databasePath);
        var service = new SessionApplicationService(sessionRepository, shotRepository, capturesRoot);

        await service.StartAsync(
            new SessionStartRequest("ses_test_capture_001", "evt_test_capture_001", SessionMode.Print, "dev_test_capture_001"),
            CancellationToken.None);

        var shot = await service.CaptureShotAsync(
            new CaptureShotRequest("ses_test_capture_001", null, "unit-test", 0.91),
            CancellationToken.None);

        var shots = await service.ListShotsAsync("ses_test_capture_001", CancellationToken.None);

        Assert.NotNull(shot);
        Assert.Single(shots);
        Assert.Equal(1, shots[0].Index);
        Assert.NotNull(shots[0].RawAssetPath);
        Assert.True(File.Exists(shots[0].RawAssetPath));

        var content = await File.ReadAllTextAsync(shots[0].RawAssetPath!);
        Assert.Contains("ses_test_capture_001", content);
        Assert.Contains("unit-test", content);
    }
}
