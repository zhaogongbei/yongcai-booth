using Booth.Runtime.Licensing;
using System.Security.Cryptography;
using System.Text.Json;

if (args.Length < 3)
{
    Console.WriteLine("Usage: LicenseGenerator <private-key.pem> <device-fingerprint> <expires-utc> [license-id]");
    Console.WriteLine("Example: LicenseGenerator private.pem abc123... 2099-12-31T23:59:59Z LIC-20260707-001");
    return 1;
}

var privateKeyPem = File.ReadAllText(args[0]);
var licenseId = args.Length >= 4
    ? args[3]
    : $"LIC-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}";

var payload = new LicensePayload(
    Version: 1,
    Product: LicenseService.ProductName,
    LicenseId: licenseId,
    DeviceFingerprint: args[1].Trim().ToLowerInvariant(),
    ExpiresAtUtc: DateTimeOffset.Parse(args[2]).ToUniversalTime(),
    Features: new[] { "export", "print", "share" });

var payloadBytes = JsonSerializer.SerializeToUtf8Bytes(payload);
using var rsa = RSA.Create();
rsa.ImportFromPem(privateKeyPem);

var signature = rsa.SignData(
    payloadBytes,
    HashAlgorithmName.SHA256,
    RSASignaturePadding.Pkcs1);

var envelope = new SignedLicenseEnvelope(
    Convert.ToBase64String(payloadBytes),
    Convert.ToBase64String(signature));

var envelopeBytes = JsonSerializer.SerializeToUtf8Bytes(envelope);
Console.WriteLine(ActivationCodeCodec.Encode(envelopeBytes));
return 0;
