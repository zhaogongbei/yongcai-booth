namespace Booth.Shared.Contracts;

public static class ErrorCodes
{
    public const string CameraDeviceNotReady = "CAM_DEVICE_NOT_READY";
    public const string PrintQueueUnavailable = "PRN_QUEUE_UNAVAILABLE";
    public const string ShareChannelRejected = "SHR_CHANNEL_REJECTED";
    public const string SyncUnavailable = "SYN_UNAVAILABLE";
    public const string AiModelUnavailable = "AI_MODEL_UNAVAILABLE";
    public const string ConfigurationInvalid = "CFG_INVALID";
    public const string SessionNotFound = "SES_NOT_FOUND";
    public const string SessionConflict = "SES_CONFLICT";
    public const string SessionInvalidState = "SES_INVALID_STATE";
    public const string ShotConflict = "SHT_CONFLICT";
    public const string JobNotFound = "JOB_NOT_FOUND";
    public const string SecurityDenied = "SEC_DENIED";
}
