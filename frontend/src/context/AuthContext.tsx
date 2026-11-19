import React, { createContext, useContext, useEffect, useState } from "react";
import type { AuthUser } from "../types";
import { api, getAuthToken, clearAuthToken } from "../lib/api";

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, pass: string, rememberMe: boolean) => Promise<{ success: boolean; error?: string }>;
  register: (name: string, email: string, pass: string, role?: string, department?: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  updateProfile: (updates: Partial<AuthUser>) => void;
  integrationNote: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Validate server-side session token on mount
  useEffect(() => {
    let isMounted = true;
    const token = getAuthToken();

    if (!token) {
      setIsLoading(false);
      return;
    }

    api.getMe()
      .then((serverUser) => {
        if (isMounted) {
          setUser(serverUser);
        }
      })
      .catch((err) => {
        console.warn("Session token validation failed against backend:", err);
        clearAuthToken();
        if (isMounted) {
          setUser(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (
    email: string,
    pass: string,
    rememberMe: boolean
  ): Promise<{ success: boolean; error?: string }> => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !trimmedEmail.includes("@")) {
      return { success: false, error: "Please enter a valid clinical or institutional email address." };
    }
    if (!pass || pass.length < 4) {
      return { success: false, error: "Password must be at least 4 characters in length." };
    }

    try {
      const res = await api.login(trimmedEmail, pass, rememberMe);
      setUser(res.user);
      return { success: true };
    } catch (err: any) {
      return {
        success: false,
        error: err.message || "Authentication failed. Check your email and password.",
      };
    }
  };

  const register = async (
    name: string,
    email: string,
    pass: string,
    role = "reviewer",
    department = "Clinical Review"
  ): Promise<{ success: boolean; error?: string }> => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !trimmedEmail.includes("@")) {
      return { success: false, error: "Please enter a valid clinical or institutional email address." };
    }
    if (!name.trim()) {
      return { success: false, error: "Please enter your full name or clinical title." };
    }
    if (!pass || pass.length < 6) {
      return { success: false, error: "Password must be at least 6 characters in length." };
    }

    try {
      const res = await api.register(trimmedEmail, pass, name.trim(), role, department.trim());
      setUser(res.user);
      return { success: true };
    } catch (err: any) {
      return {
        success: false,
        error: err.message || "Registration failed. This email may already be in use.",
      };
    }
  };

  const logout = () => {
    api.logout().finally(() => {
      setUser(null);
    });
  };

  const updateProfile = (updates: Partial<AuthUser>) => {
    if (!user) return;
    setUser({ ...user, ...updates });
  };

  const integrationNote =
    "ConfiRoute Production Auth: Connected directly to SQLite authentication and session verification.";

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        updateProfile,
        integrationNote,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};


export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
