import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto flex min-h-screen max-w-lg items-center justify-center p-6">
        <Outlet />
      </main>
    </div>
  );
}
