export interface Booth {
  id: string;
  team_id: string;
  name: string;
  device_id: string;
  status: 'online' | 'offline' | 'busy' | 'error';
  version?: string;
  last_heartbeat?: string;
  ip_address?: string;
  os_info?: string;
  current_event_id?: string;
  current_event?: { name: string };
  config_hash?: string;
  created_at: string;
  updated_at: string;
  stats?: {
    sessions: number;
    photos: number;
    prints: number;
    shares: number;
  };
  storage_used?: string;
}

export interface BoothStats {
  booth_id: string;
  name: string;
  status: string;
  last_heartbeat?: string;
  sessions: number;
  photos: number;
  prints: number;
  shares: number;
}

export interface MultiBoothStats {
  team_id: string;
  total_booths: number;
  active_booths: number;
  total_sessions: number;
  total_photos: number;
  total_prints: number;
  total_shares: number;
  by_booth: BoothStats[];
}

export interface SyncState {
  booth_id: string;
  team_id: string;
  templates_hash: string;
  settings_hash: string;
  props_hash: string;
  cloud_hash: string;
  booth_config_hash?: string;
  need_sync_templates: number;
  need_sync_settings: number;
  need_sync_props: number;
  total_templates: number;
  total_events: number;
  total_props: number;
  is_synced: boolean;
}
