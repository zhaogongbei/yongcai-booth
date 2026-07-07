using Booth.Runtime.Licensing;
using System.Security.Cryptography;
using System.Text.Json;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class LicenseServiceTests
{
    [Fact]
    public void ActivationCodeCodec_ShouldRoundTripBytes()
    {
        var bytes = new byte[] { 0, 1, 2, 3, 4, 250, 255 };

        var code = ActivationCodeCodec.Encode(bytes);
        var decoded = ActivationCodeCodec.Decode(code);

        Assert.Equal(bytes, decoded);
        Assert.Contains("-", code);
    }

    [Fact]
    public void Activate_ShouldPersistLicense_WhenSignatureAndDeviceMatch()
    {
        using var rsa = RSA.Create(2048);
        var tempRoot = CreateTempRoot();
        var fingerprint = "abc123";
        var code = CreateActivationCode(rsa, fingerprint, DateTimeOffset.UtcNow.AddDays(30));
        var service = CreateService(tempRoot, rsa, fingerprint);

        var result = service.Activate(code);
        var status = service.GetStatus();

        Assert.True(result.IsActivated);
        Assert.True(status.IsActivated);
        Assert.Equal("LIC-TEST", status.LicenseId);
        Assert.Null(status.Error);
    }

    [Fact]
    public void Activate_ShouldReject_WhenDeviceDoesNotMatch()
    {
        using var rsa = RSA.Create(2048);
        var tempRoot = CreateTempRoot();
        var code = CreateActivationCode(rsa, "device-a", DateTimeOffset.UtcNow.AddDays(30));
        var service = CreateService(tempRoot, rsa, "device-b");

        var result = service.Activate(code);

        Assert.False(result.IsActivated);
        Assert.Equal("device_mismatch", result.Error);
    }

    [Fact]
    public void Activate_ShouldReject_WhenLicenseExpired()
    {
        using var rsa = RSA.Create(2048);
        var tempRoot = CreateTempRoot();
        var fingerprint = "abc123";
        var code = CreateActivationCode(rsa, fingerprint, DateTimeOffset.UtcNow.AddDays(-1));
        var service = CreateService(tempRoot, rsa, fingerprint);

        var result = service.Activate(code);

        Assert.False(result.IsActivated);
        Assert.Equal("expired", result.Error);
    }

    private static LicenseService CreateService(string tempRoot, RSA rsa, string fingerprint)
    {
        return new LicenseService(
            licenseDirectory: Path.Combine(tempRoot, ".license"),
            publicKeyPem: rsa.ExportSubjectPublicKeyInfoPem(),
            fingerprintProvider: () => fingerprint,
            registryHashStore: new FileLicenseHashStore(Path.Combine(tempRoot, "license.hash")));
    }

    private static string CreateActivationCode(RSA rsa, string fingerprint, DateTimeOffset expiresAtUtc)
    {
        var payload = new LicensePayload(
            Version: 1,
            Product: "D-Booth",
            LicenseId: "LIC-TEST",
            DeviceFingerprint: fingerprint,
            ExpiresAtUtc: expiresAtUtc,
            Features: new[] { "export", "print", "share" });

        var payloadBytes = JsonSerializer.SerializeToUtf8Bytes(payload);
        var signature = rsa.SignData(payloadBytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        var envelope = new SignedLicenseEnvelope(
            Convert.ToBase64String(payloadBytes),
            Convert.ToBase64String(signature));

        return ActivationCodeCodec.Encode(JsonSerializer.SerializeToUtf8Bytes(envelope));
    }

    private static string CreateTempRoot()
    {
        var path = Path.Combine(Path.GetTempPath(), $"booth-license-{Guid.NewGuid():N}");
        Directory.CreateDirectory(path);
        return path;
    }
}

