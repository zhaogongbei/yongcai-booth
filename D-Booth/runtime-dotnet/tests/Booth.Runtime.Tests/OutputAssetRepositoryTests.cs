using Booth.Infra.Storage.Sqlite;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class OutputAssetRepositoryTests
{
    [Fact]
    public async Task SoftDelete_ShouldHideAssetFromQueries()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"booth-runtime-asset-{Guid.NewGuid():N}.db");
        var repository = new SqliteOutputAssetRepository(databasePath);

        var assetId = await repository.CreateAsync(
            "ses_test_asset_001",
            "print_output",
            "local",
            "C:\\temp\\asset.json",
            null,
            CancellationToken.None);

        var beforeDelete = await repository.GetAsync(assetId, CancellationToken.None);
        var deleted = await repository.SoftDeleteAsync(assetId, CancellationToken.None);
        var afterDelete = await repository.GetAsync(assetId, CancellationToken.None);
        var listAfterDelete = await repository.ListBySessionAsync("ses_test_asset_001", CancellationToken.None);

        Assert.NotNull(beforeDelete);
        Assert.True(deleted);
        Assert.Null(afterDelete);
        Assert.Empty(listAfterDelete);
    }
}
