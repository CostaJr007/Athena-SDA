export type Threat = "HOSTILE" | "SUSPECT" | "ANOMALY" | "NOMINAL";

export type Track = {
  id: string;
  name: string;
  threat: Threat;
  alt: number;
  vel: number;
  ent: number;
  conf: number;
  country: string;
  cc: string;
  operator: string;
  launched: string;
  launchSite: string;
  vehicle: string;
  mass: string;
  inclination: number;
  period: number;
  apogee: number;
  perigee: number;
  lat: number;
  lon: number;
  purpose: string;
  mission: string;
  notes: string;
};

export const TRACKS: Track[] = [
  {
    id: "44231",
    name: "COSMOS-2542",
    threat: "HOSTILE",
    alt: 738,
    vel: 7.52,
    ent: 0.91,
    conf: 0.94,
    country: "RUS",
    cc: "ru",
    operator: "Russian Ministry of Defense (VKS)",
    launched: "2019-11-25",
    launchSite: "Plesetsk 43/4",
    vehicle: "Soyuz-2.1v / Volga",
    mass: "~500 kg (est.)",
    inclination: 97.9,
    period: 99.4,
    apogee: 861,
    perigee: 368,
    lat: 47.32,
    lon: 38.11,
    purpose: "SIGINT / Orbital inspection",
    mission:
      "Russian inspector satellite from the Napryazhenie series. Maneuvered repeatedly to synchronize with USA-245 (KH-11) in 2020, exhibiting non-cooperative rendezvous behavior.",
    notes:
      "Anomalous Δv maneuvers > 70 m/s logged. Ejected sub-satellite COSMOS-2543. HOSTILE classification due to shadowing pattern over Western assets.",
  },
  {
    id: "48274",
    name: "USA-311",
    threat: "SUSPECT",
    alt: 512,
    vel: 7.61,
    ent: 0.72,
    conf: 0.81,
    country: "USA",
    cc: "us",
    operator: "National Reconnaissance Office (NRO)",
    launched: "2021-06-15",
    launchSite: "Vandenberg SLC-8",
    vehicle: "Pegasus XL / Minotaur I",
    mass: "Classified",
    inclination: 98.2,
    period: 94.7,
    apogee: 528,
    perigee: 497,
    lat: -12.44,
    lon: -74.02,
    purpose: "Electro-optical reconnaissance (classified)",
    mission:
      "NROL-111 payload operated by the NRO. Sun-synchronous orbit typical of a strategic imaging platform with dawn/dusk passes over targets of interest.",
    notes:
      "Maneuver signature outside nominal envelope detected on 2026-07-14. Flagged SUSPECT until new TLE baseline.",
  },
  {
    id: "39227",
    name: "SHIYAN-7",
    threat: "SUSPECT",
    alt: 685,
    vel: 7.55,
    ent: 0.68,
    conf: 0.77,
    country: "CHN",
    cc: "cn",
    operator: "CASC / PLASSF",
    launched: "2013-07-19",
    launchSite: "Taiyuan LC-9",
    vehicle: "Long March 4C (CZ-4C)",
    mass: "~35 kg",
    inclination: 97.3,
    period: 98.1,
    apogee: 706,
    perigee: 654,
    lat: 31.20,
    lon: 121.47,
    purpose: "Technology demonstration / RPO",
    mission:
      "Chinese platform equipped with a robotic arm. Performed rendezvous & proximity operations (RPO) with SY-15 in 2013, one of the first orbital captures demonstrated outside the Western bloc.",
    notes:
      "Dual-use capability (potential co-orbital ASAT). Continuous Δv monitoring recommended.",
  },
  {
    id: "25544",
    name: "ISS (ZARYA)",
    threat: "NOMINAL",
    alt: 408,
    vel: 7.66,
    ent: 0.21,
    conf: 0.98,
    country: "INT",
    cc: "un",
    operator: "NASA · Roscosmos · ESA · JAXA · CSA",
    launched: "1998-11-20",
    launchSite: "Baikonur LC-81/23",
    vehicle: "Proton-K",
    mass: "~450,000 kg (complex)",
    inclination: 51.64,
    period: 92.9,
    apogee: 421,
    perigee: 415,
    lat: 5.12,
    lon: -142.88,
    purpose: "Crewed orbital laboratory",
    mission:
      "International Space Station. The Zarya module was the first element launched, providing propulsion, attitude control and initial power to the complex.",
    notes:
      "Cooperative traffic. 4 km × 4 km × 200 m keep-out zone around the complex (Pizza Box).",
  },
  {
    id: "43013",
    name: "NROL-42",
    threat: "ANOMALY",
    alt: 1103,
    vel: 7.31,
    ent: 0.55,
    conf: 0.72,
    country: "USA",
    cc: "us",
    operator: "National Reconnaissance Office (NRO)",
    launched: "2017-09-24",
    launchSite: "Vandenberg SLC-3E",
    vehicle: "Atlas V 541",
    mass: "~5,000 kg (est.)",
    inclination: 63.4,
    period: 717.8,
    apogee: 37600,
    perigee: 1108,
    lat: 41.03,
    lon: -101.55,
    purpose: "SIGINT — Molniya orbit",
    mission:
      "TRUMPET-FO SIGINT-class payload in a highly elliptical (HEO/Molniya) orbit for persistent coverage over high northern latitudes.",
    notes:
      "Orbital slot consistent with TRUMPET follow-on missions. Anomaly detected by Isolation Forest in secular drift of argument of perigee.",
  },
  {
    id: "02001",
    name: "COSMOS-482 DB",
    threat: "ANOMALY",
    alt: 210,
    vel: 7.83,
    ent: 0.63,
    conf: 0.69,
    country: "RUS",
    cc: "ru",
    operator: "USSR / Roscosmos (legacy)",
    launched: "1972-03-31",
    launchSite: "Baikonur LC-31/6",
    vehicle: "Molniya-M / 8K78M",
    mass: "~495 kg (descent capsule)",
    inclination: 51.98,
    period: 88.6,
    apogee: 267,
    perigee: 187,
    lat: -22.90,
    lon: 43.17,
    purpose: "Debris — failed Venera probe",
    mission:
      "Descent capsule from the Venera probe bound for Venus. Upper-stage failure left the vehicle in Earth orbit since 1972; reentry expected within the current window.",
    notes:
      "Hardened object (designed for the Venusian atmosphere) — non-zero probability of surviving reentry. ANOMALY category due to accelerated decay.",
  },
  {
    id: "58291",
    name: "STARLINK-30412",
    threat: "NOMINAL",
    alt: 550,
    vel: 7.59,
    ent: 0.14,
    conf: 0.99,
    country: "USA",
    cc: "us",
    operator: "SpaceX",
    launched: "2024-02-14",
    launchSite: "Cape Canaveral SLC-40",
    vehicle: "Falcon 9 Block 5",
    mass: "~800 kg",
    inclination: 53.2,
    period: 95.6,
    apogee: 555,
    perigee: 545,
    lat: 18.44,
    lon: -66.10,
    purpose: "Commercial LEO broadband",
    mission:
      "Starlink v2 mini constellation node. Provides broadband internet backhaul at ~30 ms latency via optical ISL between satellites.",
    notes:
      "Nominal behavior. Autonomous conjunction maneuvers via on-board COLA.",
  },
];

export const getTrack = (id: string) => TRACKS.find((t) => t.id === id);