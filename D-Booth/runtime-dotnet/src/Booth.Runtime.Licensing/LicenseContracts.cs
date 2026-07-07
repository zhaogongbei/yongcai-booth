namespace Booth.Runtime.Licensing;

public sealed record ActivateLicenseRequest(string Code);

public sealed record LicenseStatusResponse(
    bool IsActivated,
    string? LicenseId,
    string? ExpiresAtUtc,
    string DeviceFingerprint,
    string? Error);

public sealed record LocalLicense(string ActivationCode, DateTimeOffset ActivatedAtUtc);

public sealed record SignedLicenseEnvelope(string PayloadBase64, string SignatureBase64);

public sealed record LicensePayload(
    int Version,
    string Product,
    string LicenseId,
    string DeviceFingerprint,
    DateTimeOffset ExpiresAtUtc,
    string[] Features);

