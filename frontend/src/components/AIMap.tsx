// src/pages/AIMap.tsx
import { MapContainer, TileLayer, Marker, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useOSRMRoute } from "../hooks/useOSRMRoute"; // adjust path

// Fix default Leaflet markers
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

export type RoutePoint = [number, number];

interface AIMapProps {
  waypoints: RoutePoint[];
  zoom?: number;
}

const AIMap: React.FC<AIMapProps> = ({ waypoints, zoom = 12 }) => {
  const { route, loading } = useOSRMRoute(waypoints);

  if (loading) return <div>Loading route...</div>;
  if (!route || route.length === 0) return <div>No route found</div>;

  return (
    <MapContainer
      center={waypoints[0]}
      zoom={zoom}
      style={{ height: "100vh", width: "100vw" }}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {/* Markers for all waypoints */}
      {waypoints.map((point, idx) => (
        <Marker key={idx} position={point} />
      ))}

      {/* Polyline following roads */}
      <Polyline
        positions={route}
        pathOptions={{ color: "blue", weight: 4, opacity: 0.8 }}
      />
    </MapContainer>
  );
};

export default AIMap;
