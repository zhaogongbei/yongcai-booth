namespace Booth.Domain.Session.DomainEvents;

/// <summary>
/// Domain event raised when a session fails.
/// </summary>
/// <param name="EventId">Unique identifier for this event occurrence.</param>
/// <param name="SessionId">The ID of the session that failed.</param>
/// <param name="Reason">Human-readable reason for the failure.</param>
/// <param name="FailedAtUtc">When the session failed (UTC).</param>
/// <param name="OccurredAtUtc">Timestamp when this event occurred (UTC).</param>
public sealed record SessionFailedEvent(
    string EventId,
    string SessionId,
    string Reason,
    DateTimeOffset FailedAtUtc,
    DateTimeOffset OccurredAtUtc) : IDomainEvent;
