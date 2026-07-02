namespace Booth.Domain.Session;

public sealed class Shot
{
    public string Id { get; init; } = string.Empty;
    public int Index { get; init; }
    public DateTimeOffset CapturedAtUtc { get; init; }
    public string? RawAssetPath { get; init; }
    public double? AiPickScore { get; init; }
}
