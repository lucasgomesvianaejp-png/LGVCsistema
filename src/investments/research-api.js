import { doc, getDoc } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";

export async function fetchStocksDashboard(db, user) {
  if (!db || !user) throw new Error('Firebase indisponível ou usuário não autenticado');
  const snap = await getDoc(doc(db, 'researchDashboard', 'current'));
  if (!snap.exists()) throw new Error('Research ainda não foi inicializado no Firestore');
  const data = snap.data() || {};
  return { ...data, meta: { ...(data.meta || {}), databaseMode: true } };
}
