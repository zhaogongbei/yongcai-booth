using Booth.Domain.Session;

namespace Booth.Runtime.SessionApp;

public sealed class SessionApplicationService
{
    private readonly ISessionRepository _sessionRepository;

    public SessionApplicationService(ISessionRepository sessionRepository)
    {
        _sessionRepository = sessionRepository;
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
}
