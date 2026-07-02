namespace Booth.Shared.Contracts;

public sealed record CaptureShotApiRequest(
    string? PreferredShotId,
    string? SourceLabel,
    double? AiPickScore);

public sealed record CaptureShotApiResponse(
    string SessionId,
    string ShotId,
    int ShotIndex,
    string RawAssetPath,
    string CapturedAtUtc);

public sealed record ShotDetailsApiResponse(
    string ShotId,
    string SessionId,
    int ShotIndex,
    string RawAssetPath,
    string CapturedAtUtc,
    double? AiPickScore);
