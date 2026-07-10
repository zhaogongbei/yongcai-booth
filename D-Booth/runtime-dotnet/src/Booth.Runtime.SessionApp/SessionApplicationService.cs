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
        if (await _sessionRepository.TryAddAsync(session, cancellationToken))
        {
            return session;
        }

        var existing = await _sessionRepository.GetAsync(request.SessionId, cancellationToken);
        if (existing is not null
            && string.Equals(existing.EventId, request.EventId, StringComparison.Ordinal)
            && existing.Mode == request.Mode
            && string.Equals(existing.DeviceId, request.DeviceId, StringComparison.Ordinal))
        {
            return existing;
        }

        throw new SessionStartException(
            ErrorCodes.SessionConflict,
            "Session ID already exists with a different event, mode, or device identity.");
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

        if (await _shotRepository.ExistsAsync(shotId, cancellationToken) || File.Exists(rawAssetPath))
        {
            throw new CaptureShotException(
                ErrorCodes.ShotConflict,
                "Shot ID or capture path already exists.");
        }

        if (_cameraPlugin is null || !_cameraPlugin.IsConnected)
        {
            throw new CaptureShotException(
                ErrorCodes.CameraDeviceNotReady,
                "Runtime camera integration is not configured or connected.");
        }

        session.BeginCapture();
        var captureTempPath = BuildCaptureTempPath(rawAssetPath);

        CaptureResult captureResult;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(captureTempPath)!);
            captureResult = await _cameraPlugin.CaptureAsync(
                new CaptureConfig { OutputPath = captureTempPath },
                cancellationToken);

            if (!captureResult.Success
                || string.IsNullOrWhiteSpace(captureResult.FilePath)
                || !PathsEqual(captureResult.FilePath, captureTempPath)
                || !await IsJpegFileAsync(captureTempPath, cancellationToken))
            {
                TryDeleteCaptureFile(captureTempPath);
                throw new CaptureShotException(
                    ErrorCodes.CameraDeviceNotReady,
                    "Camera capture did not produce a valid JPEG file.");
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            TryDeleteCaptureFile(captureTempPath);
            throw;
        }
        catch (CaptureShotException)
        {
            throw;
        }
        catch (Exception exception)
        {
            TryDeleteCaptureFile(captureTempPath);
            throw new CaptureShotException(
                ErrorCodes.CameraDeviceNotReady,
                "Camera capture failed before a valid image was produced.",
                exception);
        }

        try
        {
            File.Move(captureTempPath, rawAssetPath, overwrite: false);
        }
        catch (IOException exception) when (File.Exists(rawAssetPath))
        {
            TryDeleteCaptureFile(captureTempPath);
            throw new CaptureShotException(
                ErrorCodes.ShotConflict,
                "Shot capture path was created by another request.",
                exception);
        }
        catch (Exception exception)
        {
            TryDeleteCaptureFile(captureTempPath);
            throw new CaptureShotException(
                ErrorCodes.CameraDeviceNotReady,
                "Captured image could not be moved into durable storage.",
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

        bool inserted;
        try
        {
            inserted = await _shotRepository.TryAddAsync(request.SessionId, shot, cancellationToken);
        }
        catch
        {
            TryDeleteCaptureFile(rawAssetPath);
            throw;
        }

        if (!inserted)
        {
            TryDeleteCaptureFile(rawAssetPath);
            throw new CaptureShotException(
                ErrorCodes.ShotConflict,
                "Shot ID was claimed by another request.");
        }

        await _sessionRepository.SaveAsync(session, cancellationToken);
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

    private static string BuildCaptureTempPath(string rawAssetPath)
    {
        var directory = Path.GetDirectoryName(rawAssetPath)!;
        var fileName = Path.GetFileNameWithoutExtension(rawAssetPath);
        return Path.Combine(directory, $".{fileName}.{Guid.NewGuid():N}.capture.jpg");
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
