import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold text-slate-900">404 — Not Found</h1>
      <Link to="/dashboard" className="text-sm text-blue-600 hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
