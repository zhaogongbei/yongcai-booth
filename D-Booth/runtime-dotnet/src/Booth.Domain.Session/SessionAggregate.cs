using Booth.Domain.Session.DomainEvents;
using Booth.Shared.Contracts;

namespace Booth.Domain.Session;

/// <summary>
/// Aggregate root representing a photo booth session.
/// Encapsulates the complete lifecycle from start to completion,
/// including all captured shots and state transitions.
/// </summary>
public sealed class SessionAggregate
{
    private readonly List<Shot> _shots = [];
    private readonly List<IDomainEvent> _domainEvents = [];

    /// <summary>
    /// Maximum number of retry attempts allowed before a session is considered failed.
    /// </summary>
    public const int MaxRetryCount = 3;

    /// <summary>
    /// Creates a new session in Ready status.
    /// </summary>
    /// <param name="id">Unique identifier for the session.</param>
    /// <param name="eventId">The event context this session belongs to.</param>
    /// <param name="mode">The capture mode for this session.</param>
    /// <param name="deviceId">The device executing the session.</param>
    /// <exception cref="ArgumentException">Thrown when any ID is empty.</exception>
    public SessionAggregate(string id, string eventId, SessionMode mode, string deviceId)
        : this(id, eventId, mode, deviceId, SessionStatus.Ready, DateTimeOffset.UtcNow, null, 0)
    {
        ValidateIds(id, eventId, deviceId);

        RaiseDomainEvent(new SessionStartedEvent(
            Guid.NewGuid().ToString("N"),
            id,
            eventId,
            mode.ToString(),
            deviceId,
            StartedAtUtc));
    }

    private SessionAggregate(
        string id,
        string eventId,
        SessionMode mode,
        string deviceId,
        SessionStatus status,
        DateTimeOffset startedAtUtc,
        DateTimeOffset? completedAtUtc,
        int retryCount)
    {
        Id = id;
        EventId = eventId;
        Mode = mode;
        DeviceId = deviceId;
        Status = status;
        StartedAtUtc = startedAtUtc;
        CompletedAtUtc = completedAtUtc;
        RetryCount = retryCount;
    }

    /// <summary>
    /// Gets the unique identifier for this session.
    /// </summary>
    public string Id { get; }

    /// <summary>
    /// Gets the event context identifier this session belongs to.
    /// </summary>
    public string EventId { get; }

    /// <summary>
    /// Gets the capture mode for this session (e.g., Print, GIF, Video).
    /// </summary>
    public SessionMode Mode { get; }

    /// <summary>
    /// Gets the device identifier executing this session.
    /// </summary>
    public string DeviceId { get; }

    /// <summary>
    /// Gets the current status of the session.
    /// </summary>
    public SessionStatus Status { get; private set; }

    /// <summary>
    /// Gets the timestamp when the session was started (UTC).
    /// </summary>
    public DateTimeOffset StartedAtUtc { get; }

    /// <summary>
    /// Gets the timestamp when the session was completed, failed, or cancelled (UTC).
    /// Null if the session is still in progress.
    /// </summary>
    public DateTimeOffset? CompletedAtUtc { get; private set; }

    /// <summary>
    /// Gets the number of retry attempts for this session.
    /// </summary>
    public int RetryCount { get; private set; }

    /// <summary>
    /// Gets the read-only collection of captured shots.
    /// </summary>
    public IReadOnlyList<Shot> Shots => _shots.AsReadOnly();

    /// <summary>
    /// Gets the read-only collection of domain events raised by this aggregate.
    /// </summary>
    public IReadOnlyList<IDomainEvent> DomainEvents => _domainEvents.AsReadOnly();

    /// <summary>
    /// Checks if the session is in a terminal state (completed, failed, or cancelled).
    /// </summary>
    public bool IsTerminal => Status is SessionStatus.Completed or SessionStatus.Failed or SessionStatus.Cancelled;

    /// <summary>
    /// Gets the duration of the session, if completed.
    /// </summary>
    public TimeSpan? Duration => CompletedAtUtc.HasValue
        ? CompletedAtUtc.Value - StartedAtUtc
        : null;

    /// <summary>
    /// Rehydrates a session aggregate from persistence.
    /// Used by repositories to reconstruct domain objects.
    /// </summary>
    public static SessionAggregate Rehydrate(
        string id,
        string eventId,
        SessionMode mode,
        string deviceId,
        SessionStatus status,
        DateTimeOffset startedAtUtc,
        DateTimeOffset? completedAtUtc,
        int retryCount)
    {
        return new SessionAggregate(id, eventId, mode, deviceId, status, startedAtUtc, completedAtUtc, retryCount);
    }

    /// <summary>
    /// Transitions the session to countdown status.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when transition is not allowed from current status.</exception>
    public void BeginCountdown()
    {
        EnsureNotTerminal();
        EnsureStatusIs(SessionStatus.Ready);
        Status = SessionStatus.Countdown;
    }

    /// <summary>
    /// Transitions the session to capturing status.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when transition is not allowed from current status.</exception>
    public void BeginCapture()
    {
        EnsureNotTerminal();
        EnsureStatusIs(SessionStatus.Countdown);
        Status = SessionStatus.Capturing;
    }

    /// <summary>
    /// Adds a captured shot to the session and raises a domain event.
    /// </summary>
    /// <param name="shot">The shot to add.</param>
    /// <exception cref="ArgumentNullException">Thrown when shot is null.</exception>
    /// <exception cref="InvalidOperationException">Thrown when session is not in Capturing status.</exception>
    public void AddShot(Shot shot)
    {
        ArgumentNullException.ThrowIfNull(shot);
        EnsureNotTerminal();
        EnsureStatusIs(SessionStatus.Capturing);

        _shots.Add(shot);

        RaiseDomainEvent(new ShotCapturedEvent(
            Guid.NewGuid().ToString("N"),
            Id,
            shot.Id,
            shot.Index,
            shot.CapturedAtUtc,
            shot.RawAssetPath,
            DateTimeOffset.UtcNow));
    }

    /// <summary>
    /// Transitions the session to rendering status.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when transition is not allowed or no shots captured.</exception>
    public void BeginRendering()
    {
        EnsureNotTerminal();
        EnsureStatusIs(SessionStatus.Capturing);

        if (_shots.Count == 0)
            throw new InvalidOperationException("Cannot begin rendering without any captured shots.");

        Status = SessionStatus.Rendering;
    }

    /// <summary>
    /// Transitions the session to printing status.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when transition is not allowed.</exception>
    public void BeginPrinting()
    {
        EnsureNotTerminal();
        EnsureStatusIs(SessionStatus.Rendering);
        Status = SessionStatus.Printing;
    }

    /// <summary>
    /// Transitions the session to sharing status.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when transition is not allowed.</exception>
    public void BeginSharing()
    {
        EnsureNotTerminal();
        Status = SessionStatus.Sharing;
    }

    /// <summary>
    /// Increments the retry counter for this session.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when max retries exceeded.</exception>
    public void IncrementRetryCount()
    {
        if (RetryCount >= MaxRetryCount)
            throw new InvalidOperationException($"Maximum retry count ({MaxRetryCount}) exceeded.");

        RetryCount++;
    }

    /// <summary>
    /// Marks the session as completed successfully and raises a domain event.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when session is already terminal.</exception>
    public void Complete()
    {
        EnsureNotTerminal();

        Status = SessionStatus.Completed;
        CompletedAtUtc = DateTimeOffset.UtcNow;

        RaiseDomainEvent(new SessionCompletedEvent(
            Guid.NewGuid().ToString("N"),
            Id,
            _shots.Count,
            StartedAtUtc,
            CompletedAtUtc.Value,
            DateTimeOffset.UtcNow));
    }

    /// <summary>
    /// Marks the session as failed and raises a domain event.
    /// </summary>
    /// <param name="reason">Human-readable reason for the failure.</param>
    /// <exception cref="ArgumentException">Thrown when reason is empty.</exception>
    /// <exception cref="InvalidOperationException">Thrown when session is already terminal.</exception>
    public void Fail(string reason = "Unspecified error")
    {
        if (string.IsNullOrWhiteSpace(reason))
            throw new ArgumentException("Failure reason cannot be empty.", nameof(reason));

        EnsureNotTerminal();

        Status = SessionStatus.Failed;
        CompletedAtUtc = DateTimeOffset.UtcNow;

        RaiseDomainEvent(new SessionFailedEvent(
            Guid.NewGuid().ToString("N"),
            Id,
            reason,
            CompletedAtUtc.Value,
            DateTimeOffset.UtcNow));
    }

    /// <summary>
    /// Marks the session as cancelled by the user.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when session is already terminal.</exception>
    public void Cancel()
    {
        EnsureNotTerminal();

        Status = SessionStatus.Cancelled;
        CompletedAtUtc = DateTimeOffset.UtcNow;
    }

    /// <summary>
    /// Clears all domain events. Typically called after events are published.
    /// </summary>
    public void ClearDomainEvents()
    {
        _domainEvents.Clear();
    }

    private void RaiseDomainEvent(IDomainEvent domainEvent)
    {
        _domainEvents.Add(domainEvent);
    }

    private void EnsureNotTerminal()
    {
        if (IsTerminal)
            throw new InvalidOperationException($"Cannot modify session in terminal status: {Status}.");
    }

    private void EnsureStatusIs(SessionStatus expectedStatus)
    {
        if (Status != expectedStatus)
            throw new InvalidOperationException($"Expected session status to be {expectedStatus}, but was {Status}.");
    }

    private static void ValidateIds(string id, string eventId, string deviceId)
    {
        if (string.IsNullOrWhiteSpace(id))
            throw new ArgumentException("Session ID cannot be empty.", nameof(id));

        if (string.IsNullOrWhiteSpace(eventId))
            throw new ArgumentException("Event ID cannot be empty.", nameof(eventId));

        if (string.IsNullOrWhiteSpace(deviceId))
            throw new ArgumentException("Device ID cannot be empty.", nameof(deviceId));
    }
}
