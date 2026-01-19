import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { User } from 'firebase/auth';
import {
  subscribeToAuthChanges,
  signInWithGoogle,
  signInWithMicrosoft,
  signInWithApple,
  logout as firebaseLogout,
  getIdToken,
} from '@/services/firebase';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signInGoogle: () => Promise<void>;
  signInMicrosoft: () => Promise<void>;
  signInApple: () => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = subscribeToAuthChanges((user) => {
      setUser(user);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const signInGoogle = async () => {
    await signInWithGoogle();
  };

  const signInMicrosoft = async () => {
    await signInWithMicrosoft();
  };

  const signInApple = async () => {
    await signInWithApple();
  };

  const signOut = async () => {
    await firebaseLogout();
  };

  const getToken = getIdToken;

  return (
    <AuthContext.Provider value={{ user, loading, signInGoogle, signInMicrosoft, signInApple, signOut, getToken }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
