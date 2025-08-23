import { useState } from "react";
import { GoogleMap, LoadScript, Marker, DirectionsRenderer } from "@react-google-maps/api";

const containerStyle = {
  width: "100vw",
  height: "100vh",
};

const origin = { lat: 28.6139, lng: 77.2090 };
const destination = { lat: 28.6500, lng: 77.2300 };

const MapComponent: React.FC = () => {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  const [directions, setDirections] = useState<google.maps.DirectionsResult | null>(null);

  const handleMapLoad = (_map: google.maps.Map) => {
    const directionsService = new google.maps.DirectionsService();
    directionsService.route(
      {
        origin,
        destination,
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (result, status) => {
        if (status === "OK" && result) {
          setDirections(result);
        } else {
          console.error("Error fetching directions:", result);
        }
      }
    );
  };

  return (
    <LoadScript googleMapsApiKey={apiKey}>
      <GoogleMap
        mapContainerStyle={containerStyle}
        center={origin}
        zoom={12}
        onLoad={handleMapLoad} 
      >
        <Marker position={origin} />
        <Marker position={destination} />
        {directions && <DirectionsRenderer directions={directions} />}
      </GoogleMap>
    </LoadScript>
  );
};

export default MapComponent;
