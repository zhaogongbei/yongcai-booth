namespace Booth.Shared.Contracts;

public enum JobType
{
    Print,
    Share,
    Sync,
    Export
}

public sealed record PrintJobPayload(
    int Copies,
    string? PrinterProfileId);

public sealed record PrintJobApiRequest(
    string SessionId,
    int Copies,
    string? PrinterProfileId);

public sealed record ShareChannelDto(
    string Type,
    string Recipient);

public sealed record ShareJobPayload(
    string ChannelType,
    string Recipient,
    string? ConsentToken);

public sealed record ShareJobApiRequest(
    string SessionId,
    IReadOnlyList<ShareChannelDto> Channels,
    string? ConsentToken);

public sealed record JobQueuedApiResponse(
    string JobId,
    string JobType,
    string Status);

public sealed record ShareJobsQueuedApiResponse(
    IReadOnlyList<string> JobIds,
    string Status);

public sealed record JobDetailsApiResponse(
    string JobId,
    string JobType,
    string AggregateId,
    string Status,
    int Priority,
    int AttemptCount,
    string ScheduledAtUtc,
    string? PayloadJson,
    string? CreatedAssetId,
    string? LastErrorCode,
    string? LastErrorMessage);
