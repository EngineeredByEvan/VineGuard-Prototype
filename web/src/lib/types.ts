export interface Vineyard {
  id: string;
  name: string;
  region: string;
  owner_name: string;
  created_at: string;
}

export interface Block {
  id: string;
  vineyard_id: string;
  name: string;
  variety: string;
  area_ha: number | null;
  reference_lux_peak: number | null;
  notes: string;
  created_at: string;
}

export interface BlockWithNodes extends Block {
  nodes: Node[];
}

export interface Node {
  id: string;
  block_id: string;
  device_id: string;
  name: string;
  tier: 'basic' | 'precision_plus';
  lat: number | null;
  lon: number | null;
  installed_at: string;
  firmware_version: string;
  last_seen_at: string | null;
  battery_voltage: number | null;
  battery_pct: number | null;
  rssi_last: number | null;
  status: 'active' | 'stale' | 'inactive';
}

export interface TelemetryReading {
  id: string;
  device_id: string;
  node_id: string | null;
  soil_moisture: number;
  soil_temp_c: number;
  ambient_temp_c: number;
  ambient_humidity: number;
  light_lux: number;
  battery_voltage: number;
  leaf_wetness_pct: number | null;
  pressure_hpa: number | null;
  recorded_at: string;
}

export interface Alert {
  id: string;
  node_id: string | null;
  block_id: string | null;
  vineyard_id: string;
  rule_key: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  is_active: boolean;
  triggered_at: string;
  resolved_at: string | null;
}

export interface Recommendation {
  id: string;
  alert_id: string | null;
  block_id: string | null;
  vineyard_id: string;
  action_text: string;
  priority: 1 | 2 | 3;
  due_by: string | null;
  is_acknowledged: boolean;
  created_at: string;
}

export interface BlockSummary {
  id: string;
  name: string;
  variety: string;
  node_count: number;
  active_alert_count: number;
  avg_soil_moisture: number | null;
  avg_temp: number | null;
  last_reading_at: string | null;
}

export interface DashboardOverview {
  vineyard_id: string;
  vineyard_name: string;
  block_summaries: BlockSummary[];
  total_active_alerts: number;
  gdd_season_total: number | null;
  gdd_date: string | null;
  online_node_count: number;
  stale_node_count: number;
}

export interface UnregisteredDevice {
  device_id: string;
  last_seen_at: string;
  reading_count: number;
}

export interface GDDEntry {
  vineyard_id: string;
  date: string;
  gdd_daily: number;
  gdd_season_total: number;
}
