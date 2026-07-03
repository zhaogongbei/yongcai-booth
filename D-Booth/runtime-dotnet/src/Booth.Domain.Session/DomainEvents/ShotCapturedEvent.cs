namespace Booth.Domain.Session.DomainEvents;

/// <summary>
/// Domain event raised when a photo is captured during a session.
/// </summary>
/// <param name="EventId">Unique identifier for this event occurrence.</param>
/// <param name="SessionId">The ID of the session this shot belongs to.</param>
/// <param name="ShotId">The unique identifier for the captured shot.</param>
/// <param name="ShotIndex">The zero-based index of this shot in the session.</param>
/// <param name="CapturedAtUtc">Timestamp when the shot was captured (UTC).</param>
/// <param name="RawAssetPath">File path to the raw captured asset.</param>
/// <param name="OccurredAtUtc">Timestamp when this event occurred (UTC).</param>
public sealed record ShotCapturedEvent(
    string EventId,
    string SessionId,
    string ShotId,
    int ShotIndex,
    DateTimeOffset CapturedAtUtc,
    string? RawAssetPath,
    DateTimeOffset OccurredAtUtc) : IDomainEvent;
