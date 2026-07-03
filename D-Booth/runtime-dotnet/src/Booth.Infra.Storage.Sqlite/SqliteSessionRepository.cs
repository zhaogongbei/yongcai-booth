using Booth.Domain.Session;
using Booth.Shared.Contracts;
using Microsoft.Data.Sqlite;

namespace Booth.Infra.Storage.Sqlite;

/// <summary>
/// SQLite implementation of <see cref="ISessionRepository"/>.
/// Provides efficient persistence for session aggregates with batch operation support.
/// </summary>
public sealed class SqliteSessionRepository : ISessionRepository
{
    private readonly string _connectionString;

    /// <summary>
    /// Creates a new SQLite session repository.
    /// </summary>
    /// <param name="databasePath">Path to the SQLite database file.</param>
    public SqliteSessionRepository(string databasePath)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(databasePath)!);
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = databasePath,
            Mode = SqliteOpenMode.ReadWriteCreate
        }.ToString();

        Initialize();
    }

    /// <inheritdoc />
    public async Task SaveAsync(SessionAggregate session, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            INSERT INTO sessions (id, event_id, session_mode, status, started_at_utc, completed_at_utc, device_id, retry_count)
            VALUES ($id, $eventId, $mode, $status, $startedAt, $completedAt, $deviceId, $retryCount)
            ON CONFLICT(id) DO UPDATE SET
                event_id = excluded.event_id,
                session_mode = excluded.session_mode,
                status = excluded.status,
                started_at_utc = excluded.started_at_utc,
                completed_at_utc = excluded.completed_at_utc,
                device_id = excluded.device_id,
                retry_count = excluded.retry_count;
            """;

        command.Parameters.AddWithValue("$id", session.Id);
        command.Parameters.AddWithValue("$eventId", session.EventId);
        command.Parameters.AddWithValue("$mode", session.Mode.ToString());
        command.Parameters.AddWithValue("$status", session.Status.ToString());
        command.Parameters.AddWithValue("$startedAt", session.StartedAtUtc.UtcDateTime.ToString("O"));
        command.Parameters.AddWithValue("$completedAt", session.CompletedAtUtc?.UtcDateTime.ToString("O") ?? (object)DBNull.Value);
        command.Parameters.AddWithValue("$deviceId", session.DeviceId);
        command.Parameters.AddWithValue("$retryCount", session.RetryCount);

        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    /// <inheritdoc />
    public async Task<SessionAggregate?> GetAsync(string sessionId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, event_id, session_mode, status, started_at_utc, completed_at_utc, device_id, retry_count
            FROM sessions
            WHERE id = $id;
            """;
        command.Parameters.AddWithValue("$id", sessionId);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            return null;
        }

        return SessionAggregate.Rehydrate(
            reader.GetString(0),
            reader.GetString(1),
            Enum.Parse<SessionMode>(reader.GetString(2)),
            reader.GetString(6),
            Enum.Parse<SessionStatus>(reader.GetString(3)),
            DateTimeOffset.Parse(reader.GetString(4)),
            reader.IsDBNull(5) ? null : DateTimeOffset.Parse(reader.GetString(5)),
            reader.GetInt32(7));
    }

    /// <inheritdoc />
    public async Task<IReadOnlyList<SessionAggregate>> GetManyAsync(IEnumerable<string> sessionIds, CancellationToken cancellationToken)
    {
        var idList = sessionIds.ToList();
        if (idList.Count == 0)
            return Array.Empty<SessionAggregate>();

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var placeholders = string.Join(",", idList.Select((_, i) => $"$id{i}"));
        var command = connection.CreateCommand();
        command.CommandText = $"""
            SELECT id, event_id, session_mode, status, started_at_utc, completed_at_utc, device_id, retry_count
            FROM sessions
            WHERE id IN ({placeholders});
            """;

        for (int i = 0; i < idList.Count; i++)
        {
            command.Parameters.AddWithValue($"$id{i}", idList[i]);
        }

        var results = new List<SessionAggregate>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            results.Add(SessionAggregate.Rehydrate(
                reader.GetString(0),
                reader.GetString(1),
                Enum.Parse<SessionMode>(reader.GetString(2)),
                reader.GetString(6),
                Enum.Parse<SessionStatus>(reader.GetString(3)),
                DateTimeOffset.Parse(reader.GetString(4)),
                reader.IsDBNull(5) ? null : DateTimeOffset.Parse(reader.GetString(5)),
                reader.GetInt32(7)));
        }

        return results;
    }

    /// <inheritdoc />
    public async Task<IReadOnlyList<SessionAggregate>> GetByEventAsync(string eventId, CancellationToken cancellationToken)
    {
        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        var command = connection.CreateCommand();
        command.CommandText =
            """
            SELECT id, event_id, session_mode, status, started_at_utc, completed_at_utc, device_id, retry_count
            FROM sessions
            WHERE event_id = $eventId
            ORDER BY started_at_utc DESC;
            """;
        command.Parameters.AddWithValue("$eventId", eventId);

        var results = new List<SessionAggregate>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            results.Add(SessionAggregate.Rehydrate(
                reader.GetString(0),
                reader.GetString(1),
                Enum.Parse<SessionMode>(reader.GetString(2)),
                reader.GetString(6),
                Enum.Parse<SessionStatus>(reader.GetString(3)),
                DateTimeOffset.Parse(reader.GetString(4)),
                reader.IsDBNull(5) ? null : DateTimeOffset.Parse(reader.GetString(5)),
                reader.GetInt32(7)));
        }

        return results;
    }

    /// <inheritdoc />
    public async Task SaveManyAsync(IEnumerable<SessionAggregate> sessions, CancellationToken cancellationToken)
    {
        var sessionList = sessions.ToList();
        if (sessionList.Count == 0)
            return;

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);

        await using var transaction = (SqliteTransaction)await connection.BeginTransactionAsync(cancellationToken);
        try
        {
            var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText =
                """
                INSERT INTO sessions (id, event_id, session_mode, status, started_at_utc, completed_at_utc, device_id, retry_count)
                VALUES ($id, $eventId, $mode, $status, $startedAt, $completedAt, $deviceId, $retryCount)
                ON CONFLICT(id) DO UPDATE SET
                    event_id = excluded.event_id,
                    session_mode = excluded.session_mode,
                    status = excluded.status,
                    started_at_utc = excluded.started_at_utc,
                    completed_at_utc = excluded.completed_at_utc,
                    device_id = excluded.device_id,
                    retry_count = excluded.retry_count;
                """;

            var idParam = command.Parameters.Add("$id", SqliteType.Text);
            var eventIdParam = command.Parameters.Add("$eventId", SqliteType.Text);
            var modeParam = command.Parameters.Add("$mode", SqliteType.Text);
            var statusParam = command.Parameters.Add("$status", SqliteType.Text);
            var startedAtParam = command.Parameters.Add("$startedAt", SqliteType.Text);
            var completedAtParam = command.Parameters.Add("$completedAt", SqliteType.Text);
            var deviceIdParam = command.Parameters.Add("$deviceId", SqliteType.Text);
            var retryCountParam = command.Parameters.Add("$retryCount", SqliteType.Integer);

            foreach (var session in sessionList)
            {
                idParam.Value = session.Id;
                eventIdParam.Value = session.EventId;
                modeParam.Value = session.Mode.ToString();
                statusParam.Value = session.Status.ToString();
                startedAtParam.Value = session.StartedAtUtc.UtcDateTime.ToString("O");
                completedAtParam.Value = session.CompletedAtUtc?.UtcDateTime.ToString("O") ?? (object)DBNull.Value;
                deviceIdParam.Value = session.DeviceId;
                retryCountParam.Value = session.RetryCount;

                await command.ExecuteNonQueryAsync(cancellationToken);
            }

            await transaction.CommitAsync(cancellationToken);
        }
        catch
        {
            await transaction.RollbackAsync(cancellationToken);
            throw;
        }
    }

    private void Initialize()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();

        var command = connection.CreateCommand();
        command.CommandText =
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                session_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at_utc TEXT NOT NULL,
                completed_at_utc TEXT NULL,
                device_id TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_event_id ON sessions(event_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
            CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at_utc);
            """;
        command.ExecuteNonQuery();
    }
}
