export interface Device {
  id: string;
  plot_id: string;
  code: string | null;
  is_active: boolean;
  last_seen_at: string | null;
  battery_mv: number | null;
  sensors: unknown[];
}

export interface DeviceCreate {
  code: string;
}

export interface DeviceUpdate {
  code?: string;
  is_active?: boolean;
}
