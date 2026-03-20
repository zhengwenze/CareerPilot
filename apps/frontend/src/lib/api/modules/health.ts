import { apiRequest } from "@/lib/api/client";

export type HealthStatus = {
  status: string;
};

export type ReadinessStatus = {
  status: string;
  database: string;
  redis: string;
};

export type VersionStatus = {
  name: string;
  version: string;
  environment: string;
};

export async function fetchHealthStatus(): Promise<HealthStatus> {
  return apiRequest<HealthStatus>("/health", {
    method: "GET",
  });
}

export async function fetchReadinessStatus(): Promise<ReadinessStatus> {
  return apiRequest<ReadinessStatus>("/health/readiness", {
    method: "GET",
  });
}

export async function fetchVersionStatus(): Promise<VersionStatus> {
  return apiRequest<VersionStatus>("/health/version", {
    method: "GET",
  });
}
