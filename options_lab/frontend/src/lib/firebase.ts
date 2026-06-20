import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyBE9Fjp0ACGViB6PXbxLQZEypIMimp85_E",
  authDomain: "optimal-aurora-495912-n0.firebaseapp.com",
  projectId: "optimal-aurora-495912-n0",
  storageBucket: "optimal-aurora-495912-n0.firebasestorage.app",
  messagingSenderId: "855694839217",
  appId: "1:855694839217:web:afdff6034d852711a04190"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
