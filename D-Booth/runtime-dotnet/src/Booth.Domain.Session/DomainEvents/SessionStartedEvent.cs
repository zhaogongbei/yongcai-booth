namespace Booth.Domain.Session.DomainEvents;

/// <summary>
/// Domain event raised when a photo booth session begins.
/// </summary>
/// <param name="EventId">Unique identifier for this event occurrence.</param>
/// <param name="SessionId">The ID of the session that started.</param>
/// <param name="EventContextId">The event context this session belongs to.</param>
/// <param name="Mode">The capture mode for this session.</param>
/// <param name="DeviceId">The device executing the session.</param>
/// <param name="OccurredAtUtc">Timestamp when the session started (UTC).</param>
public sealed record SessionStartedEvent(
    string EventId,
    string SessionId,
    string EventContextId,
    string Mode,
    string DeviceId,
    DateTimeOffset OccurredAtUtc) : IDomainEvent;
