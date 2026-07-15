// management_profile es texto libre en BD (sin enum), pero por convencion el
// backend usa estos 3 valores en snake_case (ver setup_simulation.py). Los
// traducimos a texto legible; cualquier otro valor (texto libre de un usuario
// real) se muestra tal cual, sin tocar.
const MANAGEMENT_PROFILE_LABELS: Record<string, string> = {
  seco_eficiente: "Seco eficiente",
  moderado: "Moderado",
  humedo_intensivo: "Húmedo intensivo",
};

export function formatManagementProfile(profile: string | null | undefined): string {
  if (!profile) return "Secano";
  return MANAGEMENT_PROFILE_LABELS[profile] ?? profile;
}
