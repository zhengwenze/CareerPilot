import type { Metadata } from "next";

import { AuthPage } from "@/components/auth-page";

export const metadata: Metadata = {
  title: "注册 | CareerPilot",
};

export default function RegisterPage() {
  return <AuthPage mode="register" />;
}
