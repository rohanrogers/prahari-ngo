import { initializeApp, getApps } from "firebase/app";
import { getFirestore, collection, query, orderBy, limit, onSnapshot, doc, getDoc, getDocs, where } from "firebase/firestore";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "prahari-ngo-rj",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "",
};

// Initialize Firebase (singleton)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const db = getFirestore(app);

// ─── Collection References ───

export const volunteersCol = collection(db, "volunteers");
export const threatsCol = collection(db, "live_threats");
export const plansCol = collection(db, "response_plans");
export const activityCol = collection(db, "agent_activity");

// ─── Real-time Listeners ───

export function onAgentActivity(
  callback: (activities: any[]) => void,
  limitCount: number = 50
) {
  const q = query(activityCol, orderBy("timestamp", "desc"), limit(limitCount));
  return onSnapshot(q, (snapshot) => {
    const activities = snapshot.docs.map((doc) => ({
      id: doc.id,
      ...doc.data(),
    }));
    callback(activities);
  });
}

export function onActiveThreats(callback: (threats: any[]) => void) {
  const q = query(
    threatsCol,
    where("status", "in", ["monitoring", "pre_staged", "confirmed"]),
    orderBy("created_at", "desc")
  );
  return onSnapshot(q, (snapshot) => {
    const threats = snapshot.docs.map((doc) => ({
      id: doc.id,
      ...doc.data(),
    }));
    callback(threats);
  });
}

export function onVolunteers(callback: (volunteers: any[]) => void) {
  const q = query(volunteersCol, orderBy("created_at", "desc"), limit(200));
  return onSnapshot(q, (snapshot) => {
    const volunteers = snapshot.docs.map((doc) => ({
      id: doc.id,
      ...doc.data(),
    }));
    callback(volunteers);
  });
}

// ─── Fetchers ───

export async function getThreat(id: string) {
  const snap = await getDoc(doc(threatsCol, id));
  return snap.exists() ? { id: snap.id, ...snap.data() } : null;
}

export async function getPlan(threatId: string) {
  const q = query(plansCol, where("threat_id", "==", threatId));
  const snap = await getDocs(q);
  if (snap.empty) return null;
  return { id: snap.docs[0].id, ...snap.docs[0].data() };
}

export async function getVolunteerCount() {
  const snap = await getDocs(volunteersCol);
  return snap.size;
}

export { db };
