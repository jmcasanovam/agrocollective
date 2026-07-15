export interface Farm {
  id: string;
  user_id: string;
  name: string;
  region_id: string | null;
  latitude: number | null;
  longitude: number | null;
  area_ha: number | null;
}

export interface FarmCreate {
  name: string;
  region_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  area_ha?: number | null;
}

export interface FarmUpdate {
  name?: string;
  region_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  area_ha?: number | null;
}
