using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;

var options = RuntimeAppOptions.Parse(args);
if (options is null)
{
    Console.Error.WriteLine("Usage: Booth.Runtime.App --session-id <id> --event-id <id> --device-id <id> [--mode print|share|ai]");
    return 2;
}

var dataDir = Path.Combine(AppContext.BaseDirectory, "data");
var databasePath = Path.Combine(dataDir, "runtime.db");
var repository = new SqliteSessionRepository(databasePath);
var shotRepository = new SqliteShotRepository(databasePath);
var capturesRoot = Path.Combine(dataDir, "captures");
var service = new SessionApplicationService(repository, shotRepository, capturesRoot);

var session = await service.StartAsync(
    new SessionStartRequest(
        options.SessionId,
        options.EventId,
        options.Mode,
        options.DeviceId),
    CancellationToken.None);

Console.WriteLine($"Booth Runtime started session: {session.Id} [{session.Status}]");
return 0;

internal sealed record RuntimeAppOptions(
    string SessionId,
    string EventId,
    string DeviceId,
    SessionMode Mode)
{
    public static RuntimeAppOptions? Parse(string[] args)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < args.Length; index++)
        {
            var key = args[index];
            if (!key.StartsWith("--", StringComparison.Ordinal) || index + 1 >= args.Length)
            {
                return null;
            }

            values[key[2..]] = args[++index];
        }

        if (!TryGetRequired(values, "session-id", out var sessionId)
            || !TryGetRequired(values, "event-id", out var eventId)
            || !TryGetRequired(values, "device-id", out var deviceId))
        {
            return null;
        }

        var mode = SessionMode.Print;
        if (values.TryGetValue("mode", out var modeValue)
            && !Enum.TryParse(modeValue, ignoreCase: true, out mode))
        {
            return null;
        }

        return new RuntimeAppOptions(sessionId, eventId, deviceId, mode);
    }

    private static bool TryGetRequired(
        IReadOnlyDictionary<string, string> values,
        string key,
        out string value)
    {
        if (values.TryGetValue(key, out var rawValue) && !string.IsNullOrWhiteSpace(rawValue))
        {
            value = rawValue;
            return true;
        }

        value = string.Empty;
        return false;
    }
}