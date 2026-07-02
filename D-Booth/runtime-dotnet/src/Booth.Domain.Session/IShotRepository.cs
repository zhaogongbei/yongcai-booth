namespace Booth.Domain.Session;

public interface IShotRepository
{
    Task<int> GetNextShotIndexAsync(string sessionId, CancellationToken cancellationToken);
    Task SaveAsync(string sessionId, Shot shot, CancellationToken cancellationToken);
    Task<IReadOnlyList<Shot>> ListBySessionAsync(string sessionId, CancellationToken cancellationToken);
}
