"use client";

import { useEffect, useRef } from "react";

interface Stop {
  name: string;
  lat: number | null;
  lng: number | null;
}

interface MapViewProps {
  stops: Stop[];
  city: string;
}

export default function MapView({ stops, city }: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const validStops = stops.filter((s) => s.lat && s.lng);
    if (validStops.length === 0) return;

    import("leaflet").then((L) => {
      // Fix broken icon paths in Next.js
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
      });

      const map = L.map(mapRef.current!);
      mapInstanceRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      // Numbered pins
      validStops.forEach((stop, i) => {
        const icon = L.divIcon({
          html: `<div style="background:#E8445A;color:white;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;border:2.5px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.25);font-family:sans-serif">${i + 1}</div>`,
          className: "",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
          popupAnchor: [0, -18],
        });

        L.marker([stop.lat!, stop.lng!], { icon })
          .bindPopup(`<b style="font-size:13px">${stop.name}</b>`)
          .addTo(map);
      });

      // Dotted route line
      const latlngs = validStops.map((s) => [s.lat!, s.lng!] as [number, number]);
      L.polyline(latlngs, {
        color: "#E8445A",
        weight: 2.5,
        dashArray: "7 6",
        opacity: 0.7,
      }).addTo(map);

      // Auto-zoom to fit all pins
      map.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40] });

      // Fix tile misalignment caused by container not having final size at init
      setTimeout(() => map.invalidateSize(), 100);
    });

    return () => {
      if (mapInstanceRef.current) {
        (mapInstanceRef.current as { remove: () => void }).remove();
        mapInstanceRef.current = null;
      }
    };
  }, [stops, city]);

  return <div ref={mapRef} style={{ height: "100%", width: "100%" }} />;
}

export function buildGoogleMapsUrl(stops: Stop[], city: string): string {
  const valid = stops.filter((s) => s.lat && s.lng);
  if (valid.length === 0) return "#";
  const waypoints = valid
    .map((s) => encodeURIComponent(`${s.name} ${city}`))
    .join("/");
  return `https://www.google.com/maps/dir/${waypoints}`;
}
