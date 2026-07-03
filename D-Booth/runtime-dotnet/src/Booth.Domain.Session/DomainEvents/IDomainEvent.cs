namespace Booth.Domain.Session.DomainEvents;

/// <summary>
/// Base interface for all domain events.
/// Domain events represent important business occurrences that have already happened.
/// </summary>
public interface IDomainEvent
{
    /// <summary>
    /// Gets the unique identifier of the event.
    /// </summary>
    string EventId { get; }

    /// <summary>
    /// Gets the timestamp when the event occurred (UTC).
    /// </summary>
    DateTimeOffset OccurredAtUtc { get; }
}
