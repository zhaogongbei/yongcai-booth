using Booth.Plugin.Abstractions.Lifecycle;

namespace Booth.Plugin.Abstractions;

/// <summary>
/// Base interface for all photo booth plugins.
/// Defines common lifecycle and metadata for plugin integration.
/// </summary>
public interface IBoothPlugin
{
    /// <summary>
    /// Gets the unique identifier for this plugin.
    /// Should be stable across versions (e.g., "booth.plugin.camera.canon").
    /// </summary>
    string Id { get; }

    /// <summary>
    /// Gets the human-readable name of the plugin.
    /// </summary>
    string Name { get; }

    /// <summary>
    /// Gets the semantic version of the plugin (e.g., "1.2.0").
    /// </summary>
    string Version { get; }

    /// <summary>
    /// Initializes the plugin with the provided context.
    /// Called once when the plugin is loaded.
    /// </summary>
    /// <param name="context">Runtime context providing capabilities and configuration.</param>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>A task representing the initialization operation.</returns>
    Task InitializeAsync(IPluginContext context, CancellationToken cancellationToken);

    /// <summary>
    /// Gracefully shuts down the plugin and releases resources.
    /// Called once when the plugin is being unloaded.
    /// </summary>
    /// <param name="cancellationToken">Cancellation token for async operations.</param>
    /// <returns>A task representing the shutdown operation.</returns>
    Task ShutdownAsync(CancellationToken cancellationToken);
}
