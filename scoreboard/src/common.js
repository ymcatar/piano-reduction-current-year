export async function fetchJSON(...args) {
  const res = await fetch(...args);
  if (!res.ok) throw new Error('Response not ok');
  return await res.json();
}
