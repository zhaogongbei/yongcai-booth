using Booth.Shared.Contracts;
using Microsoft.Data.Sqlite;

namespace Booth.Infra.Storage.Sqlite;

public sealed class SqliteOutputAssetRepository
{
    private readonly string _connectionString;

    public SqliteOutputAssetRepository(string databasePath)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(databasePath)!);
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = databasePath,
            Mode = SqliteOpenMode.ReadWriteCreate
        }.ToString();

        Initialize();
    }

    public async Task<string> CreateAsync(
        string sessionId,
        string assetType,
        string storageScope,
        string? localPath,
        string? remoteUrl,
        CancellationToken cancellationToken)
    {
        var assetId = $"asset_{Guid.NewGuid():N}";

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            INSERT INTO output_assets (id, session_id, asset_type, storage_scope, local_path, remote_url, created_at_utc, is_deleted)
            VALUES ($id, $sessionId, $assetType, $storageScope, $localPath, $remoteUrl, $createdAtUtc, 0);
            """;

        command.Parameters.AddWithValue("$id", assetId);
        command.Parameters.AddWithValue("$sessionId", sessionId);
        command.Parameters.AddWithValue("$assetType", assetType);
        command.Parameters.AddWithValue("$storageScope", storageScope);
        command.Parameters.AddWithValue("$localPath", localPath ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$remoteUrl", remoteUrl ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$createdAtUtc", DateTimeOffset.UtcNow.UtcDateTime.ToString("O"));

        await command.ExecuteNonQueryAsync(cancellationToken);
        return assetId;
    }

    public async Task<IReadOnlyList<OutputAssetApiResponse>> ListBySessionAsync(string sessionId, CancellationToken cancellationToken)
    {
        var results = new List<OutputAssetApiResponse>();

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, session_id, asset_type, storage_scope, local_path, remote_url, created_at_utc
            FROM output_assets
            WHERE session_id = $sessionId AND is_deleted = 0
            ORDER BY created_at_utc ASC;
            """;
        command.Parameters.AddWithValue("$sessionId", sessionId);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            results.Add(new OutputAssetApiResponse(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                reader.GetString(3),
                reader.IsDBNull(4) ? null : reader.GetString(4),
                reader.IsDBNull(5) ? null : reader.GetString(5),
                reader.GetString(6)));
        }

        return results;
    }

    public async Task<OutputAssetApiResponse?> GetAsync(string assetId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, session_id, asset_type, storage_scope, local_path, remote_url, created_at_utc
            FROM output_assets
            WHERE id = $assetId AND is_deleted = 0;
            """;
        command.Parameters.AddWithValue("$assetId", assetId);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            return null;
        }

        return new OutputAssetApiResponse(
            reader.GetString(0),
            reader.GetString(1),
            reader.GetString(2),
            reader.GetString(3),
            reader.IsDBNull(4) ? null : reader.GetString(4),
            reader.IsDBNull(5) ? null : reader.GetString(5),
            reader.GetString(6));
    }

    public async Task<bool> SoftDeleteAsync(string assetId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            UPDATE output_assets
            SET is_deleted = 1
            WHERE id = $assetId AND is_deleted = 0;
            """;
        command.Parameters.AddWithValue("$assetId", assetId);

        var affected = await command.ExecuteNonQueryAsync(cancellationToken);
        return affected > 0;
    }

    private void Initialize()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText =
            """
            CREATE TABLE IF NOT EXISTS output_assets (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                storage_scope TEXT NOT NULL,
                local_path TEXT NULL,
                remote_url TEXT NULL,
                created_at_utc TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
            """;
        command.ExecuteNonQuery();
    }
}
