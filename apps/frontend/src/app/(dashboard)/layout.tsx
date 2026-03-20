import type { ReactNode } from "react";

import { ProtectedRoute } from "@/components/guards/protected-route";
import { DashboardTopNav } from "@/components/layout/dashboard-top-nav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-white text-black">
        <DashboardTopNav />

        <main className="py-0">
          <div className="mx-auto w-full max-w-6xl px-4 pb-8 pt-4 sm:px-6">
            {children}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
