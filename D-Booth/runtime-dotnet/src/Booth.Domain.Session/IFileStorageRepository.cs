namespace Booth.Domain.Session;

/// <summary>
/// Repository interface for file storage operations.
/// Abstracts local vs. cloud storage implementations.
/// </summary>
public interface IFileStorageRepository
{
    /// <summary>
    /// Saves a file to storage.
    /// </summary>
    /// <param name="sourcePath">Local path to the file to store.</param>
    /// <param name="destinationKey">Storage key/path for the file.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The final storage location/URL of the saved file.</returns>
    Task<string> SaveFileAsync(string sourcePath, string destinationKey, CancellationToken cancellationToken);

    /// <summary>
    /// Retrieves a file from storage to a local path.
    /// </summary>
    /// <param name="storageKey">Storage key/path of the file.</param>
    /// <param name="destinationPath">Local path where the file should be saved.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>A task representing the download operation.</returns>
    Task RetrieveFileAsync(string storageKey, string destinationPath, CancellationToken cancellationToken);

    /// <summary>
    /// Deletes a file from storage.
    /// </summary>
    /// <param name="storageKey">Storage key/path of the file to delete.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>True if the file was deleted, false if it didn't exist.</returns>
    Task<bool> DeleteFileAsync(string storageKey, CancellationToken cancellationToken);

    /// <summary>
    /// Checks if a file exists in storage.
    /// </summary>
    /// <param name="storageKey">Storage key/path to check.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>True if the file exists.</returns>
    Task<bool> ExistsAsync(string storageKey, CancellationToken cancellationToken);

    /// <summary>
    /// Gets a public URL for a stored file, if supported.
    /// </summary>
    /// <param name="storageKey">Storage key/path of the file.</param>
    /// <param name="expiresIn">Optional expiration duration for the URL.</param>
    /// <returns>Public URL to access the file, or null if not supported.</returns>
    Task<string?> GetPublicUrlAsync(string storageKey, TimeSpan? expiresIn = null);
}
