using Booth.Domain.Session;

namespace Booth.Runtime.SessionApp;

public sealed class SessionApplicationService
{
    private readonly ISessionRepository _sessionRepository;
    private readonly IShotRepository _shotRepository;
    private readonly string _capturesRoot;

    public SessionApplicationService(
        ISessionRepository sessionRepository,
        IShotRepository shotRepository,
        string capturesRoot)
    {
        _sessionRepository = sessionRepository;
        _shotRepository = shotRepository;
        _capturesRoot = capturesRoot;
    }

    public async Task<SessionAggregate> StartAsync(SessionStartRequest request, CancellationToken cancellationToken)
    {
        var session = new SessionAggregate(
            request.SessionId,
            request.EventId,
            request.Mode,
            request.DeviceId);

        session.BeginCountdown();
        await _sessionRepository.SaveAsync(session, cancellationToken);
        return session;
    }

    public Task<SessionAggregate?> GetAsync(string sessionId, CancellationToken cancellationToken)
    {
        return _sessionRepository.GetAsync(sessionId, cancellationToken);
    }

    public async Task<SessionAggregate?> CancelAsync(string sessionId, CancellationToken cancellationToken)
    {
        var session = await _sessionRepository.GetAsync(sessionId, cancellationToken);
        if (session is null)
        {
            return null;
        }

        session.Cancel();
        await _sessionRepository.SaveAsync(session, cancellationToken);
        return session;
    }

    public async Task<Shot?> CaptureShotAsync(CaptureShotRequest request, CancellationToken cancellationToken)
    {
        var session = await _sessionRepository.GetAsync(request.SessionId, cancellationToken);
        if (session is null)
        {
            return null;
        }

        session.BeginCapture();
        await _sessionRepository.SaveAsync(session, cancellationToken);

        var shotIndex = await _shotRepository.GetNextShotIndexAsync(request.SessionId, cancellationToken);
        var shotId = request.PreferredShotId ?? $"shot_{Guid.NewGuid():N}";
        var sessionCaptureDirectory = Path.Combine(_capturesRoot, request.SessionId);
        Directory.CreateDirectory(sessionCaptureDirectory);

        var rawAssetPath = Path.Combine(sessionCaptureDirectory, $"{shotId}.jpg");
        var captureTimestamp = DateTimeOffset.UtcNow;
        var capturePayload =
            $$"""
            {
              "sessionId": "{{request.SessionId}}",
              "shotId": "{{shotId}}",
              "shotIndex": {{shotIndex}},
              "sourceLabel": "{{request.SourceLabel ?? "capture"}}",
              "capturedAtUtc": "{{captureTimestamp.UtcDateTime:O}}"
            }
            """;
        await File.WriteAllTextAsync(rawAssetPath, capturePayload, cancellationToken);

        var shot = new Shot(
            shotId,
            shotIndex,
            captureTimestamp,
            rawAssetPath,
            metadata: null,
            request.AiPickScore);

        await _shotRepository.SaveAsync(request.SessionId, shot, cancellationToken);
        return shot;
    }

    public Task<IReadOnlyList<Shot>> ListShotsAsync(string sessionId, CancellationToken cancellationToken)
    {
        return _shotRepository.ListBySessionAsync(sessionId, cancellationToken);
    }
}
