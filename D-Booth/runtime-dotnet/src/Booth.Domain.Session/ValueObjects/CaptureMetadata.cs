namespace Booth.Domain.Session.ValueObjects;

/// <summary>
/// Value object representing metadata about a captured photo.
/// </summary>
public sealed record CaptureMetadata
{
    /// <summary>
    /// Creates a new instance of <see cref="CaptureMetadata"/>.
    /// </summary>
    /// <param name="exposureTime">Camera exposure time in seconds.</param>
    /// <param name="iso">ISO sensitivity value.</param>
    /// <param name="focalLength">Focal length in millimeters.</param>
    /// <param name="aperture">Aperture f-number.</param>
    /// <param name="whiteBalance">White balance mode used.</param>
    /// <param name="flash">Whether flash was used.</param>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when parameters are out of valid range.</exception>
    public CaptureMetadata(
        double? exposureTime,
        int? iso,
        double? focalLength,
        double? aperture,
        string? whiteBalance,
        bool flash)
    {
        if (exposureTime is < 0)
            throw new ArgumentOutOfRangeException(nameof(exposureTime), "Exposure time cannot be negative.");

        if (iso is < 0)
            throw new ArgumentOutOfRangeException(nameof(iso), "ISO cannot be negative.");

        if (focalLength is < 0)
            throw new ArgumentOutOfRangeException(nameof(focalLength), "Focal length cannot be negative.");

        if (aperture is < 0)
            throw new ArgumentOutOfRangeException(nameof(aperture), "Aperture cannot be negative.");

        ExposureTime = exposureTime;
        Iso = iso;
        FocalLength = focalLength;
        Aperture = aperture;
        WhiteBalance = whiteBalance;
        Flash = flash;
    }

    /// <summary>
    /// Gets the camera exposure time in seconds.
    /// </summary>
    public double? ExposureTime { get; }

    /// <summary>
    /// Gets the ISO sensitivity value.
    /// </summary>
    public int? Iso { get; }

    /// <summary>
    /// Gets the focal length in millimeters.
    /// </summary>
    public double? FocalLength { get; }

    /// <summary>
    /// Gets the aperture f-number.
    /// </summary>
    public double? Aperture { get; }

    /// <summary>
    /// Gets the white balance mode used.
    /// </summary>
    public string? WhiteBalance { get; }

    /// <summary>
    /// Gets a value indicating whether flash was used.
    /// </summary>
    public bool Flash { get; }

    /// <summary>
    /// Creates a default metadata instance with no values set.
    /// </summary>
    public static CaptureMetadata Empty => new(null, null, null, null, null, false);
}
