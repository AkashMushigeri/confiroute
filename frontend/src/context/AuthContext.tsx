import React, { createContext, useContext, useEffect, useState } from "react";
import type { AuthUser } from "../types";

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, pass: string, rememberMe: boolean) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  updateProfile: (updates: Partial<AuthUser>) => void;
  integrationNote: string;
}

const STORAGE_KEY = "confiroute_auth_session";

const DEFAULT_DEMO_USER: AuthUser = {
  id: "usr_clinical_942",
  name: "Dr. Sarah Chen",
  email: "clinician@confiroute.ai",
  role: "Lead Clinical Safety Reviewer",
  department: "Emergency Medicine & LLM Diagnostics",
  avatarUrl: "",
  sessionStartedAt: new Date().toISOString(),
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore authenticated session on mount if remembered
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as AuthUser;
        setUser(parsed);
      }
    } catch (e) {
      console.warn("Failed to restore session from storage:", e);
      localStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (
    email: string,
    pass: string,
    rememberMe: boolean
  ): Promise<{ success: boolean; error?: string }> => {
    // Basic validation
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !trimmedEmail.includes("@")) {
      return { success: false, error: "Please enter a valid clinical or institutional email address." };
    }
    if (!pass || pass.length < 5) {
      return { success: false, error: "Password must be at least 5 characters in length." };
    }

    // Simulate verification delay for natural tactile UX
    await new Promise((resolve) => setTimeout(resolve, 600));

    // Construct authenticated clinician user record
    const displayName =
      trimmedEmail === "clinician@confiroute.ai"
        ? DEFAULT_DEMO_USER.name
        : trimmedEmail
            .split("@")[0]
            .replace(/[._]/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase());

    const authenticatedUser: AuthUser = {
      id: `usr_${Math.random().toString(36).substring(2, 9)}`,
      name: displayName.startsWith("Dr.") ? displayName : `Dr. ${displayName}`,
      email: trimmedEmail,
      role: "Clinical Reviewer & AI Auditor",
      department: "Internal Medicine & Safety",
      sessionStartedAt: new Date().toISOString(),
    };

    setUser(authenticatedUser);

    try {
      const serialized = JSON.stringify(authenticatedUser);
      if (rememberMe) {
        localStorage.setItem(STORAGE_KEY, serialized);
        sessionStorage.removeItem(STORAGE_KEY);
      } else {
        sessionStorage.setItem(STORAGE_KEY, serialized);
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // storage unavailable
    }

    return { success: true };
  };

  const logout = () => {
    setUser(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  };

  const updateProfile = (updates: Partial<AuthUser>) => {
    if (!user) return;
    const updated = { ...user, ...updates };
    setUser(updated);
    try {
      const serialized = JSON.stringify(updated);
      if (localStorage.getItem(STORAGE_KEY)) {
        localStorage.setItem(STORAGE_KEY, serialized);
      } else {
        sessionStorage.setItem(STORAGE_KEY, serialized);
      }
    } catch {
      // ignore
    }
  };

  const integrationNote =
    "ConfiRoute Client Auth Layer: Ready for OAuth2/OIDC/JWT backend endpoint integration once an authentication provider service is mounted.";

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
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
