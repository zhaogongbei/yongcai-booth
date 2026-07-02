using Booth.Shared.Contracts;
using System.Net;
using System.Net.Http.Json;
using System.Net.Sockets;
using System.Diagnostics;
using Xunit;

namespace Booth.Runtime.Tests;

public sealed class ApiHostIntegrationTests
{
    [Fact]
    public async Task SessionDetails_ShouldReturnShotsJobsAndAssets_FromHttpFlow()
    {
        var tempRoot = CreateTempRoot();

        await using var host = await BoothApiHost.StartAsync(tempRoot);
        using var client = new HttpClient { BaseAddress = host.BaseAddress };

        var startResponse = await client.PostAsJsonAsync("/v1/session/start", new SessionStartApiRequest(
            "ses_http_flow_001",
            "evt_http_flow_001",
            SessionMode.Print,
            "dev_http_flow_001"));
        startResponse.EnsureSuccessStatusCode();

        var captureResponse = await client.PostAsJsonAsync("/v1/sessions/ses_http_flow_001/shots", new CaptureShotApiRequest(
            "shot_http_flow_001",
            "integration-test",
            0.97));
        captureResponse.EnsureSuccessStatusCode();

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
        Assert.Equal("succeeded", execution!.Status);
        Assert.False(string.IsNullOrWhiteSpace(execution.CreatedAssetId));

        var detailsResponse = await client.GetAsync("/v1/sessions/ses_http_flow_001");
        detailsResponse.EnsureSuccessStatusCode();

        var details = await detailsResponse.Content.ReadFromJsonAsync<SessionDetailsApiResponse>();
        Assert.NotNull(details);
        Assert.Equal("ses_http_flow_001", details!.SessionId);
        Assert.Equal("capturing", details.Status);
        Assert.Single(details.Shots);
        Assert.Single(details.Jobs);
        Assert.Single(details.Assets);
        Assert.Equal("shot_http_flow_001", details.Shots[0].ShotId);
        Assert.Equal(0.97, details.Shots[0].AiPickScore);
        Assert.Equal(queuedJob.JobId, details.Jobs[0].JobId);
        Assert.Equal("Succeeded", details.Jobs[0].Status);
        Assert.Equal(execution.CreatedAssetId, details.Assets[0].AssetId);
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

        private BoothApiHost(string tempRoot, Process process, Uri baseAddress, string stdoutPath, string stderrPath)
        {
            _tempRoot = tempRoot;
            _process = process;
            BaseAddress = baseAddress;
            _stdoutPath = stdoutPath;
            _stderrPath = stderrPath;
        }

        public Uri BaseAddress { get; }

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
                "Debug",
                "net8.0-windows",
                "Booth.Runtime.ApiHost.dll"));
            var stdoutPath = Path.Combine(tempRoot, "apihost.stdout.log");
            var stderrPath = Path.Combine(tempRoot, "apihost.stderr.log");

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

            var host = new BoothApiHost(tempRoot, process, baseAddress, stdoutPath, stderrPath);
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
