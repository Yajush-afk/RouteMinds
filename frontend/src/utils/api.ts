// api.ts
export async function getRouteEta({
  route_short_name,
  timestamp_iso,
  holiday_flag,
  token,
}: {
  route_short_name: string;
  timestamp_iso: string;
  holiday_flag: number;
  token: string;
}) {
  const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/eta`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ route_short_name, timestamp_iso, holiday_flag }),
  });

  if (!res.ok) {
    throw new Error(`Backend error: ${res.status}`);
  }

  return res.json();
}
