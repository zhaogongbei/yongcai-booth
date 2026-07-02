namespace Booth.Domain.Session;

public enum SessionStatus
{
    Ready,
    Countdown,
    Capturing,
    Rendering,
    Printing,
    Sharing,
    Completed,
    Failed,
    Cancelled
}
