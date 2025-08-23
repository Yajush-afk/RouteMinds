export async function getRouteEta(params: {
  route_short_name: string;
  timestamp_iso: string;
  holiday_flag: number;
  token: string;
  from_stop_id?: number;
  to_stop_id?: number;
  from_coord?: [number, number];
  to_coord?: [number, number];
}) {
  if (!params.token) throw new Error("No token provided");

  const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/eta`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.token}`,
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    throw new Error(`Backend error: ${res.status}`);
  }

  return res.json();
}
