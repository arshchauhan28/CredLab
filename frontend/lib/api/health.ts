import { apiRequest } from "./client";

export interface HealthResponse {
  status: string;
}

export function checkApiHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/api/health");
}