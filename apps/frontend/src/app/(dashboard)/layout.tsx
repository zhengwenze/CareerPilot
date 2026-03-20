import type { ReactNode } from "react";

import { ProtectedRoute } from "@/components/guards/protected-route";
import { DashboardTopNav } from "@/components/layout/dashboard-top-nav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background text-foreground">
        <div className="min-h-screen bg-[#F9F8F6]/50">
          <DashboardTopNav />

          <main className="py-6 sm:py-8 lg:py-12">
            <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}