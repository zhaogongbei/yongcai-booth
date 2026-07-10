using Booth.Domain.Session;
using Booth.Infra.Storage.Sqlite;
using Booth.Runtime.JobApp;
using Booth.Runtime.Licensing;
using Booth.Runtime.SessionApp;
using Booth.Shared.Contracts;
using System.Net;

var builder = WebApplication.CreateBuilder(args);
const string FrontendCorsPolicy = "FrontendDev";

var dataDir = builder.Configuration["Runtime:DataDirectory"]
    ?? Path.Combine(AppContext.BaseDirectory, "data");
var databasePath = Path.Combine(dataDir, "runtime.db");
var outputsRoot = Path.Combine(dataDir, "outputs");
var capturesRoot = Path.Combine(dataDir, "captures");
var licenseRoot = Path.Combine(dataDir, ".license");

builder.Services.AddSingleton(new SqliteSessionRepository(databasePath));
builder.Services.AddSingleton(new SqliteShotRepository(databasePath));
builder.Services.AddSingleton(new SqliteJobRepository(databasePath));
builder.Services.AddSingleton(new SqliteOutputAssetRepository(databasePath));
builder.Services.AddSingleton<SessionApplicationService>(sp =>
    new SessionApplicationService(
        sp.GetRequiredService<SqliteSessionRepository>(),
        sp.GetRequiredService<SqliteShotRepository>(),
        capturesRoot));
builder.Services.AddSingleton(sp =>
    new LicenseService(
        licenseRoot,
        builder.Configuration["Runtime:License:PublicKeyPem"] ?? string.Empty,
        string.IsNullOrWhiteSpace(builder.Configuration["Runtime:License:FingerprintOverride"])
            ? null
            : () => builder.Configuration["Runtime:License:FingerprintOverride"]!));
builder.Services.AddSingleton<IJobExecutor, PrintJobExecutor>();
builder.Services.AddSingleton<IJobExecutor, ShareJobExecutor>();
builder.Services.AddSingleton(sp =>
    new JobExecutionService(
        sp.GetRequiredService<SqliteJobRepository>(),
        sp.GetRequiredService<SqliteOutputAssetRepository>(),
        sp.GetServices<IJobExecutor>(),
        outputsRoot));
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddCors(options =>
{
    options.AddPolicy(FrontendCorsPolicy, policy =>
        policy
            .SetIsOriginAllowed(IsFrontendDevOrigin)
            .AllowAnyHeader()
            .AllowAnyMethod());
});

var app = builder.Build();

app.UseCors(FrontendCorsPolicy);
app.UseSwagger();
app.UseSwaggerUI();

app.MapGet("/v1/health", () =>
    Results.Ok(new HealthCheckResponse("healthy", "1.0.0-dev")))
    .WithTags("Health");

app.MapGet("/v1/license/status", (LicenseService license) =>
    Results.Ok(license.GetStatus()))
    .WithTags("License");

app.MapPost("/v1/license/activate", (ActivateLicenseRequest request, LicenseService license) =>
{
    var result = license.Activate(request.Code);
    return result.IsActivated
        ? Results.Ok(result)
        : Results.BadRequest(result);
})
    .WithTags("License");
app.MapPost("/v1/session/start", async (SessionStartApiRequest request, SessionApplicationService service, CancellationToken cancellationToken) =>
{
    SessionAggregate session;
    try
    {
        session = await service.StartAsync(
            new SessionStartRequest(request.SessionId, request.EventId, request.Mode, request.DeviceId),
            cancellationToken);
    }
    catch (SessionStartException exception)
    {
        return Results.Conflict(new { errorCode = exception.ErrorCode, message = exception.Message });
    }

    return Results.Ok(new SessionStartApiResponse(
        session.Id,
        session.Status.ToString().ToLowerInvariant(),
        "countdown"));
})
    .WithTags("Sessions");

app.MapPost("/v1/session/{sessionId}/cancel", async (string sessionId, SessionApplicationService service, CancellationToken cancellationToken) =>
{
    SessionAggregate? session;
    try
    {
        session = await service.CancelAsync(sessionId, cancellationToken);
    }
    catch (SessionStateException exception)
    {
        return Results.Conflict(new { errorCode = exception.ErrorCode, message = exception.Message });
    }

    if (session is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.ConfigurationInvalid, message = "Session not found." });
    }

    return Results.Ok(new SessionCancelApiResponse(
        session.Id,
        session.Status.ToString().ToLowerInvariant()));
})
    .WithTags("Sessions");

app.MapGet("/v1/sessions/{sessionId}", async (
    string sessionId,
    SessionApplicationService sessionService,
    SqliteJobRepository jobRepository,
    SqliteOutputAssetRepository assetRepository,
    CancellationToken cancellationToken) =>
{
    var session = await sessionService.GetAsync(sessionId, cancellationToken);
    if (session is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.SessionNotFound, message = "Session not found." });
    }

    var shots = await sessionService.ListShotsAsync(sessionId, cancellationToken);
    var jobs = await jobRepository.ListByAggregateAsync(sessionId, cancellationToken);
    var assets = await assetRepository.ListBySessionAsync(sessionId, cancellationToken);

    return Results.Ok(new SessionDetailsApiResponse(
        session.Id,
        session.EventId,
        session.Mode.ToString(),
        session.Status.ToString().ToLowerInvariant(),
        session.DeviceId,
        session.StartedAtUtc.UtcDateTime.ToString("O"),
        session.CompletedAtUtc?.UtcDateTime.ToString("O"),
        session.RetryCount,
        shots.Select(shot => new ShotDetailsApiResponse(
            shot.Id,
            sessionId,
            shot.Index,
            shot.RawAssetPath ?? string.Empty,
            shot.CapturedAtUtc.UtcDateTime.ToString("O"),
            shot.AiPickScore)).ToArray(),
        jobs,
        assets));
})
    .WithTags("Sessions");

app.MapPost("/v1/sessions/{sessionId}/shots", async (string sessionId, CaptureShotApiRequest request, SessionApplicationService service, CancellationToken cancellationToken) =>
{
    Shot? shot;
    try
    {
        shot = await service.CaptureShotAsync(
            new CaptureShotRequest(sessionId, request.PreferredShotId, request.SourceLabel, request.AiPickScore),
            cancellationToken);
    }
    catch (CaptureShotException exception)
    {
        var statusCode = exception.ErrorCode switch
        {
            ErrorCodes.ConfigurationInvalid => StatusCodes.Status400BadRequest,
            ErrorCodes.ShotConflict => StatusCodes.Status409Conflict,
            ErrorCodes.SessionInvalidState => StatusCodes.Status409Conflict,
            _ => StatusCodes.Status503ServiceUnavailable
        };
        return Results.Json(
            new { errorCode = exception.ErrorCode, message = exception.Message },
            statusCode: statusCode);
    }

    if (shot is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.SessionNotFound, message = "Session not found." });
    }

    return Results.Ok(new CaptureShotApiResponse(
        sessionId,
        shot.Id,
        shot.Index,
        shot.RawAssetPath ?? string.Empty,
        shot.CapturedAtUtc.UtcDateTime.ToString("O")));
})
    .WithTags("Shots");

app.MapGet("/v1/sessions/{sessionId}/shots", async (string sessionId, SessionApplicationService service, CancellationToken cancellationToken) =>
{
    var session = await service.GetAsync(sessionId, cancellationToken);
    if (session is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.SessionNotFound, message = "Session not found." });
    }

    var shots = await service.ListShotsAsync(sessionId, cancellationToken);
    return Results.Ok(shots.Select(shot => new ShotDetailsApiResponse(
        shot.Id,
        sessionId,
        shot.Index,
        shot.RawAssetPath ?? string.Empty,
        shot.CapturedAtUtc.UtcDateTime.ToString("O"),
        shot.AiPickScore)));
})
    .WithTags("Shots");

app.MapPost("/v1/print/jobs", async (PrintJobApiRequest request, SessionApplicationService sessionService, SqliteJobRepository repository, LicenseService license, CancellationToken cancellationToken) =>
{
    var licenseStatus = license.GetStatus();
    if (!licenseStatus.IsActivated)
    {
        return Results.Forbid();
    }

    var session = await sessionService.GetAsync(request.SessionId, cancellationToken);
    if (session is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.SessionNotFound, message = "Session not found." });
    }

    var jobId = await repository.QueueJobAsync(
        JobType.Print,
        request.SessionId,
        priority: 100,
        cancellationToken: cancellationToken,
        payload: new PrintJobPayload(request.Copies, request.PrinterProfileId));

    return Results.Accepted($"/v1/jobs/{jobId}",
        new JobQueuedApiResponse(jobId, JobType.Print.ToString().ToLowerInvariant(), JobStatus.Queued.ToString().ToLowerInvariant()));
})
    .WithTags("Jobs");

app.MapPost("/v1/share/jobs", async (ShareJobApiRequest request, SessionApplicationService sessionService, SqliteJobRepository repository, LicenseService license, CancellationToken cancellationToken) =>
{
    var licenseStatus = license.GetStatus();
    if (!licenseStatus.IsActivated)
    {
        return Results.Forbid();
    }

    var session = await sessionService.GetAsync(request.SessionId, cancellationToken);
    if (session is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.SessionNotFound, message = "Session not found." });
    }

    var jobIds = new List<string>();
    foreach (var channel in request.Channels)
    {
        var jobId = await repository.QueueJobAsync(
            JobType.Share,
            request.SessionId,
            priority: 120,
            cancellationToken: cancellationToken,
            payload: new ShareJobPayload(channel.Type, channel.Recipient, request.ConsentToken));
        jobIds.Add(jobId);
    }

    return Results.Accepted("/v1/jobs",
        new ShareJobsQueuedApiResponse(jobIds, JobStatus.Queued.ToString().ToLowerInvariant()));
})
    .WithTags("Jobs");

app.MapGet("/v1/jobs/{jobId}", async (string jobId, SqliteJobRepository repository, CancellationToken cancellationToken) =>
{
    var job = await repository.GetAsync(jobId, cancellationToken);
    return job is null
        ? Results.NotFound(new { errorCode = ErrorCodes.JobNotFound, message = "Job not found." })
        : Results.Ok(job);
})
    .WithTags("Jobs");

app.MapPost("/v1/jobs/{jobId}/execute", async (string jobId, JobExecutionService executionService, CancellationToken cancellationToken) =>
{
    var result = await executionService.ExecuteAsync(jobId, cancellationToken);
    return result is null
        ? Results.NotFound(new { errorCode = ErrorCodes.JobNotFound, message = "Job not found." })
        : Results.Ok(result);
})
    .WithTags("Jobs");

app.MapGet("/v1/sessions/{sessionId}/assets", async (string sessionId, SessionApplicationService sessionService, SqliteOutputAssetRepository repository, CancellationToken cancellationToken) =>
{
    var session = await sessionService.GetAsync(sessionId, cancellationToken);
    if (session is null)
    {
        return Results.NotFound(new { errorCode = ErrorCodes.SessionNotFound, message = "Session not found." });
    }

    var assets = await repository.ListBySessionAsync(sessionId, cancellationToken);
    return Results.Ok(assets);
})
    .WithTags("Assets");

app.MapGet("/v1/assets/{assetId}", async (string assetId, SqliteOutputAssetRepository repository, CancellationToken cancellationToken) =>
{
    var asset = await repository.GetAsync(assetId, cancellationToken);
    return asset is null
        ? Results.NotFound(new { errorCode = ErrorCodes.ConfigurationInvalid, message = "Asset not found." })
        : Results.Ok(asset);
})
    .WithTags("Assets");

app.MapDelete("/v1/assets/{assetId}", async (string assetId, SqliteOutputAssetRepository repository, CancellationToken cancellationToken) =>
{
    var deleted = await repository.SoftDeleteAsync(assetId, cancellationToken);
    return deleted
        ? Results.Ok(new { assetId, status = "deleted" })
        : Results.NotFound(new { errorCode = ErrorCodes.ConfigurationInvalid, message = "Asset not found." });
})
    .WithTags("Assets");

app.Run();

static bool IsFrontendDevOrigin(string origin)
{
    if (!Uri.TryCreate(origin, UriKind.Absolute, out var uri) || uri.Port != 5173)
    {
        return false;
    }

    if (uri.IsLoopback)
    {
        return true;
    }

    if (!IPAddress.TryParse(uri.Host, out var address))
    {
        return false;
    }

    var bytes = address.GetAddressBytes();
    return bytes.Length == 4
        && (bytes[0] == 10
            || (bytes[0] == 172 && bytes[1] >= 16 && bytes[1] <= 31)
            || (bytes[0] == 192 && bytes[1] == 168));
}
