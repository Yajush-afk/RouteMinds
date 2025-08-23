// frontend/src/utils/api.js
export async function checkBackend() {
  const res = await fetch("http://localhost:8000/ping");
  const data = await res.json();
  console.log(data); // should log { status: "Backend is working" }
}
