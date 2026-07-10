using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Booth.Plugin.Abstractions;
using Booth.Plugin.Abstractions.Camera;
using Booth.Plugin.Abstractions.Lifecycle;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class SessionCaptureFlowTests
{
    [Fact]
    public async Task CaptureShot_ShouldPersistShot_WhenCameraProducesValidJpeg()
    {
        var context = CreateContext(new TestCameraPlugin(async (config, cancellationToken) =>
        {
            await File.WriteAllBytesAsync(
                config.OutputPath,
                new byte[] { 0xFF, 0xD8, 0xFF, 0xE0, 0xFF, 0xD9 },
                cancellationToken);
            return CaptureResult.Successful(config.OutputPath);
        }));

        await context.Service.StartAsync(
            new SessionStartRequest("ses_test_capture_001", "evt_test_capture_001", SessionMode.Print, "dev_test_capture_001"),
            CancellationToken.None);

        var shot = await context.Service.CaptureShotAsync(
            new CaptureShotRequest("ses_test_capture_001", null, "unit-test", 0.91),
            CancellationToken.None);

        var shots = await context.Service.ListShotsAsync("ses_test_capture_001", CancellationToken.None);

        Assert.NotNull(shot);
        Assert.Single(shots);
        Assert.Equal(1, shots[0].Index);
        Assert.NotNull(shots[0].RawAssetPath);
        Assert.True(File.Exists(shots[0].RawAssetPath));
    }

    [Fact]
    public async Task CaptureShot_ShouldFailClosed_WhenCameraIsNotConfigured()
    {
        var context = CreateContext(cameraPlugin: null);
        await context.Service.StartAsync(
            new SessionStartRequest("ses_camera_missing", "evt_camera_missing", SessionMode.Print, "dev_camera_missing"),
            CancellationToken.None);

        var exception = await Assert.ThrowsAsync<CaptureShotException>(() => context.Service.CaptureShotAsync(
            new CaptureShotRequest("ses_camera_missing", "shot_camera_missing", null, null),
            CancellationToken.None));

        var shots = await context.Service.ListShotsAsync("ses_camera_missing", CancellationToken.None);
        var session = await context.Service.GetAsync("ses_camera_missing", CancellationToken.None);

        Assert.Equal(ErrorCodes.CameraDeviceNotReady, exception.ErrorCode);
        Assert.Empty(shots);
        Assert.NotNull(session);
        Assert.Equal(SessionStatus.Countdown, session!.Status);
        Assert.False(Directory.Exists(Path.Combine(context.CapturesRoot, "ses_camera_missing")));
    }

    [Fact]
    public async Task CaptureShot_ShouldFailClosed_WhenPluginReportsSuccessWithoutValidJpeg()
    {
        var context = CreateContext(new TestCameraPlugin(async (config, cancellationToken) =>
        {
            await File.WriteAllTextAsync(config.OutputPath, "not-a-jpeg", cancellationToken);
            return CaptureResult.Successful(config.OutputPath);
        }));
        await context.Service.StartAsync(
            new SessionStartRequest("ses_invalid_jpeg", "evt_invalid_jpeg", SessionMode.Print, "dev_invalid_jpeg"),
            CancellationToken.None);

        var exception = await Assert.ThrowsAsync<CaptureShotException>(() => context.Service.CaptureShotAsync(
            new CaptureShotRequest("ses_invalid_jpeg", "shot_invalid_jpeg", null, null),
            CancellationToken.None));

        Assert.Equal(ErrorCodes.CameraDeviceNotReady, exception.ErrorCode);
        Assert.Empty(await context.Service.ListShotsAsync("ses_invalid_jpeg", CancellationToken.None));
        Assert.False(File.Exists(Path.Combine(context.CapturesRoot, "ses_invalid_jpeg", "shot_invalid_jpeg.jpg")));
    }

    [Theory]
    [InlineData("../outside")]
    [InlineData("..\\outside")]
    public async Task CaptureShot_ShouldRejectPathTraversal_InPreferredShotId(string preferredShotId)
    {
        var camera = new TestCameraPlugin((config, cancellationToken) =>
            Task.FromResult(CaptureResult.Successful(config.OutputPath)));
        var context = CreateContext(camera);
        await context.Service.StartAsync(
            new SessionStartRequest("ses_safe_path", "evt_safe_path", SessionMode.Print, "dev_safe_path"),
            CancellationToken.None);

        var exception = await Assert.ThrowsAsync<CaptureShotException>(() => context.Service.CaptureShotAsync(
            new CaptureShotRequest("ses_safe_path", preferredShotId, null, null),
            CancellationToken.None));

        Assert.Equal(ErrorCodes.ConfigurationInvalid, exception.ErrorCode);
        Assert.Equal(0, camera.CaptureCallCount);
        Assert.Empty(await context.Service.ListShotsAsync("ses_safe_path", CancellationToken.None));
    }

    [Fact]
    public async Task CaptureShot_ShouldRejectDuplicateShotIdWithoutReassigningOrOverwriting()
    {
        var camera = new TestCameraPlugin(async (config, cancellationToken) =>
        {
            await File.WriteAllBytesAsync(
                config.OutputPath,
                new byte[] { 0xFF, 0xD8, 0xFF, 0xE0, 0x01, 0xFF, 0xD9 },
                cancellationToken);
            return CaptureResult.Successful(config.OutputPath);
        });
        var context = CreateContext(camera);
        await context.Service.StartAsync(
            new SessionStartRequest("ses_shot_owner", "evt_shot_owner", SessionMode.Print, "dev_shot_owner"),
            CancellationToken.None);
        await context.Service.StartAsync(
            new SessionStartRequest("ses_shot_contender", "evt_shot_contender", SessionMode.Print, "dev_shot_contender"),
            CancellationToken.None);

        var original = await context.Service.CaptureShotAsync(
            new CaptureShotRequest("ses_shot_owner", "shot_shared", null, null),
            CancellationToken.None);
        var originalBytes = await File.ReadAllBytesAsync(original!.RawAssetPath!);

        var exception = await Assert.ThrowsAsync<CaptureShotException>(() => context.Service.CaptureShotAsync(
            new CaptureShotRequest("ses_shot_contender", "shot_shared", null, null),
            CancellationToken.None));

        Assert.Equal(ErrorCodes.ShotConflict, exception.ErrorCode);
        Assert.Equal(1, camera.CaptureCallCount);
        Assert.Equal(originalBytes, await File.ReadAllBytesAsync(original.RawAssetPath!));
        Assert.Single(await context.Service.ListShotsAsync("ses_shot_owner", CancellationToken.None));
        Assert.Empty(await context.Service.ListShotsAsync("ses_shot_contender", CancellationToken.None));
        Assert.False(File.Exists(Path.Combine(context.CapturesRoot, "ses_shot_contender", "shot_shared.jpg")));
    }

    private static TestContext CreateContext(ICameraPlugin? cameraPlugin)
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-shot-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var capturesRoot = Path.Combine(tempRoot, "captures");
        var sessionRepository = new SqliteSessionRepository(databasePath);
        var shotRepository = new SqliteShotRepository(databasePath);
        var service = new SessionApplicationService(sessionRepository, shotRepository, capturesRoot, cameraPlugin);
        return new TestContext(service, capturesRoot);
    }

    private sealed record TestContext(SessionApplicationService Service, string CapturesRoot);

    private sealed class TestCameraPlugin : ICameraPlugin
    {
        private readonly Func<CaptureConfig, CancellationToken, Task<CaptureResult>> _capture;

        public TestCameraPlugin(Func<CaptureConfig, CancellationToken, Task<CaptureResult>> capture)
        {
            _capture = capture;
        }

        public string Id => "test.camera";
        public string Name => "Test Camera";
        public string Version => "1.0.0";
        public bool IsConnected => true;
        public CameraDescriptor? ConnectedCamera => new("test-camera", "Test", "Camera", Array.Empty<string>());
        public int CaptureCallCount { get; private set; }

        public Task InitializeAsync(IPluginContext context, CancellationToken cancellationToken) => Task.CompletedTask;
        public Task ShutdownAsync(CancellationToken cancellationToken) => Task.CompletedTask;
        public Task<IReadOnlyList<CameraDescriptor>> DiscoverAsync(CancellationToken cancellationToken) =>
            Task.FromResult<IReadOnlyList<CameraDescriptor>>(new[] { ConnectedCamera! });
        public Task<bool> ConnectAsync(string deviceId, CancellationToken cancellationToken) => Task.FromResult(true);
        public Task DisconnectAsync(CancellationToken cancellationToken) => Task.CompletedTask;

        public Task<CaptureResult> CaptureAsync(CaptureConfig config, CancellationToken cancellationToken)
        {
            CaptureCallCount++;
            return _capture(config, cancellationToken);
        }
    }
}
