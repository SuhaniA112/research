import { SignUp } from "@clerk/clerk-react";
import { useNavigate } from "react-router-dom";

import { env } from "@/config/env";
import { CLERK_APPEARANCE } from "@/lib/clerkAppearance";
import { useAuthState } from "@/lib/auth";

export function SignUpPage() {
  const navigate = useNavigate();
  const { isSignedIn } = useAuthState();

  if (env.authMode === "mock") {
    return (
      <div className="w-full rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Sign up</h2>
        <p className="mt-2 text-sm text-slate-600">
          Local dev mode (VITE_AUTH_MODE=mock) — always signed in as a fixed dev user.
        </p>
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          disabled={!isSignedIn}
          className="mt-6 w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Continue
        </button>
      </div>
    );
  }

  return (
    <SignUp
      routing="path"
      path="/sign-up"
      signInUrl="/login"
      fallbackRedirectUrl="/dashboard"
      appearance={CLERK_APPEARANCE}
    />
  );
}
