namespace Booth.Runtime.JobApp;

public sealed class JobExecutionException : Exception
{
    public JobExecutionException(string errorCode, string message)
        : base(message)
    {
        ErrorCode = errorCode;
    }

    public string ErrorCode { get; }
}
