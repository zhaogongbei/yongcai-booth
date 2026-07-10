using Booth.Runtime.Licensing;
using Booth.Shared.Contracts;
using System.Net;
using System.Net.Http.Json;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text.Json;
using System.Diagnostics;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class ApiHostIntegrationTests
{
    [Fact]
    public async Task SessionDetails_ShouldPersistFailedPrintJob_WhenPrinterIsNotConfigured()
    {
        var tempRoot = CreateTempRoot();

        await using var host = await BoothApiHost.StartAsync(tempRoot);
        using var client = new HttpClient { BaseAddress = host.BaseAddress };

        await ActivateRuntimeLicenseAsync(client, host.SigningKey);

        var startResponse = await client.PostAsJsonAsync("/v1/session/start", new SessionStartApiRequest(
            "ses_http_flow_001",
            "evt_http_flow_001",
            SessionMode.Print,
            "dev_http_flow_001"));
        startResponse.EnsureSuccessStatusCode();

        var queueResponse = await client.PostAsJsonAsync("/v1/print/jobs", new PrintJobApiRequest(
            "ses_http_flow_001",
            2,
            "printer_http_flow_001"));
        Assert.Equal(HttpStatusCode.Accepted, queueResponse.StatusCode);

        var queuedJob = await queueResponse.Content.ReadFromJsonAsync<JobQueuedApiResponse>();
        Assert.NotNull(queuedJob);

        var executeResponse = await client.PostAsync($"/v1/jobs/{queuedJob!.JobId}/execute", content: null);
        executeResponse.EnsureSuccessStatusCode();

        var execution = await executeResponse.Content.ReadFromJsonAsync<JobExecutionApiResponse>();
        Assert.NotNull(execution);
        Assert.Equal("failed", execution!.Status);
        Assert.Null(execution.CreatedAssetId);

        var detailsResponse = await client.GetAsync("/v1/sessions/ses_http_flow_001");
        detailsResponse.EnsureSuccessStatusCode();

        var details = await detailsResponse.Content.ReadFromJsonAsync<SessionDetailsApiResponse>();
        Assert.NotNull(details);
        Assert.Equal("ses_http_flow_001", details!.SessionId);
        Assert.Equal("countdown", details.Status);
        Assert.Empty(details.Shots);
        Assert.Single(details.Jobs);
        Assert.Empty(details.Assets);
        Assert.Equal(queuedJob.JobId, details.Jobs[0].JobId);
        Assert.Equal("Failed", details.Jobs[0].Status);
        Assert.Equal(ErrorCodes.PrintQueueUnavailable, details.Jobs[0].LastErrorCode);
        Assert.Null(details.Jobs[0].CreatedAssetId);
    }

    [Fact]
    public async Task CaptureShot_ShouldReturnServiceUnavailable_WhenCameraIsNotConfigured()
    {
        var tempRoot = CreateTempRoot();

        await using var host = await BoothApiHost.StartAsync(tempRoot);
        using var client = new HttpClient { BaseAddress = host.BaseAddress };

        var startResponse = await client.PostAsJsonAsync("/v1/session/start", new SessionStartApiRequest(
            "ses_http_capture_unavailable",
            "evt_http_capture_unavailable",
            SessionMode.Print,
            "dev_http_capture_unavailable"));
        startResponse.EnsureSuccessStatusCode();

        var captureResponse = await client.PostAsJsonAsync(
            "/v1/sessions/ses_http_capture_unavailable/shots",
            new CaptureShotApiRequest("shot_http_capture_unavailable", "integration-test", 0.97));

        Assert.Equal(HttpStatusCode.ServiceUnavailable, captureResponse.StatusCode);
        using var error = JsonDocument.Parse(await captureResponse.Content.ReadAsStringAsync());
        Assert.Equal(
            ErrorCodes.CameraDeviceNotReady,
            error.RootElement.GetProperty("errorCode").GetString());

        var shotsResponse = await client.GetAsync("/v1/sessions/ses_http_capture_unavailable/shots");
        shotsResponse.EnsureSuccessStatusCode();
        var shots = await shotsResponse.Content.ReadFromJsonAsync<ShotDetailsApiResponse[]>();
        Assert.NotNull(shots);
        Assert.Empty(shots!);
        Assert.False(Directory.Exists(Path.Combine(tempRoot, "captures", "ses_http_capture_unavailable")));
    }

    [Fact]
    public async Task SessionDetails_ShouldReturnNotFound_WhenSessionDoesNotExist()
    {
        var tempRoot = CreateTempRoot();

        await using var host = await BoothApiHost.StartAsync(tempRoot);
        using var client = new HttpClient { BaseAddress = host.BaseAddress };

        var response = await client.GetAsync("/v1/sessions/ses_missing_001");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task FrontendCors_ShouldAllowLocalDevOrigin_AndRejectPublicOrigin()
    {
        var tempRoot = CreateTempRoot();

        await using var host = await BoothApiHost.StartAsync(tempRoot);
        using var client = new HttpClient { BaseAddress = host.BaseAddress };

        using var allowedRequest = new HttpRequestMessage(HttpMethod.Get, "/v1/health");
        allowedRequest.Headers.Add("Origin", "http://localhost:5173");
        var allowedResponse = await client.SendAsync(allowedRequest);

        allowedResponse.EnsureSuccessStatusCode();
        Assert.True(allowedResponse.Headers.TryGetValues("Access-Control-Allow-Origin", out var allowedOrigins));
        Assert.Contains("http://localhost:5173", allowedOrigins);

        using var rejectedRequest = new HttpRequestMessage(HttpMethod.Get, "/v1/health");
        rejectedRequest.Headers.Add("Origin", "https://example.com");
        var rejectedResponse = await client.SendAsync(rejectedRequest);

        rejectedResponse.EnsureSuccessStatusCode();
        Assert.False(rejectedResponse.Headers.Contains("Access-Control-Allow-Origin"));
    }


    private static async Task ActivateRuntimeLicenseAsync(HttpClient client, RSA signingKey)
    {
        var payload = new LicensePayload(
            Version: 1,
            Product: LicenseService.ProductName,
            LicenseId: "LIC-RUNTIME-TEST",
            DeviceFingerprint: BoothApiHost.TestFingerprint,
            ExpiresAtUtc: DateTimeOffset.UtcNow.AddDays(30),
            Features: new[] { "export", "print", "share" });

        var payloadBytes = JsonSerializer.SerializeToUtf8Bytes(payload);
        var signature = signingKey.SignData(payloadBytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        var envelope = new SignedLicenseEnvelope(
            Convert.ToBase64String(payloadBytes),
            Convert.ToBase64String(signature));
        var code = ActivationCodeCodec.Encode(JsonSerializer.SerializeToUtf8Bytes(envelope));

        var response = await client.PostAsJsonAsync("/v1/license/activate", new ActivateLicenseRequest(code));
        response.EnsureSuccessStatusCode();
    }

    private static string CreateTempRoot()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"booth-runtime-api-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempRoot);
        return tempRoot;
    }

    private sealed class BoothApiHost : IAsyncDisposable
    {
        private readonly string _tempRoot;
        private readonly Process _process;
        private readonly string _stdoutPath;
        private readonly string _stderrPath;
        private readonly RSA _signingKey;

        private BoothApiHost(string tempRoot, Process process, Uri baseAddress, string stdoutPath, string stderrPath, RSA signingKey)
        {
            _tempRoot = tempRoot;
            _process = process;
            BaseAddress = baseAddress;
            _stdoutPath = stdoutPath;
            _stderrPath = stderrPath;
            _signingKey = signingKey;
        }

        public const string TestFingerprint = "runtime-test-fingerprint";

        public Uri BaseAddress { get; }

        public RSA SigningKey => _signingKey;

        public static async Task<BoothApiHost> StartAsync(string tempRoot)
        {
            var port = GetFreeTcpPort();
            var baseAddress = new Uri($"http://127.0.0.1:{port}");
            var apiHostDllPath = Path.GetFullPath(Path.Combine(
                AppContext.BaseDirectory,
                "..",
                "..",
                "..",
                "..",
                "..",
                "src",
                "Booth.Runtime.ApiHost",
                "bin",
                GetBuildConfiguration(),
                "net8.0-windows",
                "Booth.Runtime.ApiHost.dll"));
            var stdoutPath = Path.Combine(tempRoot, "apihost.stdout.log");
            var stderrPath = Path.Combine(tempRoot, "apihost.stderr.log");

            var signingKey = RSA.Create(2048);

            var startInfo = new ProcessStartInfo
            {
                FileName = "dotnet",
                Arguments = $"\"{apiHostDllPath}\" --urls {baseAddress}",
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            startInfo.Environment["DOTNET_ROLL_FORWARD"] = "Major";
            startInfo.Environment["Runtime__DataDirectory"] = tempRoot;
            startInfo.Environment["Runtime__License__PublicKeyPem"] = signingKey.ExportSubjectPublicKeyInfoPem();
            startInfo.Environment["Runtime__License__FingerprintOverride"] = TestFingerprint;
            startInfo.Environment["ASPNETCORE_URLS"] = baseAddress.ToString();

            var process = Process.Start(startInfo)
                ?? throw new InvalidOperationException("Unable to start Booth.Runtime.ApiHost process.");

            _ = process.StandardOutput.ReadToEndAsync().ContinueWith(async task =>
            {
                await File.WriteAllTextAsync(stdoutPath, task.Result);
            }).Unwrap();
            _ = process.StandardError.ReadToEndAsync().ContinueWith(async task =>
            {
                await File.WriteAllTextAsync(stderrPath, task.Result);
            }).Unwrap();

            var host = new BoothApiHost(tempRoot, process, baseAddress, stdoutPath, stderrPath, signingKey);
            await host.WaitUntilHealthyAsync();
            return host;
        }

        public async ValueTask DisposeAsync()
        {
            if (!_process.HasExited)
            {
                _process.Kill(entireProcessTree: true);
                await _process.WaitForExitAsync();
            }

            if (Directory.Exists(_tempRoot))
            {
                for (var attempt = 0; attempt < 5; attempt++)
                {
                    try
                    {
                        Directory.Delete(_tempRoot, recursive: true);
                        break;
                    }
                    catch (IOException) when (attempt < 4)
                    {
                        await Task.Delay(150);
                    }
                    catch (UnauthorizedAccessException) when (attempt < 4)
                    {
                        await Task.Delay(150);
                    }
                }
            }
        }


        private static string GetBuildConfiguration()
        {
            var baseDirectory = new DirectoryInfo(AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            return baseDirectory.Parent?.Name ?? "Release";
        }
        private async Task WaitUntilHealthyAsync()
        {
            using var client = new HttpClient();
            var deadline = DateTimeOffset.UtcNow.AddSeconds(15);

            while (DateTimeOffset.UtcNow < deadline)
            {
                if (_process.HasExited)
                {
                    var stdout = File.Exists(_stdoutPath) ? await File.ReadAllTextAsync(_stdoutPath) : string.Empty;
                    var stderr = File.Exists(_stderrPath) ? await File.ReadAllTextAsync(_stderrPath) : string.Empty;
                    throw new InvalidOperationException($"Booth.Runtime.ApiHost exited before becoming healthy. ExitCode={_process.ExitCode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}");
                }

                try
                {
                    using var requestTimeout = new CancellationTokenSource(TimeSpan.FromSeconds(2));
                    var response = await client.GetAsync(new Uri(BaseAddress, "/v1/health"), requestTimeout.Token);
                    if (response.IsSuccessStatusCode)
                    {
                        return;
                    }
                }
                catch
                {
                }

                await Task.Delay(250);
            }

            throw new TimeoutException("Booth.Runtime.ApiHost did not become healthy in time.");
        }

        private static int GetFreeTcpPort()
        {
            using var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            return ((IPEndPoint)listener.LocalEndpoint).Port;
        }
    }
}
