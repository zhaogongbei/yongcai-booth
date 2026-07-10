namespace Booth.Domain.Session;

/// <summary>
/// Repository interface for shot entity persistence.
/// </summary>
public interface IShotRepository
{
    /// <summary>
    /// Checks whether a shot ID already exists in any session.
    /// </summary>
    /// <param name="shotId">The globally unique shot ID.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    Task<bool> ExistsAsync(string shotId, CancellationToken cancellationToken);

    /// <summary>
    /// Gets the next available shot index for a session.
    /// </summary>
    /// <param name="sessionId">The session ID.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The next index to use (one-based).</returns>
    Task<int> GetNextShotIndexAsync(string sessionId, CancellationToken cancellationToken);

    /// <summary>
    /// Atomically inserts a shot without replacing an existing shot identity.
    /// </summary>
    /// <param name="sessionId">The session this shot belongs to.</param>
    /// <param name="shot">The new shot to persist.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>True when inserted; false when the shot ID already exists.</returns>
    Task<bool> TryAddAsync(string sessionId, Shot shot, CancellationToken cancellationToken);

    /// <summary>
    /// Saves a shot for a specific session.
    /// </summary>
    /// <param name="sessionId">The session this shot belongs to.</param>
    /// <param name="shot">The shot to persist.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    Task SaveAsync(string sessionId, Shot shot, CancellationToken cancellationToken);

    /// <summary>
    /// Retrieves all shots for a specific session, ordered by index.
    /// </summary>
    /// <param name="sessionId">The session ID.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>List of shots for the session.</returns>
    Task<IReadOnlyList<Shot>> ListBySessionAsync(string sessionId, CancellationToken cancellationToken);

    /// <summary>
    /// Saves multiple shots in a batch operation.
    /// </summary>
    /// <param name="sessionId">The session ID these shots belong to.</param>
    /// <param name="shots">Collection of shots to save.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    Task SaveManyAsync(string sessionId, IEnumerable<Shot> shots, CancellationToken cancellationToken);

    /// <summary>
    /// Deletes all shots for a specific session.
    /// </summary>
    /// <param name="sessionId">The session ID.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    Task DeleteBySessionAsync(string sessionId, CancellationToken cancellationToken);
}
