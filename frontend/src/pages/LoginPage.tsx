import { setAccessToken } from "@/lib/axios";
import { ensureCurrentUserId } from "@/lib/userContext";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

export function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleMockLogin() {
    setBusy(true);
    setError(null);
    try {
      // Temporary user row for project ownership (X-User-ID) until real auth.
      await ensureCurrentUserId();
      setAccessToken("mock-jwt-token");
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-900">Sign in</h2>
      <p className="mt-2 text-sm text-slate-600">
        Placeholder login — provisions a temporary user id for project scoping
        and sets a mock token for protected routing.
      </p>
      {error ? (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        onClick={() => {
          void handleMockLogin();
        }}
        disabled={busy}
        className="mt-6 w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
      >
        {busy ? "Continuing…" : "Continue"}
      </button>
    </div>
  );
}
