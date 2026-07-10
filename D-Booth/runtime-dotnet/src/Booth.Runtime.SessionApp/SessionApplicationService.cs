using Booth.Domain.Session;
using Booth.Plugin.Abstractions;
using Booth.Plugin.Abstractions.Camera;
using Booth.Shared.Contracts;

namespace Booth.Runtime.SessionApp;

public sealed class SessionApplicationService
{
    private readonly ISessionRepository _sessionRepository;
    private readonly IShotRepository _shotRepository;
    private readonly string _capturesRoot;
    private readonly ICameraPlugin? _cameraPlugin;

    public SessionApplicationService(
        ISessionRepository sessionRepository,
        IShotRepository shotRepository,
        string capturesRoot,
        ICameraPlugin? cameraPlugin = null)
    {
        _sessionRepository = sessionRepository;
        _shotRepository = shotRepository;
        _capturesRoot = capturesRoot;
        _cameraPlugin = cameraPlugin;
    }

    public async Task<SessionAggregate> StartAsync(SessionStartRequest request, CancellationToken cancellationToken)
    {
        var session = new SessionAggregate(
            request.SessionId,
            request.EventId,
            request.Mode,
            request.DeviceId);

        session.BeginCountdown();
        await _sessionRepository.SaveAsync(session, cancellationToken);
        return session;
    }

    public Task<SessionAggregate?> GetAsync(string sessionId, CancellationToken cancellationToken)
    {
        return _sessionRepository.GetAsync(sessionId, cancellationToken);
    }

    public async Task<SessionAggregate?> CancelAsync(string sessionId, CancellationToken cancellationToken)
    {
        var session = await _sessionRepository.GetAsync(sessionId, cancellationToken);
        if (session is null)
        {
            return null;
        }

        session.Cancel();
        await _sessionRepository.SaveAsync(session, cancellationToken);
        return session;
    }

    public async Task<Shot?> CaptureShotAsync(CaptureShotRequest request, CancellationToken cancellationToken)
    {
        var session = await _sessionRepository.GetAsync(request.SessionId, cancellationToken);
        if (session is null)
        {
            return null;
        }

        var shotIndex = await _shotRepository.GetNextShotIndexAsync(request.SessionId, cancellationToken);
        var shotId = request.PreferredShotId ?? $"shot_{Guid.NewGuid():N}";
        var rawAssetPath = BuildCapturePath(request.SessionId, shotId);

        if (_cameraPlugin is null || !_cameraPlugin.IsConnected)
        {
            throw new CaptureShotException(
                ErrorCodes.CameraDeviceNotReady,
                "Runtime camera integration is not configured or connected.");
        }

        session.BeginCapture();

        CaptureResult captureResult;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(rawAssetPath)!);
            captureResult = await _cameraPlugin.CaptureAsync(
                new CaptureConfig { OutputPath = rawAssetPath },
                cancellationToken);

            if (!captureResult.Success
                || string.IsNullOrWhiteSpace(captureResult.FilePath)
                || !PathsEqual(captureResult.FilePath, rawAssetPath)
                || !await IsJpegFileAsync(rawAssetPath, cancellationToken))
            {
                TryDeleteCaptureFile(rawAssetPath);
                throw new CaptureShotException(
                    ErrorCodes.CameraDeviceNotReady,
                    "Camera capture did not produce a valid JPEG file.");
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            TryDeleteCaptureFile(rawAssetPath);
            throw;
        }
        catch (CaptureShotException)
        {
            throw;
        }
        catch (Exception exception)
        {
            TryDeleteCaptureFile(rawAssetPath);
            throw new CaptureShotException(
                ErrorCodes.CameraDeviceNotReady,
                "Camera capture failed before a valid image was produced.",
                exception);
        }

        var captureTimestamp = DateTimeOffset.UtcNow;

        var shot = new Shot(
            shotId,
            shotIndex,
            captureTimestamp,
            rawAssetPath,
            metadata: null,
            request.AiPickScore);

        await _sessionRepository.SaveAsync(session, cancellationToken);
        await _shotRepository.SaveAsync(request.SessionId, shot, cancellationToken);
        return shot;
    }

    public Task<IReadOnlyList<Shot>> ListShotsAsync(string sessionId, CancellationToken cancellationToken)
    {
        return _shotRepository.ListBySessionAsync(sessionId, cancellationToken);
    }

    private string BuildCapturePath(string sessionId, string shotId)
    {
        EnsureSafePathComponent(sessionId, nameof(sessionId));
        EnsureSafePathComponent(shotId, nameof(shotId));

        var capturesRoot = Path.GetFullPath(_capturesRoot);
        var capturePath = Path.GetFullPath(Path.Combine(capturesRoot, sessionId, $"{shotId}.jpg"));
        var rootPrefix = Path.EndsInDirectorySeparator(capturesRoot)
            ? capturesRoot
            : capturesRoot + Path.DirectorySeparatorChar;

        if (!capturePath.StartsWith(rootPrefix, StringComparison.OrdinalIgnoreCase))
        {
            throw new CaptureShotException(
                ErrorCodes.ConfigurationInvalid,
                "Capture identifiers must resolve inside the configured capture directory.");
        }

        return capturePath;
    }

    private static void EnsureSafePathComponent(string value, string parameterName)
    {
        if (string.IsNullOrWhiteSpace(value)
            || value is "." or ".."
            || value.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0
            || value.Contains(Path.DirectorySeparatorChar)
            || value.Contains(Path.AltDirectorySeparatorChar))
        {
            throw new CaptureShotException(
                ErrorCodes.ConfigurationInvalid,
                $"{parameterName} contains invalid path characters.");
        }
    }

    private static bool PathsEqual(string firstPath, string secondPath)
    {
        return string.Equals(
            Path.GetFullPath(firstPath),
            Path.GetFullPath(secondPath),
            StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<bool> IsJpegFileAsync(string path, CancellationToken cancellationToken)
    {
        if (!File.Exists(path))
        {
            return false;
        }

        await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (stream.Length < 4)
        {
            return false;
        }

        var header = new byte[3];
        await stream.ReadExactlyAsync(header, cancellationToken);
        stream.Seek(-2, SeekOrigin.End);
        var footer = new byte[2];
        await stream.ReadExactlyAsync(footer, cancellationToken);

        return header[0] == 0xFF
            && header[1] == 0xD8
            && header[2] == 0xFF
            && footer[0] == 0xFF
            && footer[1] == 0xD9;
    }

    private static void TryDeleteCaptureFile(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
