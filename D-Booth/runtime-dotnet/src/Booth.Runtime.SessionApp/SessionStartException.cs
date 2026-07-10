namespace Booth.Runtime.SessionApp;

public sealed class SessionStartException : Exception
{
    public SessionStartException(string errorCode, string message)
        : base(message)
    {
        ErrorCode = errorCode;
    }

    public string ErrorCode { get; }
}
