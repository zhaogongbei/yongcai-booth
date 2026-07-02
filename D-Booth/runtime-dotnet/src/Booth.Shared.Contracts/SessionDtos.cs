namespace Booth.Shared.Contracts;

public sealed record SessionStartApiRequest(
    string SessionId,
    string EventId,
    SessionMode Mode,
    string DeviceId);

public sealed record SessionStartApiResponse(
    string SessionId,
    string Status,
    string NextAction);

public sealed record SessionCancelApiResponse(
    string SessionId,
    string Status);

public sealed record SessionDetailsApiResponse(
    string SessionId,
    string EventId,
    string Mode,
    string Status,
    string DeviceId,
    string StartedAtUtc,
    string? CompletedAtUtc,
    int RetryCount,
    IReadOnlyList<ShotDetailsApiResponse> Shots,
    IReadOnlyList<JobDetailsApiResponse> Jobs,
    IReadOnlyList<OutputAssetApiResponse> Assets);

public sealed record HealthCheckResponse(
    string Status,
    string RuntimeVersion);
