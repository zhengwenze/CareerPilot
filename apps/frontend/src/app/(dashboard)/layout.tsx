import type { ReactNode } from "react";

import { ProtectedRoute } from "@/components/guards/protected-route";
import { DashboardTopNav } from "@/components/layout/dashboard-top-nav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-white text-black">
        <DashboardTopNav />

        <main className="px-6 py-8 lg:px-10 lg:py-10">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-10">
            {children}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
