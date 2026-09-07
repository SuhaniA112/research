import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { env } from "@/config/env";
import { ensureCurrentUserId } from "@/lib/userContext";

export function ProtectedLayout() {
  useEffect(() => {
    if (env.useMocks) {
      void ensureCurrentUserId();
      return;
    }
    void ensureCurrentUserId().catch(() => {
      // Login page will reprovision; avoid blocking the shell.
    });
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
