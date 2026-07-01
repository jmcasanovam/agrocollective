export interface Crop {
  id: string;
  name: string;
  description: string | null;
}

export interface Soil {
  id: string;
  name: string;
  description: string | null;
}

export interface Plot {
  id: string;
  farm_id: string;
  crop_id: string;
  soil_id: string;
  name: string;
  area_ha: number | null;
  management_profile: string | null;
  hash_plot: string | null;
}

export interface PlotCreate {
  crop_id: string;
  soil_id: string;
  name: string;
  area_ha?: number | null;
  management_profile?: string | null;
}

export interface PlotUpdate {
  crop_id?: string;
  soil_id?: string;
  name?: string;
  area_ha?: number | null;
  management_profile?: string | null;
}
