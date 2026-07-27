/** Major cities for discreet globe pins (lat/lon WGS84, degrees). */
export interface City {
  name: string
  lat: number
  lon: number
  /** Higher = prefer label when zoomed */
  tier?: 1 | 2
}

/** Capitals / hubs — keep sparse so the globe stays readable. */
export const CITIES: City[] = [
  // Americas
  { name: 'New York', lat: 40.71, lon: -74.01, tier: 1 },
  { name: 'Washington', lat: 38.91, lon: -77.04, tier: 1 },
  { name: 'Los Angeles', lat: 34.05, lon: -118.24, tier: 2 },
  { name: 'Chicago', lat: 41.88, lon: -87.63, tier: 2 },
  { name: 'Toronto', lat: 43.65, lon: -79.38, tier: 2 },
  { name: 'Mexico City', lat: 19.43, lon: -99.13, tier: 1 },
  { name: 'Bogotá', lat: 4.71, lon: -74.07, tier: 2 },
  { name: 'Lima', lat: -12.05, lon: -77.04, tier: 2 },
  { name: 'São Paulo', lat: -23.55, lon: -46.63, tier: 1 },
  { name: 'Rio', lat: -22.91, lon: -43.17, tier: 2 },
  { name: 'Brasília', lat: -15.79, lon: -47.88, tier: 1 },
  { name: 'Recife', lat: -8.05, lon: -34.9, tier: 2 },
  { name: 'Buenos Aires', lat: -34.6, lon: -58.38, tier: 1 },
  { name: 'Santiago', lat: -33.45, lon: -70.67, tier: 2 },
  // Europe / Africa
  { name: 'London', lat: 51.51, lon: -0.13, tier: 1 },
  { name: 'Paris', lat: 48.86, lon: 2.35, tier: 1 },
  { name: 'Berlin', lat: 52.52, lon: 13.41, tier: 1 },
  { name: 'Madrid', lat: 40.42, lon: -3.7, tier: 2 },
  { name: 'Rome', lat: 41.9, lon: 12.5, tier: 2 },
  { name: 'Moscow', lat: 55.76, lon: 37.62, tier: 1 },
  { name: 'Istanbul', lat: 41.01, lon: 28.98, tier: 2 },
  { name: 'Cairo', lat: 30.04, lon: 31.24, tier: 1 },
  { name: 'Lagos', lat: 6.52, lon: 3.38, tier: 2 },
  { name: 'Johannesburg', lat: -26.2, lon: 28.05, tier: 2 },
  { name: 'Nairobi', lat: -1.29, lon: 36.82, tier: 2 },
  // Middle East / Asia
  { name: 'Dubai', lat: 25.2, lon: 55.27, tier: 2 },
  { name: 'Tehran', lat: 35.69, lon: 51.39, tier: 2 },
  { name: 'Mumbai', lat: 19.08, lon: 72.88, tier: 1 },
  { name: 'Delhi', lat: 28.61, lon: 77.21, tier: 1 },
  { name: 'Beijing', lat: 39.9, lon: 116.4, tier: 1 },
  { name: 'Shanghai', lat: 31.23, lon: 121.47, tier: 2 },
  { name: 'Tokyo', lat: 35.68, lon: 139.69, tier: 1 },
  { name: 'Seoul', lat: 37.57, lon: 126.98, tier: 1 },
  { name: 'Singapore', lat: 1.35, lon: 103.82, tier: 2 },
  { name: 'Jakarta', lat: -6.21, lon: 106.85, tier: 2 },
  { name: 'Bangkok', lat: 13.76, lon: 100.5, tier: 2 },
  { name: 'Hong Kong', lat: 22.32, lon: 114.17, tier: 2 },
  // Oceania
  { name: 'Sydney', lat: -33.87, lon: 151.21, tier: 1 },
  { name: 'Melbourne', lat: -37.81, lon: 144.96, tier: 2 },
  { name: 'Auckland', lat: -36.85, lon: 174.76, tier: 2 },
  // Polar / strategic
  { name: 'Anchorage', lat: 61.22, lon: -149.9, tier: 2 },
  { name: 'Reykjavík', lat: 64.15, lon: -21.94, tier: 2 },
]

/** Earth-fixed unit vector: Z = north, X = lon 0 (matches globe mesh after rotateX). */
export function latLonToUnit(latDeg: number, lonDeg: number): [number, number, number] {
  const lat = (latDeg * Math.PI) / 180
  const lon = (lonDeg * Math.PI) / 180
  const cl = Math.cos(lat)
  return [cl * Math.cos(lon), cl * Math.sin(lon), Math.sin(lat)]
}
