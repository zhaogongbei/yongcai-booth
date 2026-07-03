using Booth.Domain.Session.ValueObjects;

namespace Booth.Domain.Session;

/// <summary>
/// Represents a single captured photo within a session.
/// Immutable entity containing capture details and metadata.
/// </summary>
public sealed class Shot
{
    /// <summary>
    /// Creates a new shot instance.
    /// </summary>
    /// <param name="id">Unique identifier for the shot.</param>
    /// <param name="index">Zero-based index within the session.</param>
    /// <param name="capturedAtUtc">Timestamp when captured (UTC).</param>
    /// <param name="rawAssetPath">File path to the raw captured asset.</param>
    /// <param name="metadata">Camera metadata for this capture.</param>
    /// <param name="aiPickScore">AI-generated quality score (0-1), if available.</param>
    /// <exception cref="ArgumentException">Thrown when ID is empty.</exception>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when index or AI score is invalid.</exception>
    public Shot(
        string id,
        int index,
        DateTimeOffset capturedAtUtc,
        string? rawAssetPath,
        CaptureMetadata? metadata,
        double? aiPickScore)
    {
        if (string.IsNullOrWhiteSpace(id))
            throw new ArgumentException("Shot ID cannot be empty.", nameof(id));

        if (index < 0)
            throw new ArgumentOutOfRangeException(nameof(index), "Index cannot be negative.");

        if (aiPickScore is < 0 or > 1)
            throw new ArgumentOutOfRangeException(nameof(aiPickScore), "AI pick score must be between 0 and 1.");

        Id = id;
        Index = index;
        CapturedAtUtc = capturedAtUtc;
        RawAssetPath = rawAssetPath;
        Metadata = metadata ?? CaptureMetadata.Empty;
        AiPickScore = aiPickScore;
    }

    /// <summary>
    /// Gets the unique identifier for this shot.
    /// </summary>
    public string Id { get; }

    /// <summary>
    /// Gets the zero-based index of this shot within its session.
    /// </summary>
    public int Index { get; }

    /// <summary>
    /// Gets the timestamp when this shot was captured (UTC).
    /// </summary>
    public DateTimeOffset CapturedAtUtc { get; }

    /// <summary>
    /// Gets the file path to the raw captured asset, if available.
    /// </summary>
    public string? RawAssetPath { get; }

    /// <summary>
    /// Gets the camera metadata for this capture.
    /// </summary>
    public CaptureMetadata Metadata { get; }

    /// <summary>
    /// Gets the AI-generated quality score (0-1), if available.
    /// Higher values indicate better perceived quality.
    /// </summary>
    public double? AiPickScore { get; }

    /// <summary>
    /// Factory method for backward compatibility with init-only properties.
    /// </summary>
    internal static Shot CreateLegacy(string id, int index, DateTimeOffset capturedAtUtc, string? rawAssetPath, double? aiPickScore)
    {
        return new Shot(id, index, capturedAtUtc, rawAssetPath, null, aiPickScore);
    }
}
