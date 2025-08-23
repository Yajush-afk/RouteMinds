import { MapContainer, TileLayer, Marker, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useOSRMRoute } from "../hooks/useOSRMRoute";

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
  
  // Default to Delhi coordinates if no waypoints provided
  const defaultCenter: RoutePoint = [28.6139, 77.209];
  const mapCenter = waypoints.length > 0 ? waypoints[0] : defaultCenter;
  
  return (
    <div style={{ position: "relative", height: "100vh", width: "100%" }}>
      <MapContainer
        center={mapCenter}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        
        {/* Show markers for waypoints */}
        {waypoints.map((point, idx) => (
          <Marker key={idx} position={point} />
        ))}
        
        {/* Show route polyline if available */}
        {route && route.length > 0 && (
          <Polyline 
            positions={route} 
            pathOptions={{ color: "blue", weight: 4, opacity: 0.8 }} 
          />
        )}
      </MapContainer>
      
      {/* Optional loading overlay */}
      {loading && (
        <div style={{
          position: "absolute",
          top: 10,
          left: 10,
          background: "white",
          padding: "8px 12px",
          borderRadius: "4px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
          zIndex: 1000
        }}>
          Loading route...
        </div>
      )}
      
      {/* Optional status indicator */}
      {waypoints.length === 0 && (
        <div style={{
          position: "absolute",
          top: 10,
          left: 10,
          background: "white",
          padding: "8px 12px",
          borderRadius: "4px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
          zIndex: 1000
        }}>
          No waypoints - showing default location
        </div>
      )}
    </div>
  );
};

export default AIMap;