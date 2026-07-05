export function buildLinePath(
  values: (number | null)[],
  width: number,
  height: number,
  padding = 4,
): string {
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < 2) return "";

  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const range = max - min || 1;
  const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : 0;

  let path = "";
  let penDown = false;
  values.forEach((v, i) => {
    if (v === null) {
      penDown = false;
      return;
    }
    const x = padding + i * step;
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    path += `${penDown ? " L" : `${path ? " " : ""}M`} ${x.toFixed(2)} ${y.toFixed(2)}`;
    penDown = true;
  });
  return path.trim();
}

// Mismas coordenadas que buildLinePath, expuestas como puntos individuales
// para poder dibujar marcadores (círculos) sobre cada lectura real.
export function buildLinePoints(
  values: (number | null)[],
  width: number,
  height: number,
  padding = 4,
): { x: number; y: number }[] {
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < 2) return [];

  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const range = max - min || 1;
  const step = values.length > 1 ? (width - padding * 2) / (values.length - 1) : 0;

  const points: { x: number; y: number }[] = [];
  values.forEach((v, i) => {
    if (v === null) return;
    points.push({
      x: padding + i * step,
      y: height - padding - ((v - min) / range) * (height - padding * 2),
    });
  });
  return points;
}
