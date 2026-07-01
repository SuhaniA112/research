import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";

export function ProtectedLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
