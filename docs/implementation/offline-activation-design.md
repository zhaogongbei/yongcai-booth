# 桌面端离线激活码授权设计

## 关键结论

严格的 `XXXXX-XXXXX-XXXXX` 只有 15 个字母数字位，最多承载约 78 bit 信息；RSA-2048 签名本身就有 256 字节，编码后远大于 15 位。因此以下三项不能同时成立：

- 激活码只有 `XXXXX-XXXXX-XXXXX`
- 完全离线，无服务端查询
- RSA 私钥生成，客户端公钥校验，并包含设备指纹和有效期

可落地方案有两种：

- 推荐方案：离线 RSA 授权码使用固定 5 字符分组和 `-` 分隔，但允许多个分组，例如 `ABCDE-23456-...`。这是本文代码采用的方案。
- 严格短码方案：`XXXXX-XXXXX-XXXXX` 只能作为兑换码或授权编号，必须在线查询，或配套导入一个 RSA 签名的 `license.bin` 文件。

下面设计以当前仓库的 `.NET 8 Windows Runtime + React 前端` 为目标：授权校验放在 `D-Booth/runtime-dotnet`，React 只调用本机 API。

## 整体架构

```text
开发者生成器
  输入：设备指纹、有效期、授权范围
  私钥：RSA private key，只保存在开发者机器或后台
  输出：RSA 签名授权码，多段 5 字符分组

桌面客户端
  React 激活弹窗
    GET  /v1/license/status
    POST /v1/license/activate
  .NET Runtime
    读取硬件指纹
    用内置公钥验签授权码
    比对产品、设备指纹、有效期
    生成 DPAPI 加密 license.bin
    所有导出入口检查授权状态

本地存储
  %ProgramData%\D-Booth\.license\license.bin
  HKLM\Software\D-Booth\LicenseHash
```

## 授权数据结构

授权码不是“私钥加密、公钥解密”，而是“私钥签名、公钥验签”。签名更符合 RSA 授权场景，也避免错误地把公钥解密当成保密机制。

```json
{
  "version": 1,
  "product": "D-Booth",
  "licenseId": "LIC-20260707-001",
  "deviceFingerprint": "sha256 hex",
  "expiresAtUtc": "2099-12-31T23:59:59Z",
  "features": ["export", "print", "share"]
}
```

生成器对上面的 payload 字节做 RSA-SHA256 签名，然后把 `{ payload, signature }` 编码成 Base32，再按 5 位分组。

## 本地 API

```csharp
app.MapGet("/v1/license/status", (LicenseService license) =>
    Results.Ok(license.GetStatus()));

app.MapPost("/v1/license/activate", (ActivateLicenseRequest request, LicenseService license) =>
{
    var result = license.Activate(request.Code);
    return result.IsActivated
        ? Results.Ok(result)
        : Results.BadRequest(result);
});

public sealed record ActivateLicenseRequest(string Code);
public sealed record LicenseStatusResponse(
    bool IsActivated,
    string? LicenseId,
    string? ExpiresAtUtc,
    string DeviceFingerprint,
    string? Error);
```

## C# 客户端校验代码示例

依赖建议：

```xml
<PackageReference Include="System.Management" Version="9.0.0" />
```

`LicenseService.cs`：

```csharp
using System.Management;
using System.Net.NetworkInformation;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32;

public sealed class LicenseService
{
    private const string ProductName = "D-Booth";
    private const string PublicKeyPem = """
-----BEGIN PUBLIC KEY-----
替换为开发者生成的 RSA PUBLIC KEY
-----END PUBLIC KEY-----
""";

    private static readonly byte[] DpapiEntropy =
        SHA256.HashData(Encoding.UTF8.GetBytes("D-Booth.LocalLicense.v1"));

    private readonly string _licensePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
        "D-Booth",
        ".license",
        "license.bin");

    public LicenseStatusResponse GetStatus()
    {
        var fingerprint = HardwareFingerprint.Get();
        if (!File.Exists(_licensePath))
            return new(false, null, null, fingerprint, "not_activated");

        try
        {
            var protectedBytes = File.ReadAllBytes(_licensePath);
            var plain = ProtectedData.Unprotect(
                protectedBytes,
                DpapiEntropy,
                DataProtectionScope.LocalMachine);

            var local = JsonSerializer.Deserialize<LocalLicense>(plain)
                ?? throw new CryptographicException("Invalid local license.");

            var payload = VerifyActivationCode(local.ActivationCode);
            var now = DateTimeOffset.UtcNow;

            if (payload.Product != ProductName)
                return new(false, null, null, fingerprint, "product_mismatch");
            if (!CryptographicOperations.FixedTimeEquals(
                    Encoding.UTF8.GetBytes(payload.DeviceFingerprint),
                    Encoding.UTF8.GetBytes(fingerprint)))
                return new(false, null, null, fingerprint, "device_mismatch");
            if (payload.ExpiresAtUtc <= now)
                return new(false, payload.LicenseId, payload.ExpiresAtUtc.ToString("O"), fingerprint, "expired");

            if (!RegistryHashMatches(protectedBytes))
                return new(false, null, null, fingerprint, "license_tampered");

            return new(true, payload.LicenseId, payload.ExpiresAtUtc.ToString("O"), fingerprint, null);
        }
        catch
        {
            return new(false, null, null, fingerprint, "license_invalid");
        }
    }

    public LicenseStatusResponse Activate(string activationCode)
    {
        var fingerprint = HardwareFingerprint.Get();

        try
        {
            var payload = VerifyActivationCode(activationCode);
            if (payload.Product != ProductName)
                return new(false, null, null, fingerprint, "授权码不属于当前产品。");
            if (!StringComparer.Ordinal.Equals(payload.DeviceFingerprint, fingerprint))
                return new(false, null, null, fingerprint, "授权码不属于当前设备。");
            if (payload.ExpiresAtUtc <= DateTimeOffset.UtcNow)
                return new(false, payload.LicenseId, payload.ExpiresAtUtc.ToString("O"), fingerprint, "授权码已过期。");

            Directory.CreateDirectory(Path.GetDirectoryName(_licensePath)!);
            File.SetAttributes(Path.GetDirectoryName(_licensePath)!, FileAttributes.Hidden | FileAttributes.Directory);

            var local = JsonSerializer.SerializeToUtf8Bytes(new LocalLicense(
                activationCode.Trim().ToUpperInvariant(),
                DateTimeOffset.UtcNow));

            var protectedBytes = ProtectedData.Protect(
                local,
                DpapiEntropy,
                DataProtectionScope.LocalMachine);

            File.WriteAllBytes(_licensePath, protectedBytes);
            SaveRegistryHash(protectedBytes);

            return new(true, payload.LicenseId, payload.ExpiresAtUtc.ToString("O"), fingerprint, null);
        }
        catch
        {
            return new(false, null, null, fingerprint, "无效激活码。");
        }
    }

    private static LicensePayload VerifyActivationCode(string code)
    {
        var envelopeBytes = ActivationCodeCodec.Decode(code);
        var envelope = JsonSerializer.Deserialize<SignedLicenseEnvelope>(envelopeBytes)
            ?? throw new CryptographicException("Invalid envelope.");

        var payloadBytes = Convert.FromBase64String(envelope.PayloadBase64);
        var signature = Convert.FromBase64String(envelope.SignatureBase64);

        using var rsa = RSA.Create();
        rsa.ImportFromPem(PublicKeyPem);

        var ok = rsa.VerifyData(
            payloadBytes,
            signature,
            HashAlgorithmName.SHA256,
            RSASignaturePadding.Pkcs1);

        if (!ok)
            throw new CryptographicException("Invalid signature.");

        return JsonSerializer.Deserialize<LicensePayload>(payloadBytes)
            ?? throw new CryptographicException("Invalid payload.");
    }

    private static void SaveRegistryHash(byte[] protectedBytes)
    {
        using var key = Registry.LocalMachine.CreateSubKey(@"Software\D-Booth");
        key.SetValue("LicenseHash", Convert.ToHexString(SHA256.HashData(protectedBytes)), RegistryValueKind.String);
    }

    private static bool RegistryHashMatches(byte[] protectedBytes)
    {
        using var key = Registry.LocalMachine.OpenSubKey(@"Software\D-Booth");
        var stored = key?.GetValue("LicenseHash") as string;
        var actual = Convert.ToHexString(SHA256.HashData(protectedBytes));
        return StringComparer.OrdinalIgnoreCase.Equals(stored, actual);
    }
}

public sealed record LocalLicense(string ActivationCode, DateTimeOffset ActivatedAtUtc);

public sealed record SignedLicenseEnvelope(string PayloadBase64, string SignatureBase64);

public sealed record LicensePayload(
    int Version,
    string Product,
    string LicenseId,
    string DeviceFingerprint,
    DateTimeOffset ExpiresAtUtc,
    string[] Features);
```

`HardwareFingerprint.cs`：

```csharp
using System.Management;
using System.Net.NetworkInformation;
using System.Security.Cryptography;
using System.Text;

public static class HardwareFingerprint
{
    public static string Get()
    {
        var cpu = FirstWmiValue("Win32_Processor", "ProcessorId");
        var disk = FirstWmiValue("Win32_DiskDrive", "SerialNumber");
        var mac = NetworkInterface.GetAllNetworkInterfaces()
            .Where(n => n.OperationalStatus == OperationalStatus.Up)
            .Where(n => n.NetworkInterfaceType != NetworkInterfaceType.Loopback)
            .Select(n => n.GetPhysicalAddress().ToString())
            .Where(v => !string.IsNullOrWhiteSpace(v))
            .OrderBy(v => v, StringComparer.Ordinal)
            .FirstOrDefault() ?? "NO_MAC";

        var raw = $"cpu={Normalize(cpu)}|disk={Normalize(disk)}|mac={Normalize(mac)}";
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw))).ToLowerInvariant();
    }

    private static string FirstWmiValue(string cls, string prop)
    {
        try
        {
            using var searcher = new ManagementObjectSearcher($"SELECT {prop} FROM {cls}");
            foreach (ManagementObject item in searcher.Get())
                return item[prop]?.ToString() ?? "";
        }
        catch
        {
            return "";
        }

        return "";
    }

    private static string Normalize(string value) =>
        value.Trim().Replace(" ", "").ToUpperInvariant();
}
```

`ActivationCodeCodec.cs`：

```csharp
using System.Text;

public static class ActivationCodeCodec
{
    private const string Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    public static string Encode(byte[] bytes)
    {
        var output = new StringBuilder();
        var buffer = 0;
        var bitsLeft = 0;

        foreach (var b in bytes)
        {
            buffer = (buffer << 8) | b;
            bitsLeft += 8;
            while (bitsLeft >= 5)
            {
                output.Append(Alphabet[(buffer >> (bitsLeft - 5)) & 31]);
                bitsLeft -= 5;
            }
        }

        if (bitsLeft > 0)
            output.Append(Alphabet[(buffer << (5 - bitsLeft)) & 31]);

        return string.Join("-", output.ToString().Chunk(5).Select(c => new string(c)));
    }

    public static byte[] Decode(string code)
    {
        var clean = new string(code.Where(char.IsLetterOrDigit).ToArray()).ToUpperInvariant();
        var bytes = new List<byte>();
        var buffer = 0;
        var bitsLeft = 0;

        foreach (var ch in clean)
        {
            var value = Alphabet.IndexOf(ch);
            if (value < 0)
                throw new FormatException("Invalid activation code character.");

            buffer = (buffer << 5) | value;
            bitsLeft += 5;
            if (bitsLeft >= 8)
            {
                bytes.Add((byte)((buffer >> (bitsLeft - 8)) & 255));
                bitsLeft -= 8;
            }
        }

        return bytes.ToArray();
    }
}
```

## 开发者激活码生成器

`LicenseGenerator/Program.cs`：

```csharp
using System.Security.Cryptography;
using System.Text.Json;

if (args.Length < 3)
{
    Console.WriteLine("Usage: LicenseGenerator <private-key.pem> <device-fingerprint> <expires-utc>");
    Console.WriteLine("Example: LicenseGenerator private.pem abc123... 2099-12-31T23:59:59Z");
    return 1;
}

var privateKeyPem = File.ReadAllText(args[0]);
var payload = new LicensePayload(
    Version: 1,
    Product: "D-Booth",
    LicenseId: $"LIC-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}",
    DeviceFingerprint: args[1].Trim().ToLowerInvariant(),
    ExpiresAtUtc: DateTimeOffset.Parse(args[2]).ToUniversalTime(),
    Features: ["export", "print", "share"]);

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
```

密钥生成：

```powershell
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

私钥只能放在开发者后台或离线制码电脑；客户端只内置 `public.pem`。

## React 激活弹窗逻辑

启动时调用 `/v1/license/status`。未激活时显示不可关闭弹窗；如果业务允许未激活试用，可以保留“继续未激活模式”，否则只提供“激活”和“退出”。

```tsx
import { useEffect, useState } from "react";

type LicenseStatus = {
  isActivated: boolean;
  licenseId?: string;
  expiresAtUtc?: string;
  deviceFingerprint: string;
  error?: string;
};

export function ActivationGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/v1/license/status")
      .then((r) => r.json())
      .then(setStatus);
  }, []);

  async function activate() {
    setError(null);
    const response = await fetch("/v1/license/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const next = await response.json();
    if (!response.ok || !next.isActivated) {
      setError(next.error ?? "无效激活码");
      return;
    }
    setStatus(next);
  }

  if (!status) return null;
  if (status.isActivated) return <>{children}</>;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60">
      <div className="w-[520px] max-w-[calc(100vw-32px)] rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">激活 D-Booth</h2>
        <p className="mt-3 text-sm text-neutral-600">设备指纹</p>
        <code className="mt-1 block break-all rounded bg-neutral-100 p-2 text-xs">
          {status.deviceFingerprint}
        </code>
        <textarea
          className="mt-4 h-28 w-full rounded border p-3 font-mono text-sm"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="输入授权码，例如 XXXXX-XXXXX-XXXXX-..."
        />
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button className="rounded border px-4 py-2" onClick={() => window.close()}>
            退出
          </button>
          <button className="rounded bg-black px-4 py-2 text-white" onClick={activate}>
            激活
          </button>
        </div>
      </div>
    </div>
  );
}
```

## 未激活限制逻辑

导出、打印、分享等核心能力必须在后端再次校验，不能只靠前端禁用按钮。

```csharp
public sealed class ExportGuard
{
    private readonly LicenseService _license;

    public ExportGuard(LicenseService license)
    {
        _license = license;
    }

    public bool CanExportOriginal() => _license.GetStatus().IsActivated;

    public ExportMode GetExportMode()
    {
        return _license.GetStatus().IsActivated
            ? ExportMode.FullQuality
            : ExportMode.WatermarkedPreview;
    }
}

public enum ExportMode
{
    FullQuality,
    WatermarkedPreview
}
```

实现策略：

- 前端：未激活时隐藏或禁用高质量导出按钮，弹出激活弹窗。
- 后端：所有导出 API 都调用 `LicenseService.GetStatus()`。
- 未激活：禁止原图、高分辨率导出；如允许预览导出，必须强制调用 `WatermarkService` 加水印。
- 已激活：走原始导出链路。
- 启动：`ActivationGate` 强制覆盖主界面；运行时 API 仍需防绕过。

## 本地授权存储方案

文件路径：

```text
%ProgramData%\D-Booth\.license\license.bin
```

注册表：

```text
HKLM\Software\D-Booth\LicenseHash
```

存储内容：

- `license.bin`：`LocalLicense` JSON 经 Windows DPAPI `LocalMachine` 加密后的二进制。
- `LicenseHash`：加密后文件的 SHA-256，用于发现授权文件被替换。
- 授权文件内保存原始签名授权码，不保存私钥，不保存明文 payload。

安全边界：

- DPAPI 能防普通复制和明文篡改，但管理员仍能删除授权。
- 公钥验签能防伪造授权码。
- 设备指纹绑定能防授权文件直接复制到其他机器。
- 客户端校验逻辑无法绝对隐藏；发布版需要代码签名、混淆、完整性校验、关键校验点分散到多个导出入口。

## 集成位置

建议新增：

```text
D-Booth/runtime-dotnet/src/Booth.Runtime.ApiHost/Licensing/
  ActivationCodeCodec.cs
  HardwareFingerprint.cs
  LicenseService.cs
  LicenseContracts.cs

D-Booth/runtime-dotnet/tools/LicenseGenerator/
  LicenseGenerator.csproj
  Program.cs

D-Booth/frontend/src/app/components/ActivationGate.tsx
```

`Program.cs` 中注册：

```csharp
builder.Services.AddSingleton<LicenseService>();
builder.Services.AddSingleton<ExportGuard>();
```

然后把所有导出、打印、分享等核心 API 接入 `ExportGuard` 或 `LicenseService`，不要只在 React 层判断授权。
