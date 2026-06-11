import { Outlet } from "react-router-dom";

import { env } from "@/config/env";

export function ProtectedLayout() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-slate-200 px-6 py-4">
        <h1 className="text-lg font-semibold text-slate-900">{env.appName}</h1>
      </header>
      <main className="mx-auto max-w-5xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
