using Booth.Shared.Contracts;

namespace Booth.Domain.Session;

public sealed class SessionAggregate
{
    private readonly List<Shot> _shots = new();

    public SessionAggregate(string id, string eventId, SessionMode mode, string deviceId)
    {
        Id = id;
        EventId = eventId;
        Mode = mode;
        DeviceId = deviceId;
        Status = SessionStatus.Ready;
        StartedAtUtc = DateTimeOffset.UtcNow;
    }

    public string Id { get; }
    public string EventId { get; }
    public SessionMode Mode { get; }
    public string DeviceId { get; }
    public SessionStatus Status { get; private set; }
    public DateTimeOffset StartedAtUtc { get; }
    public DateTimeOffset? CompletedAtUtc { get; private set; }
    public IReadOnlyList<Shot> Shots => _shots;

    public void BeginCountdown() => Status = SessionStatus.Countdown;

    public void BeginCapture() => Status = SessionStatus.Capturing;

    public void AddShot(Shot shot) => _shots.Add(shot);

    public void BeginRendering() => Status = SessionStatus.Rendering;

    public void Complete()
    {
        Status = SessionStatus.Completed;
        CompletedAtUtc = DateTimeOffset.UtcNow;
    }

    public void Fail()
    {
        Status = SessionStatus.Failed;
        CompletedAtUtc = DateTimeOffset.UtcNow;
    }

    public void Cancel()
    {
        Status = SessionStatus.Cancelled;
        CompletedAtUtc = DateTimeOffset.UtcNow;
    }
}
