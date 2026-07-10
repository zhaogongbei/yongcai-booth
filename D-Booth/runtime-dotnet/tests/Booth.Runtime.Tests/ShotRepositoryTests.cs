using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class ShotRepositoryTests
{
    [Fact]
    public async Task SaveAsync_ShouldRejectCrossSessionReassignment()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"booth-runtime-shot-repository-{Guid.NewGuid():N}.db");
        var repository = new SqliteShotRepository(databasePath);
        var original = new Shot("shot_owner", 1, DateTimeOffset.UtcNow, "owner.jpg", metadata: null, aiPickScore: null);
        var conflicting = new Shot("shot_owner", 1, DateTimeOffset.UtcNow.AddSeconds(1), "other.jpg", metadata: null, aiPickScore: null);

        await repository.SaveAsync("ses_owner", original, CancellationToken.None);

        await Assert.ThrowsAsync<InvalidOperationException>(() => repository.SaveAsync(
            "ses_other",
            conflicting,
            CancellationToken.None));

        Assert.Single(await repository.ListBySessionAsync("ses_owner", CancellationToken.None));
        Assert.Empty(await repository.ListBySessionAsync("ses_other", CancellationToken.None));
    }

    [Fact]
    public async Task TryAddAsync_ShouldPreserveOriginalShotOwnership()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"booth-runtime-shot-try-add-{Guid.NewGuid():N}.db");
        var repository = new SqliteShotRepository(databasePath);
        var original = new Shot("shot_try_add", 1, DateTimeOffset.UtcNow, "owner.jpg", metadata: null, aiPickScore: null);
        var conflicting = new Shot("shot_try_add", 1, DateTimeOffset.UtcNow.AddSeconds(1), "other.jpg", metadata: null, aiPickScore: null);

        Assert.True(await repository.TryAddAsync("ses_owner", original, CancellationToken.None));
        Assert.False(await repository.TryAddAsync("ses_other", conflicting, CancellationToken.None));
        Assert.True(await repository.ExistsAsync(original.Id, CancellationToken.None));

        Assert.Single(await repository.ListBySessionAsync("ses_owner", CancellationToken.None));
        Assert.Empty(await repository.ListBySessionAsync("ses_other", CancellationToken.None));
    }
}
