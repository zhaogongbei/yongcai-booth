using Booth.Shared.Contracts;

namespace Booth.Runtime.SessionApp;

public sealed record SessionStartRequest(
    string SessionId,
    string EventId,
    SessionMode Mode,
    string DeviceId);
