export type CropType = "olivo" | "tomate" | "almendro" | "vina" | "naranjo";
export type RegionCode = "VALENCIA" | "GUADIX_BAZA";

export interface Plot {
  id: string;
  farm_id: string;
  name: string;
  crop_type: CropType;
  region_code: RegionCode;
  area_ha: number | null;
  created_at: string;
}

export interface PlotsResponse {
  items: Plot[];
  total: number;
  page: number;
  page_size: number;
}
