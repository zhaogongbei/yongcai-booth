using Booth.Shared.Contracts;
using Microsoft.Data.Sqlite;
using System.Text.Json;

namespace Booth.Infra.Storage.Sqlite;

public sealed class SqliteJobRepository
{
    private readonly string _connectionString;

    public SqliteJobRepository(string databasePath)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(databasePath)!);
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = databasePath,
            Mode = SqliteOpenMode.ReadWriteCreate
        }.ToString();

        Initialize();
    }

    public async Task<string> QueueJobAsync(
        JobType jobType,
        string aggregateId,
        int priority,
        CancellationToken cancellationToken,
        object? payload = null,
        string? lastErrorCode = null,
        string? lastErrorMessage = null)
    {
        var jobId = $"job_{jobType.ToString().ToLowerInvariant()}_{Guid.NewGuid():N}";
        var payloadJson = payload is null ? null : JsonSerializer.Serialize(payload);

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            INSERT INTO jobs (id, job_type, aggregate_id, status, priority, attempt_count, scheduled_at_utc, payload_json, created_asset_id, last_error_code, last_error_message)
            VALUES ($id, $jobType, $aggregateId, $status, $priority, $attemptCount, $scheduledAtUtc, $payloadJson, NULL, $lastErrorCode, $lastErrorMessage);
            """;

        command.Parameters.AddWithValue("$id", jobId);
        command.Parameters.AddWithValue("$jobType", jobType.ToString());
        command.Parameters.AddWithValue("$aggregateId", aggregateId);
        command.Parameters.AddWithValue("$status", JobStatus.Queued.ToString());
        command.Parameters.AddWithValue("$priority", priority);
        command.Parameters.AddWithValue("$attemptCount", 0);
        command.Parameters.AddWithValue("$scheduledAtUtc", DateTimeOffset.UtcNow.UtcDateTime.ToString("O"));
        command.Parameters.AddWithValue("$payloadJson", payloadJson ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$lastErrorCode", lastErrorCode ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$lastErrorMessage", lastErrorMessage ?? (object)DBNull.Value);

        await command.ExecuteNonQueryAsync(cancellationToken);
        return jobId;
    }

    public async Task<JobDetailsApiResponse?> GetAsync(string jobId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, job_type, aggregate_id, status, priority, attempt_count, scheduled_at_utc, payload_json, created_asset_id, last_error_code, last_error_message
            FROM jobs
            WHERE id = $id;
            """;
        command.Parameters.AddWithValue("$id", jobId);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            return null;
        }

        return new JobDetailsApiResponse(
            reader.GetString(0),
            reader.GetString(1),
            reader.GetString(2),
            reader.GetString(3),
            reader.GetInt32(4),
            reader.GetInt32(5),
            reader.GetString(6),
            reader.IsDBNull(7) ? null : reader.GetString(7),
            reader.IsDBNull(8) ? null : reader.GetString(8),
            reader.IsDBNull(9) ? null : reader.GetString(9),
            reader.IsDBNull(10) ? null : reader.GetString(10));
    }

    public async Task<IReadOnlyList<JobDetailsApiResponse>> ListByAggregateAsync(string aggregateId, CancellationToken cancellationToken)
    {
        var results = new List<JobDetailsApiResponse>();

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, job_type, aggregate_id, status, priority, attempt_count, scheduled_at_utc, payload_json, created_asset_id, last_error_code, last_error_message
            FROM jobs
            WHERE aggregate_id = $aggregateId
            ORDER BY scheduled_at_utc ASC, priority DESC;
            """;
        command.Parameters.AddWithValue("$aggregateId", aggregateId);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            results.Add(new JobDetailsApiResponse(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                reader.GetString(3),
                reader.GetInt32(4),
                reader.GetInt32(5),
                reader.GetString(6),
                reader.IsDBNull(7) ? null : reader.GetString(7),
                reader.IsDBNull(8) ? null : reader.GetString(8),
                reader.IsDBNull(9) ? null : reader.GetString(9),
                reader.IsDBNull(10) ? null : reader.GetString(10)));
        }

        return results;
    }

    public async Task UpdateStatusAsync(
        string jobId,
        JobStatus status,
        CancellationToken cancellationToken,
        string? createdAssetId = null,
        string? lastErrorCode = null,
        string? lastErrorMessage = null)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            UPDATE jobs
            SET status = $status,
                created_asset_id = COALESCE($createdAssetId, created_asset_id),
                last_error_code = $lastErrorCode,
                last_error_message = $lastErrorMessage
            WHERE id = $id;
            """;

        command.Parameters.AddWithValue("$id", jobId);
        command.Parameters.AddWithValue("$status", status.ToString());
        command.Parameters.AddWithValue("$createdAssetId", createdAssetId ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$lastErrorCode", lastErrorCode ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$lastErrorMessage", lastErrorMessage ?? (object)DBNull.Value);

        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private void Initialize()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText =
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 100,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                scheduled_at_utc TEXT NOT NULL,
                payload_json TEXT NULL,
                created_asset_id TEXT NULL,
                last_error_code TEXT NULL,
                last_error_message TEXT NULL
            );
            """;
        command.ExecuteNonQuery();

        EnsureColumn(connection, "jobs", "payload_json", "TEXT NULL");
        EnsureColumn(connection, "jobs", "created_asset_id", "TEXT NULL");
    }

    private static void EnsureColumn(SqliteConnection connection, string tableName, string columnName, string columnDefinition)
    {
        using var check = connection.CreateCommand();
        check.CommandText = $"PRAGMA table_info({tableName});";
        using var reader = check.ExecuteReader();
        while (reader.Read())
        {
            if (string.Equals(reader.GetString(1), columnName, StringComparison.OrdinalIgnoreCase))
            {
                return;
            }
        }

        using var alter = connection.CreateCommand();
        alter.CommandText = $"ALTER TABLE {tableName} ADD COLUMN {columnName} {columnDefinition};";
        alter.ExecuteNonQuery();
    }
}
