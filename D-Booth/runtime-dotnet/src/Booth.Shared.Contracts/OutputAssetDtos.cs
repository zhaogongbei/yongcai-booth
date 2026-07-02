namespace Booth.Shared.Contracts;

public sealed record OutputAssetApiResponse(
    string AssetId,
    string SessionId,
    string AssetType,
    string StorageScope,
    string? LocalPath,
    string? RemoteUrl,
    string CreatedAtUtc);

public sealed record JobExecutionApiResponse(
    string JobId,
    string Status,
    string? CreatedAssetId);
