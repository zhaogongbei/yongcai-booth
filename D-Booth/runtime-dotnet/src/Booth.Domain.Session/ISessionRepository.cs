namespace Booth.Domain.Session;

public interface ISessionRepository
{
    Task SaveAsync(SessionAggregate session, CancellationToken cancellationToken);
    Task<SessionAggregate?> GetAsync(string sessionId, CancellationToken cancellationToken);
}
