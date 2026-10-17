/**
 * Spherical & ellipsoidal geodesic calculation utilities.
 */

export function calculatePolygonAreaHa(coords: [number, number][]): number {
  if (coords.length < 3) return 0;
  const lons = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  const meanLat = lats.reduce((a, b) => a + b, 0) / lats.length;
  const meanLon = lons.reduce((a, b) => a + b, 0) / lons.length;
  const latRad = (meanLat * Math.PI) / 180;
  const cosLat = Math.cos(latRad);
  const mPerDegLat = 111132.954 - 559.822 * Math.cos(2 * latRad) + 1.175 * Math.cos(4 * latRad);
  const mPerDegLon = 111412.84 * cosLat - 93.5 * Math.cos(3 * latRad);

  let area = 0;
  for (let i = 0; i < coords.length; i++) {
    const j = (i + 1) % coords.length;
    const xi = (coords[i][0] - meanLon) * mPerDegLon;
    const yi = (coords[i][1] - meanLat) * mPerDegLat;
    const xj = (coords[j][0] - meanLon) * mPerDegLon;
    const yj = (coords[j][1] - meanLat) * mPerDegLat;
    area += xi * yj - xj * yi;
  }
  return (Math.abs(area) * 0.5) / 10000;
}
