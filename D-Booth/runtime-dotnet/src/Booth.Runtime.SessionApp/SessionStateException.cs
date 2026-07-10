namespace Booth.Runtime.SessionApp;

public sealed class SessionStateException : Exception
{
    public SessionStateException(string errorCode, string message)
        : base(message)
    {
        ErrorCode = errorCode;
    }

    public string ErrorCode { get; }
}
