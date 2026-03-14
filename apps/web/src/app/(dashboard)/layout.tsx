import type { ReactNode } from "react";
import { BellRing, ChevronRight } from "lucide-react";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { Badge } from "@/components/ui/badge";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.72),transparent_24%),radial-gradient(circle_at_top_right,rgba(20,184,166,0.18),transparent_24%),linear-gradient(180deg,rgba(255,252,247,0.98),rgba(244,236,221,0.94))]">
      <div className="flex min-h-screen">
        <AppSidebar />

        <div className="flex min-h-screen min-w-0 flex-1 flex-col md:pl-0">
          <header className="sticky top-0 z-10 border-b border-border/70 bg-background/75 backdrop-blur-xl">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-4 pl-16 md:px-8 md:pl-8">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>CareerPilot</span>
                  <ChevronRight className="size-4" />
                  <span>Dashboard</span>
                </div>
                <h1 className="text-lg font-semibold tracking-tight text-foreground md:text-2xl">
                  统一工作台壳层
                </h1>
              </div>

              <div className="flex items-center gap-3">
                <Badge className="hidden bg-primary/10 text-primary hover:bg-primary/10 sm:inline-flex">
                  Layout Ready
                </Badge>
                <div className="flex size-10 items-center justify-center rounded-2xl border border-border/70 bg-white/72 text-muted-foreground shadow-sm">
                  <BellRing className="size-4" />
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-5 md:px-8 md:py-8">
            <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
