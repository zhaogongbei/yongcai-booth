namespace Booth.Runtime.SessionApp;

public sealed record CaptureShotRequest(
    string SessionId,
    string? PreferredShotId,
    string? SourceLabel,
    double? AiPickScore);
