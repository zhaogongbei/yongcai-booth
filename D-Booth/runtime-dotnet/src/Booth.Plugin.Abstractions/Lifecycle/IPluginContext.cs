namespace Booth.Plugin.Abstractions.Lifecycle;

/// <summary>
/// Provides context and runtime capabilities to plugins during initialization.
/// </summary>
public interface IPluginContext
{
    /// <summary>
    /// Gets the version of the booth runtime hosting the plugin.
    /// </summary>
    string RuntimeVersion { get; }

    /// <summary>
    /// Gets the read-only dictionary of runtime capabilities.
    /// Keys represent capability names, values provide version or status information.
    /// Example: { "usb-control": "2.0", "network-printing": "enabled" }
    /// </summary>
    IReadOnlyDictionary<string, string> Capabilities { get; }

    /// <summary>
    /// Gets plugin-specific configuration values.
    /// Allows plugins to retrieve settings provided at initialization.
    /// </summary>
    IReadOnlyDictionary<string, string> Configuration { get; }
}

/// <summary>
/// Default implementation of <see cref="IPluginContext"/>.
/// </summary>
public sealed class PluginContext : IPluginContext
{
    /// <summary>
    /// Creates a new plugin context.
    /// </summary>
    /// <param name="runtimeVersion">Runtime version string.</param>
    /// <param name="capabilities">Runtime capabilities dictionary.</param>
    /// <param name="configuration">Plugin-specific configuration.</param>
    public PluginContext(
        string runtimeVersion,
        IReadOnlyDictionary<string, string> capabilities,
        IReadOnlyDictionary<string, string> configuration)
    {
        RuntimeVersion = runtimeVersion ?? throw new ArgumentNullException(nameof(runtimeVersion));
        Capabilities = capabilities ?? throw new ArgumentNullException(nameof(capabilities));
        Configuration = configuration ?? throw new ArgumentNullException(nameof(configuration));
    }

    /// <inheritdoc />
    public string RuntimeVersion { get; }

    /// <inheritdoc />
    public IReadOnlyDictionary<string, string> Capabilities { get; }

    /// <inheritdoc />
    public IReadOnlyDictionary<string, string> Configuration { get; }
}
