namespace Booth.Domain.Session;

/// <summary>
/// Repository interface for session aggregate persistence.
/// </summary>
public interface ISessionRepository
{
    /// <summary>
    /// Atomically inserts a new session without replacing an existing identity.
    /// </summary>
    /// <param name="session">The new session to persist.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>True when inserted; false when the session ID already exists.</returns>
    Task<bool> TryAddAsync(SessionAggregate session, CancellationToken cancellationToken);

    /// <summary>
    /// Saves or updates a session aggregate.
    /// </summary>
    /// <param name="session">The session to persist.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    Task SaveAsync(SessionAggregate session, CancellationToken cancellationToken);

    /// <summary>
    /// Retrieves a session by its unique identifier.
    /// </summary>
    /// <param name="sessionId">The session ID to retrieve.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The session aggregate, or null if not found.</returns>
    Task<SessionAggregate?> GetAsync(string sessionId, CancellationToken cancellationToken);

    /// <summary>
    /// Retrieves multiple sessions by their IDs.
    /// </summary>
    /// <param name="sessionIds">Collection of session IDs to retrieve.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>List of found sessions (may be fewer than requested if some don't exist).</returns>
    Task<IReadOnlyList<SessionAggregate>> GetManyAsync(IEnumerable<string> sessionIds, CancellationToken cancellationToken);

    /// <summary>
    /// Retrieves all sessions for a specific event.
    /// </summary>
    /// <param name="eventId">The event ID to filter by.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>List of sessions belonging to the event.</returns>
    Task<IReadOnlyList<SessionAggregate>> GetByEventAsync(string eventId, CancellationToken cancellationToken);

    /// <summary>
    /// Saves multiple sessions in a batch operation.
    /// </summary>
    /// <param name="sessions">Collection of sessions to save.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    Task SaveManyAsync(IEnumerable<SessionAggregate> sessions, CancellationToken cancellationToken);
}
