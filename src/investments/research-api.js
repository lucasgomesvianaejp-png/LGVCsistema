async function authHeaders(user) {
  if (!user?.getIdToken) throw new Error('Usuário não autenticado');
  const token = await user.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

export async function fetchStocksDashboard(user) {
  const response = await fetch('/api/research/stocks', {
    method: 'GET',
    headers: await authHeaders(user),
    cache: 'no-store'
  });
  if (!response.ok) {
    let message = `Research API ${response.status}`;
    try { message = (await response.json()).error || message; } catch {}
    throw new Error(message);
  }
  return response.json();
}
