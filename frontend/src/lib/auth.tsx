import { ClerkProvider, useAuth as useClerkAuth } from "@clerk/clerk-react";
import { createContext, useContext, useEffect, type ReactNode } from "react";

import { env } from "@/config/env";

const MOCK_USER_ID = "mock-user-local-dev";

export interface AuthState {
  isLoaded: boolean;
  isSignedIn: boolean;
  userId: string | null;
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
}

const MOCK_AUTH_STATE: AuthState = {
  isLoaded: true,
  isSignedIn: true,
  userId: MOCK_USER_ID,
  getToken: async () => null,
  // Mock mode always presents a signed-in dev user — nothing to sign out of.
  signOut: async () => {},
};

const AuthStateContext = createContext<AuthState>(MOCK_AUTH_STATE);

// Mirrors the current auth state outside React, for the axios interceptor.
let latestAuthState: AuthState = MOCK_AUTH_STATE;

function ClerkAuthBridge({ children }: { children: ReactNode }) {
  const clerk = useClerkAuth();
  const state: AuthState = {
    isLoaded: clerk.isLoaded,
    isSignedIn: Boolean(clerk.isSignedIn),
    userId: clerk.userId ?? null,
    getToken: async () => clerk.getToken(),
    signOut: async () => {
      await clerk.signOut();
    },
  };

  useEffect(() => {
    latestAuthState = state;
  });

  return (
    <AuthStateContext.Provider value={state}>{children}</AuthStateContext.Provider>
  );
}

/** Wraps the app in real Clerk auth or a fixed local dev user, per VITE_AUTH_MODE. */
export function AppAuthProvider({ children }: { children: ReactNode }) {
  if (env.authMode === "mock") {
    latestAuthState = MOCK_AUTH_STATE;
    return (
      <AuthStateContext.Provider value={MOCK_AUTH_STATE}>
        {children}
      </AuthStateContext.Provider>
    );
  }

  return (
    <ClerkProvider publishableKey={env.clerkPublishableKey}>
      <ClerkAuthBridge>{children}</ClerkAuthBridge>
    </ClerkProvider>
  );
}

/** Auth state for components — works the same whether VITE_AUTH_MODE is mock or clerk. */
export function useAuthState(): AuthState {
  return useContext(AuthStateContext);
}

/** For non-component code (the axios interceptor) that can't call hooks. */
export async function getAuthToken(): Promise<string | null> {
  return latestAuthState.getToken();
}
