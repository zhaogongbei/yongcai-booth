using Microsoft.Win32;
using System.Net.NetworkInformation;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Booth.Runtime.Licensing;

public interface ILicenseHashStore
{
    void SaveHash(string hash);
    string? ReadHash();
}

public sealed class FileLicenseHashStore : ILicenseHashStore
{
    private readonly string _path;

    public FileLicenseHashStore(string path)
    {
        _path = path;
    }

    public void SaveHash(string hash)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
        File.WriteAllText(_path, hash, Encoding.UTF8);
    }

    public string? ReadHash()
    {
        return File.Exists(_path) ? File.ReadAllText(_path, Encoding.UTF8).Trim() : null;
    }
}

public sealed class RegistryLicenseHashStore : ILicenseHashStore
{
    private readonly string _fallbackPath;

    public RegistryLicenseHashStore(string fallbackPath)
    {
        _fallbackPath = fallbackPath;
    }

    public void SaveHash(string hash)
    {
        try
        {
            using var key = Registry.LocalMachine.CreateSubKey(@"Software\D-Booth");
            key?.SetValue("LicenseHash", hash, RegistryValueKind.String);
            return;
        }
        catch
        {
            new FileLicenseHashStore(_fallbackPath).SaveHash(hash);
        }
    }

    public string? ReadHash()
    {
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(@"Software\D-Booth");
            var stored = key?.GetValue("LicenseHash") as string;
            if (!string.IsNullOrWhiteSpace(stored))
            {
                return stored;
            }
        }
        catch
        {
        }

        return new FileLicenseHashStore(_fallbackPath).ReadHash();
    }
}

public interface ILocalLicenseProtector
{
    byte[] Protect(byte[] plain);
    byte[] Unprotect(byte[] protectedBytes);
}

public sealed class DpapiLocalLicenseProtector : ILocalLicenseProtector
{
    private static readonly byte[] Entropy =
        SHA256.HashData(Encoding.UTF8.GetBytes("D-Booth.LocalLicense.v1"));

    public byte[] Protect(byte[] plain)
    {
        return ProtectedData.Protect(plain, Entropy, DataProtectionScope.LocalMachine);
    }

    public byte[] Unprotect(byte[] protectedBytes)
    {
        return ProtectedData.Unprotect(protectedBytes, Entropy, DataProtectionScope.LocalMachine);
    }
}

public sealed class LicenseService
{
    public const string ProductName = "D-Booth";

    private readonly string _licensePath;
    private readonly string _publicKeyPem;
    private readonly Func<string> _fingerprintProvider;
    private readonly ILicenseHashStore _registryHashStore;
    private readonly ILocalLicenseProtector _protector;

    public LicenseService(
        string licenseDirectory,
        string publicKeyPem,
        Func<string>? fingerprintProvider = null,
        ILicenseHashStore? registryHashStore = null,
        ILocalLicenseProtector? protector = null)
    {
        _licensePath = Path.Combine(licenseDirectory, "license.bin");
        _publicKeyPem = publicKeyPem;
        _fingerprintProvider = fingerprintProvider ?? HardwareFingerprint.Get;
        _registryHashStore = registryHashStore
            ?? new RegistryLicenseHashStore(Path.Combine(licenseDirectory, "license.hash"));
        _protector = protector ?? new DpapiLocalLicenseProtector();
    }

    public LicenseStatusResponse GetStatus()
    {
        var fingerprint = NormalizeFingerprint(_fingerprintProvider());
        if (!File.Exists(_licensePath))
        {
            return new(false, null, null, fingerprint, "not_activated");
        }

        try
        {
            var protectedBytes = File.ReadAllBytes(_licensePath);
            if (!RegistryHashMatches(protectedBytes))
            {
                return new(false, null, null, fingerprint, "license_tampered");
            }

            var plain = _protector.Unprotect(protectedBytes);
            var local = JsonSerializer.Deserialize<LocalLicense>(plain)
                ?? throw new CryptographicException("Invalid local license.");

            var payload = VerifyActivationCode(local.ActivationCode);
            return ValidatePayload(payload, fingerprint);
        }
        catch
        {
            return new(false, null, null, fingerprint, "license_invalid");
        }
    }

    public LicenseStatusResponse Activate(string activationCode)
    {
        var fingerprint = NormalizeFingerprint(_fingerprintProvider());

        try
        {
            var payload = VerifyActivationCode(activationCode);
            var validation = ValidatePayload(payload, fingerprint);
            if (!validation.IsActivated)
            {
                return validation;
            }

            Directory.CreateDirectory(Path.GetDirectoryName(_licensePath)!);
            TryMarkDirectoryHidden(Path.GetDirectoryName(_licensePath)!);

            var local = JsonSerializer.SerializeToUtf8Bytes(new LocalLicense(
                NormalizeActivationCode(activationCode),
                DateTimeOffset.UtcNow));

            var protectedBytes = _protector.Protect(local);
            File.WriteAllBytes(_licensePath, protectedBytes);
            SaveRegistryHash(protectedBytes);

            return validation;
        }
        catch
        {
            return new(false, null, null, fingerprint, "invalid_code");
        }
    }

    private LicenseStatusResponse ValidatePayload(LicensePayload payload, string fingerprint)
    {
        if (payload.Version != 1)
        {
            return new(false, null, null, fingerprint, "version_unsupported");
        }

        if (!StringComparer.Ordinal.Equals(payload.Product, ProductName))
        {
            return new(false, null, null, fingerprint, "product_mismatch");
        }

        if (!FixedTimeEquals(payload.DeviceFingerprint, fingerprint))
        {
            return new(false, null, null, fingerprint, "device_mismatch");
        }

        if (payload.ExpiresAtUtc <= DateTimeOffset.UtcNow)
        {
            return new(false, payload.LicenseId, payload.ExpiresAtUtc.ToString("O"), fingerprint, "expired");
        }

        return new(true, payload.LicenseId, payload.ExpiresAtUtc.ToString("O"), fingerprint, null);
    }

    private LicensePayload VerifyActivationCode(string code)
    {
        if (string.IsNullOrWhiteSpace(_publicKeyPem))
        {
            throw new CryptographicException("License public key is not configured.");
        }

        var envelopeBytes = ActivationCodeCodec.Decode(code);
        var envelope = JsonSerializer.Deserialize<SignedLicenseEnvelope>(envelopeBytes)
            ?? throw new CryptographicException("Invalid license envelope.");

        var payloadBytes = Convert.FromBase64String(envelope.PayloadBase64);
        var signature = Convert.FromBase64String(envelope.SignatureBase64);

        using var rsa = RSA.Create();
        rsa.ImportFromPem(_publicKeyPem);

        var ok = rsa.VerifyData(
            payloadBytes,
            signature,
            HashAlgorithmName.SHA256,
            RSASignaturePadding.Pkcs1);

        if (!ok)
        {
            throw new CryptographicException("Invalid license signature.");
        }

        return JsonSerializer.Deserialize<LicensePayload>(payloadBytes)
            ?? throw new CryptographicException("Invalid license payload.");
    }

    private void SaveRegistryHash(byte[] protectedBytes)
    {
        _registryHashStore.SaveHash(HashProtectedBytes(protectedBytes));
    }

    private bool RegistryHashMatches(byte[] protectedBytes)
    {
        var stored = _registryHashStore.ReadHash();
        var actual = HashProtectedBytes(protectedBytes);
        return StringComparer.OrdinalIgnoreCase.Equals(stored, actual);
    }

    private static string HashProtectedBytes(byte[] protectedBytes)
    {
        return Convert.ToHexString(SHA256.HashData(protectedBytes));
    }

    private static string NormalizeActivationCode(string code)
    {
        return string.Join("-", new string(code.Where(char.IsLetterOrDigit).ToArray())
            .ToUpperInvariant()
            .Chunk(5)
            .Select(c => new string(c)));
    }

    private static string NormalizeFingerprint(string fingerprint)
    {
        return fingerprint.Trim().ToLowerInvariant();
    }

    private static bool FixedTimeEquals(string left, string right)
    {
        var leftBytes = Encoding.UTF8.GetBytes(NormalizeFingerprint(left));
        var rightBytes = Encoding.UTF8.GetBytes(NormalizeFingerprint(right));
        return leftBytes.Length == rightBytes.Length
            && CryptographicOperations.FixedTimeEquals(leftBytes, rightBytes);
    }

    private static void TryMarkDirectoryHidden(string directory)
    {
        try
        {
            File.SetAttributes(directory, File.GetAttributes(directory) | FileAttributes.Hidden);
        }
        catch
        {
        }
    }
}

public static class HardwareFingerprint
{
    public static string Get()
    {
        var mac = NetworkInterface.GetAllNetworkInterfaces()
            .Where(n => n.OperationalStatus == OperationalStatus.Up)
            .Where(n => n.NetworkInterfaceType != NetworkInterfaceType.Loopback)
            .Select(n => n.GetPhysicalAddress().ToString())
            .Where(v => !string.IsNullOrWhiteSpace(v))
            .OrderBy(v => v, StringComparer.Ordinal)
            .FirstOrDefault() ?? "NO_MAC";

        var raw = $"machine={Normalize(Environment.MachineName)}|os={Normalize(Environment.OSVersion.VersionString)}|mac={Normalize(mac)}";
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw))).ToLowerInvariant();
    }

    private static string Normalize(string value)
    {
        return value.Trim().Replace(" ", "").ToUpperInvariant();
    }
}

