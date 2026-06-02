import { initializeApp } from "firebase/app";
import {
  initializeFirestore,
  memoryLocalCache,
  collection,
  query,
  where,
  orderBy,
  getDocs,
  doc,
  getDoc,
  Timestamp
} from "firebase/firestore";
import {
  getAuth,
  signInWithEmailAndPassword,
  onAuthStateChanged
} from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyB-GPbCiXlXMDzlUDrWeW6p5oiTrWurReA",
  authDomain: "bread-basket-e2a59l.firebaseapp.com",
  projectId: "bread-basket-e2a59l",
  storageBucket: "bread-basket-e2a59l.appspot.com",
  messagingSenderId: "397515863695",
  appId: "1:397515863695:web:a6757d60cc964c12ffe2fa"
};

const appStart = performance.now();

const app = initializeApp(firebaseConfig);
const db = initializeFirestore(app, {
  localCache: memoryLocalCache()
});
const auth = getAuth(app);

const testEmail = "apptest@solarabread.ca";

document.body.innerHTML = `
  <h1>Firebase Safari Auth Benchmark</h1>

  <p>Email: <strong>${testEmail}</strong></p>

  <input
    id="password"
    type="password"
    placeholder="Password"
    style="padding: 8px; width: 260px;"
  />

  <button id="run">Sign In + Run Test</button>

  <pre id="output"></pre>
`;

function log(message) {
  document.getElementById("output").textContent += message + "\n";
}

function clearLog() {
  document.getElementById("output").textContent = "";
}

function elapsed() {
  return Math.round(performance.now() - appStart);
}

function startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return Timestamp.fromDate(d);
}

function todayIdString() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function bakesQuery() {
  return query(
    collection(db, "bakes"),
    where("bake_date", ">=", startOfToday()),
    orderBy("bake_date"),
    orderBy("order_date_time"),
    orderBy("product_name")
  );
}

async function time(label, fn) {
  const start = performance.now();

  try {
    const result = await fn();
    const ms = Math.round(performance.now() - start);
    log(`${label}: ${ms}ms`);
    log(JSON.stringify(result, null, 2));
    log("");
    return result;
  } catch (e) {
    const ms = Math.round(performance.now() - start);
    log(`${label}: ERROR after ${ms}ms`);
    log(e.message);
    log("");
    console.error(e);
    return null;
  }
}

function waitForAuthReady() {
  return new Promise((resolve) => {
    const unsub = onAuthStateChanged(auth, (user) => {
      unsub();
      resolve(user);
    });
  });
}

document.getElementById("run").addEventListener("click", async () => {
  clearLog();

  const password = document.getElementById("password").value;

  if (!password) {
    log("Enter the password first.");
    return;
  }

  log(`Page/app initialized at: ${elapsed()}ms`);
  log("");

  const user = await time("Auth sign-in", async () => {
    const cred = await signInWithEmailAndPassword(auth, testEmail, password);
    return {
      uid: cred.user.uid,
      email: cred.user.email
    };
  });

  if (!user?.uid) {
    return;
  }

  await time("Auth ready observer", async () => {
    const authUser = await waitForAuthReady();
    return {
      uid: authUser?.uid ?? null,
      email: authUser?.email ?? null
    };
  });

  await time("Bakes query 1", async () => {
    const snap = await getDocs(bakesQuery());
    return {
      count: snap.size
    };
  });

  const totalsDocId = `${user.uid}_${todayIdString()}`;

  await time("User daily order totals doc", async () => {
    const snap = await getDoc(doc(db, "user_daily_order_totals", totalsDocId));
    return {
      id: totalsDocId,
      exists: snap.exists(),
      size: snap.exists() ? JSON.stringify(snap.data()).length : 0
    };
  });

  await time("Bakes query 2 duplicate", async () => {
    const snap = await getDocs(bakesQuery());
    return {
      count: snap.size
    };
  });
});