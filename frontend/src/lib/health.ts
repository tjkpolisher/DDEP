import { z } from "zod";
import { domainDefinitionSchema } from "@/lib/domains";

export const healthResponseSchema = z.object({
  status: z.literal("ok"),
  service: z.string(),
  environment: z.string(),
  domains: z.array(domainDefinitionSchema),
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/health`, {
    signal,
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with ${response.status}`);
  }

  return healthResponseSchema.parse(await response.json());
}
