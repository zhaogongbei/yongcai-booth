namespace Booth.Runtime.SessionApp;

public sealed class CaptureShotException : Exception
{
    public CaptureShotException(string errorCode, string message, Exception? innerException = null)
        : base(message, innerException)
    {
        ErrorCode = errorCode;
    }

    public string ErrorCode { get; }
}
