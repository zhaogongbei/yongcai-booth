namespace Booth.Shared.Contracts;

public enum JobStatus
{
    Queued,
    Running,
    Succeeded,
    Failed,
    DeadLetter
}
