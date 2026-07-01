import { Metadata } from "next";
import { FarmSelector } from "@/features/farms/components/farm-selector";

export const metadata: Metadata = {
  title: "Seleccionar Finca | AgroCollective",
};

export default function FarmsPage() {
  return <FarmSelector />;
}
