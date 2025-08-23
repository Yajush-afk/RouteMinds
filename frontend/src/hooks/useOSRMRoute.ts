import { useState, useEffect } from "react";

// Hook to fetch a route from OSRM
export const useOSRMRoute = (waypoints: [number, number][]) => {
  const [route, setRoute] = useState<[number, number][]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (waypoints.length < 2) return;

    // OSRM expects coordinates as lng,lat
    const coords = waypoints.map(([lat, lng]) => `${lng},${lat}`).join(";");

    const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data.routes && data.routes.length > 0) {
          // Convert back to [lat, lng] for Leaflet
          const routeCoords = data.routes[0].geometry.coordinates.map(
            ([lng, lat]: number[]) => [lat, lng] as [number, number]
          );
          setRoute(routeCoords);
        } else {
          console.error("No routes found", data);
        }
      })
      .catch(err => console.error("OSRM fetch error:", err))
      .finally(() => setLoading(false));
  }, [waypoints]);

  return { route, loading };
};
