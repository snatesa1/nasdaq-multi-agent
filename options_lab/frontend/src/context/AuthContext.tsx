'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { auth, googleProvider } from '@/lib/firebase';
import { onAuthStateChanged, signInWithPopup, signOut, User } from 'firebase/auth';

interface DemoUser {
  displayName: string;
  email: string;
  photoURL: string | null;
  uid: string;
  getIdToken: () => Promise<string>;
}

interface AuthContextType {
  user: User | DemoUser | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
}

const defaultDemoUser: DemoUser = {
  displayName: 'Sathish',
  email: 'sathish84@gmail.com',
  photoURL: null,
  uid: 'sathish-saxo-trader',
  getIdToken: async () => 'demo-id-token-12345',
};


const AuthContext = createContext<AuthContextType>({
  user: defaultDemoUser,
  loading: false,
  signInWithGoogle: async () => {},
  logout: async () => {},
  getIdToken: async () => 'demo-id-token-12345',
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | DemoUser | null>(defaultDemoUser);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    try {
      const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
        if (firebaseUser) {
          setUser(firebaseUser);
        } else {
          setUser(defaultDemoUser);
        }
        setLoading(false);
      });
      return () => unsubscribe();
    } catch (err) {
      console.warn('Firebase Auth initialization warning:', err);
      setUser(defaultDemoUser);
      setLoading(false);
    }
  }, []);

  const signInWithGoogle = async () => {
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      console.error('Google Sign-In failed, continuing as demo user:', err);
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
    } catch (err) {
      console.error('Logout error:', err);
    }
    setUser(defaultDemoUser);
  };

  const getIdToken = async (): Promise<string | null> => {
    if (user && 'getIdToken' in user) {
      return await user.getIdToken();
    }
    return 'demo-id-token-12345';
  };

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, logout, getIdToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
