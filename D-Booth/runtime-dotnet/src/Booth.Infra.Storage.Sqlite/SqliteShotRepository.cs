using Booth.Domain.Session;
using Microsoft.Data.Sqlite;

namespace Booth.Infra.Storage.Sqlite;

public sealed class SqliteShotRepository : IShotRepository
{
    private readonly string _connectionString;

    public SqliteShotRepository(string databasePath)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(databasePath)!);
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = databasePath,
            Mode = SqliteOpenMode.ReadWriteCreate
        }.ToString();

        Initialize();
    }

    public async Task<int> GetNextShotIndexAsync(string sessionId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText = "SELECT COALESCE(MAX(shot_index), 0) + 1 FROM shots WHERE session_id = $sessionId;";
        command.Parameters.AddWithValue("$sessionId", sessionId);

        var result = await command.ExecuteScalarAsync(cancellationToken);
        return Convert.ToInt32(result);
    }

    public async Task SaveAsync(string sessionId, Shot shot, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            INSERT INTO shots (id, session_id, shot_index, raw_asset_path, captured_at_utc, ai_pick_score)
            VALUES ($id, $sessionId, $shotIndex, $rawAssetPath, $capturedAtUtc, $aiPickScore)
            ON CONFLICT(id) DO UPDATE SET
                session_id = excluded.session_id,
                shot_index = excluded.shot_index,
                raw_asset_path = excluded.raw_asset_path,
                captured_at_utc = excluded.captured_at_utc,
                ai_pick_score = excluded.ai_pick_score;
            """;

        command.Parameters.AddWithValue("$id", shot.Id);
        command.Parameters.AddWithValue("$sessionId", sessionId);
        command.Parameters.AddWithValue("$shotIndex", shot.Index);
        command.Parameters.AddWithValue("$rawAssetPath", shot.RawAssetPath ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$capturedAtUtc", shot.CapturedAtUtc.UtcDateTime.ToString("O"));
        command.Parameters.AddWithValue("$aiPickScore", shot.AiPickScore ?? (object)DBNull.Value);

        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    public async Task<IReadOnlyList<Shot>> ListBySessionAsync(string sessionId, CancellationToken cancellationToken)
    {
        var results = new List<Shot>();

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, shot_index, raw_asset_path, captured_at_utc, ai_pick_score
            FROM shots
            WHERE session_id = $sessionId
            ORDER BY shot_index ASC;
            """;
        command.Parameters.AddWithValue("$sessionId", sessionId);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            results.Add(new Shot(
                reader.GetString(0),
                reader.GetInt32(1),
                DateTimeOffset.Parse(reader.GetString(3)),
                reader.IsDBNull(2) ? null : reader.GetString(2),
                metadata: null,
                reader.IsDBNull(4) ? null : reader.GetDouble(4)));
        }

        return results;
    }

    public async Task SaveManyAsync(
        string sessionId,
        IEnumerable<Shot> shots,
        CancellationToken cancellationToken)
    {
        foreach (var shot in shots)
        {
            await SaveAsync(sessionId, shot, cancellationToken);
        }
    }

    public async Task DeleteBySessionAsync(string sessionId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText = "DELETE FROM shots WHERE session_id = $sessionId;";
        command.Parameters.AddWithValue("$sessionId", sessionId);

        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private void Initialize()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText =
            """
            CREATE TABLE IF NOT EXISTS shots (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                shot_index INTEGER NOT NULL,
                raw_asset_path TEXT NULL,
                captured_at_utc TEXT NOT NULL,
                ai_pick_score REAL NULL
            );
            """;
        command.ExecuteNonQuery();
    }
}
