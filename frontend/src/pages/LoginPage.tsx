import { setAccessToken } from "@/lib/axios";
import { useNavigate } from "react-router-dom";

export function LoginPage() {
  const navigate = useNavigate();

  function handleMockLogin() {
    setAccessToken("mock-jwt-token");
    navigate("/dashboard");
  }

  return (
    <div className="w-full rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-900">Sign in</h2>
      <p className="mt-2 text-sm text-slate-600">
        Placeholder login — sets a mock token to demonstrate protected routing.
      </p>
      <button
        type="button"
        onClick={handleMockLogin}
        className="mt-6 w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
      >
        Continue
      </button>
    </div>
  );
}
