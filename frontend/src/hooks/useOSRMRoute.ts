import { useState, useEffect } from "react";

export const useOSRMRoute = (waypoints: [number, number][]) => {
  const [route, setRoute] = useState<[number, number][]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!waypoints || waypoints.length < 2) {
      setRoute([]);
      setLoading(false);
      return;
    }

    setLoading(true);

    const coords = waypoints.map(([lat, lng]) => `${lng},${lat}`).join(";");

    const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`;

    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (data.routes && data.routes.length > 0) {
          const routeCoords = data.routes[0].geometry.coordinates.map(
            ([lng, lat]: number[]) => [lat, lng] as [number, number]
          );
          setRoute(routeCoords);
        } else {
          console.error("No routes found", data);
          setRoute([]);
        }
      })
      .catch((err) => {
        console.error("OSRM fetch error:", err);
        setRoute([]);
      })
      .finally(() => setLoading(false));
  }, [waypoints]);

  return { route, loading };
};
