import { Outlet } from "react-router-dom";

export function OnboardingLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto min-h-screen max-w-3xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
}
