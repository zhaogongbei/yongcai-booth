using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class SessionStartFlowTests
{
    [Fact]
    public async Task StartAsync_ShouldReturnExistingSessionWithoutResettingState_WhenIdentityMatches()
    {
        var context = CreateContext();
        var request = new SessionStartRequest(
            "ses_idempotent_start",
            "evt_idempotent_start",
            SessionMode.Print,
            "dev_idempotent_start");

        var started = await context.Service.StartAsync(request, CancellationToken.None);
        var cancelled = await context.Service.CancelAsync(request.SessionId, CancellationToken.None);
        var repeated = await context.Service.StartAsync(request, CancellationToken.None);

        Assert.NotNull(cancelled);
        Assert.Equal(SessionStatus.Cancelled, repeated.Status);
        Assert.Equal(started.StartedAtUtc.ToString("O"), repeated.StartedAtUtc.ToString("O"));
        Assert.Equal(cancelled!.CompletedAtUtc?.ToString("O"), repeated.CompletedAtUtc?.ToString("O"));
    }

    [Fact]
    public async Task StartAsync_ShouldRejectDifferentIdentityAndPreserveExistingSession()
    {
        var context = CreateContext();
        var originalRequest = new SessionStartRequest(
            "ses_identity_conflict",
            "evt_original",
            SessionMode.Print,
            "dev_original");

        await context.Service.StartAsync(originalRequest, CancellationToken.None);

        var exception = await Assert.ThrowsAsync<SessionStartException>(() => context.Service.StartAsync(
            originalRequest with { EventId = "evt_other" },
            CancellationToken.None));
        var persisted = await context.Service.GetAsync(originalRequest.SessionId, CancellationToken.None);

        Assert.Equal(ErrorCodes.SessionConflict, exception.ErrorCode);
        Assert.NotNull(persisted);
        Assert.Equal(originalRequest.EventId, persisted!.EventId);
        Assert.Equal(originalRequest.DeviceId, persisted.DeviceId);
        Assert.Equal(SessionStatus.Countdown, persisted.Status);
    }

    [Fact]
    public async Task StartAsync_ShouldAllowOnlyOneIdentity_WhenRequestsRaceForSameSessionId()
    {
        var context = CreateContext();
        var requests = new[]
        {
            new SessionStartRequest("ses_race", "evt_race_a", SessionMode.Print, "dev_race_a"),
            new SessionStartRequest("ses_race", "evt_race_b", SessionMode.Gif, "dev_race_b")
        };

        var attempts = await Task.WhenAll(requests.Select(async request =>
        {
            try
            {
                return (Session: await context.Service.StartAsync(request, CancellationToken.None), Error: (SessionStartException?)null);
            }
            catch (SessionStartException exception)
            {
                return (Session: (SessionAggregate?)null, Error: exception);
            }
        }));
        var persisted = await context.Service.GetAsync("ses_race", CancellationToken.None);

        var winner = Assert.Single(attempts.Where(attempt => attempt.Session is not null)).Session!;
        var loser = Assert.Single(attempts.Where(attempt => attempt.Error is not null)).Error!;
        Assert.Equal(ErrorCodes.SessionConflict, loser.ErrorCode);
        Assert.NotNull(persisted);
        Assert.Equal(winner.EventId, persisted!.EventId);
        Assert.Equal(winner.Mode, persisted.Mode);
        Assert.Equal(winner.DeviceId, persisted.DeviceId);
    }

    private static TestContext CreateContext()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-session-start-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        var databasePath = Path.Combine(tempRoot, "runtime.db");
        var service = new SessionApplicationService(
            new SqliteSessionRepository(databasePath),
            new SqliteShotRepository(databasePath),
            Path.Combine(tempRoot, "captures"));
        return new TestContext(service);
    }

    private sealed record TestContext(SessionApplicationService Service);
}
