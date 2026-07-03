namespace Booth.Domain.Session.DomainEvents;

/// <summary>
/// Domain event raised when a photo booth session completes successfully.
/// </summary>
/// <param name="EventId">Unique identifier for this event occurrence.</param>
/// <param name="SessionId">The ID of the session that completed.</param>
/// <param name="ShotCount">Total number of shots captured in the session.</param>
/// <param name="StartedAtUtc">When the session started (UTC).</param>
/// <param name="CompletedAtUtc">When the session completed (UTC).</param>
/// <param name="OccurredAtUtc">Timestamp when this event occurred (UTC).</param>
public sealed record SessionCompletedEvent(
    string EventId,
    string SessionId,
    int ShotCount,
    DateTimeOffset StartedAtUtc,
    DateTimeOffset CompletedAtUtc,
    DateTimeOffset OccurredAtUtc) : IDomainEvent;
