"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth-provider";

const DASHBOARD_ENTRY_PATH = "/dashboard/overview";
const LOGIN_PATH = "/login";

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isBootstrapping } = useAuth();

  useEffect(() => {
    if (isBootstrapping) {
      return;
    }

    router.replace(isAuthenticated ? DASHBOARD_ENTRY_PATH : LOGIN_PATH);
  }, [isAuthenticated, isBootstrapping, router]);

  return null;
}
