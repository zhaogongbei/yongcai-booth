CREATE TABLE IF NOT EXISTS booth_devices (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    site_id UUID NULL,
    device_name TEXT NOT NULL,
    runtime_version TEXT NOT NULL,
    health_status TEXT NOT NULL,
    last_heartbeat_at TIMESTAMPTZ NULL,
    hardware_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    certificate_thumbprint TEXT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    campaign_name TEXT NOT NULL,
    status TEXT NOT NULL,
    starts_at TIMESTAMPTZ NULL,
    ends_at TIMESTAMPTZ NULL,
    package_manifest JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS template_versions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    template_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    status TEXT NOT NULL,
    theme_id UUID NULL,
    manifest_json JSONB NOT NULL,
    preview_urls JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS device_health_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    device_id UUID NOT NULL,
    status_from TEXT NULL,
    status_to TEXT NOT NULL,
    event_code TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    actor_id UUID NULL,
    actor_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id UUID NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_booth_devices_tenant_health
    ON booth_devices(tenant_id, health_status);

CREATE INDEX IF NOT EXISTS idx_template_versions_tenant_template
    ON template_versions(tenant_id, template_id, version_no DESC);

CREATE INDEX IF NOT EXISTS idx_device_health_events_device_time
    ON device_health_events(device_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_time
    ON audit_events(tenant_id, occurred_at DESC);
