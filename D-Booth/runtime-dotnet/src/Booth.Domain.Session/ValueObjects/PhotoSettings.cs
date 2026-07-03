namespace Booth.Domain.Session.ValueObjects;

/// <summary>
/// Value object representing photo capture settings.
/// Immutable configuration for how photos should be captured.
/// </summary>
public sealed record PhotoSettings
{
    /// <summary>
    /// Creates a new instance of <see cref="PhotoSettings"/>.
    /// </summary>
    /// <param name="width">Image width in pixels.</param>
    /// <param name="height">Image height in pixels.</param>
    /// <param name="quality">JPEG quality (1-100).</param>
    /// <param name="format">Image format (e.g., "jpeg", "png").</param>
    /// <param name="colorSpace">Color space (e.g., "sRGB", "AdobeRGB").</param>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when parameters are out of valid range.</exception>
    /// <exception cref="ArgumentException">Thrown when format or color space is invalid.</exception>
    public PhotoSettings(
        int width,
        int height,
        int quality,
        string format,
        string colorSpace)
    {
        if (width <= 0)
            throw new ArgumentOutOfRangeException(nameof(width), "Width must be positive.");

        if (height <= 0)
            throw new ArgumentOutOfRangeException(nameof(height), "Height must be positive.");

        if (quality is < 1 or > 100)
            throw new ArgumentOutOfRangeException(nameof(quality), "Quality must be between 1 and 100.");

        if (string.IsNullOrWhiteSpace(format))
            throw new ArgumentException("Format cannot be empty.", nameof(format));

        if (string.IsNullOrWhiteSpace(colorSpace))
            throw new ArgumentException("Color space cannot be empty.", nameof(colorSpace));

        Width = width;
        Height = height;
        Quality = quality;
        Format = format.ToLowerInvariant();
        ColorSpace = colorSpace;
    }

    /// <summary>
    /// Gets the image width in pixels.
    /// </summary>
    public int Width { get; }

    /// <summary>
    /// Gets the image height in pixels.
    /// </summary>
    public int Height { get; }

    /// <summary>
    /// Gets the JPEG quality (1-100).
    /// </summary>
    public int Quality { get; }

    /// <summary>
    /// Gets the image format (e.g., "jpeg", "png").
    /// </summary>
    public string Format { get; }

    /// <summary>
    /// Gets the color space (e.g., "sRGB", "AdobeRGB").
    /// </summary>
    public string ColorSpace { get; }

    /// <summary>
    /// Gets the aspect ratio of the photo.
    /// </summary>
    public double AspectRatio => (double)Width / Height;

    /// <summary>
    /// Creates default photo settings for standard booth output.
    /// 4:3 aspect ratio, 1600x1200, JPEG quality 95.
    /// </summary>
    public static PhotoSettings Default => new(1600, 1200, 95, "jpeg", "sRGB");

    /// <summary>
    /// Creates photo settings for high-resolution output.
    /// 4:3 aspect ratio, 3200x2400, JPEG quality 98.
    /// </summary>
    public static PhotoSettings HighResolution => new(3200, 2400, 98, "jpeg", "sRGB");

    /// <summary>
    /// Creates a new <see cref="PhotoSettings"/> with modified quality.
    /// </summary>
    /// <param name="quality">New quality value (1-100).</param>
    /// <returns>New instance with updated quality.</returns>
    public PhotoSettings WithQuality(int quality) => this with { Quality = quality };
}
