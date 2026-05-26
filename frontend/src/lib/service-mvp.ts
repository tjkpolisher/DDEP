import { z } from "zod";

import { diagnosisDomainSlugSchema } from "@/lib/domains";
import { recommendationRunSchema } from "@/lib/recommendations";
import { resultReportSchema } from "@/lib/result-report";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const accessVerifyResponseSchema = z.object({
  token: z.string(),
  token_type: z.literal("bearer"),
  expires_at: z.string(),
  user: z.object({
    id: z.number(),
    display_name: z.string(),
    email: z.string().nullable(),
    is_operator: z.boolean(),
  }),
});

export const diagnosisQuestionSchema = z.object({
  external_id: z.string(),
  domain: diagnosisDomainSlugSchema,
  difficulty: z.enum(["easy", "medium", "hard"]),
  answer_type: z.enum(["single_choice", "multi_select", "short_answer"]),
  prompt: z.string(),
  choices: z.array(z.object({ key: z.string(), text: z.string() })),
  concept_tags: z.array(z.string()),
  prerequisite_tags: z.array(z.string()),
});

export const diagnosisSessionSchema = z.object({
  id: z.string(),
  status: z.enum(["active", "completed"]),
  answered_question_count: z.number(),
  question_count: z.number(),
  questions: z.array(diagnosisQuestionSchema),
  created_at: z.string(),
  completed_at: z.string().nullable(),
});

export const completeDiagnosisResponseSchema = z.object({
  diagnosis: diagnosisSessionSchema,
  report: resultReportSchema,
  recommendations: recommendationRunSchema,
});

export type AccessVerifyResponse = z.infer<typeof accessVerifyResponseSchema>;
export type CompleteDiagnosisResponse = z.infer<typeof completeDiagnosisResponseSchema>;
export type DiagnosisQuestion = z.infer<typeof diagnosisQuestionSchema>;
export type DiagnosisSession = z.infer<typeof diagnosisSessionSchema>;

export async function verifyAccess(input: {
  invite_code: string;
  display_name: string;
  email?: string;
}): Promise<AccessVerifyResponse> {
  const response = await apiFetch("/access/verify", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return accessVerifyResponseSchema.parse(await response.json());
}

export async function createDiagnosis(token: string): Promise<DiagnosisSession> {
  const response = await apiFetch("/diagnoses", { method: "POST", token });
  return diagnosisSessionSchema.parse(await response.json());
}

export async function saveAnswer(input: {
  token: string;
  diagnosisId: string;
  questionExternalId: string;
  choiceKeys?: string[];
  shortAnswer?: string;
}): Promise<void> {
  await apiFetch(`/diagnoses/${input.diagnosisId}/answers`, {
    method: "POST",
    token: input.token,
    body: JSON.stringify({
      question_external_id: input.questionExternalId,
      choice_keys: input.choiceKeys ?? [],
      short_answer: input.shortAnswer,
    }),
  });
}

export async function completeDiagnosis(
  token: string,
  diagnosisId: string,
): Promise<CompleteDiagnosisResponse> {
  const response = await apiFetch(`/diagnoses/${diagnosisId}/complete`, {
    method: "POST",
    token,
  });
  return completeDiagnosisResponseSchema.parse(await response.json());
}

async function apiFetch(
  path: string,
  init: RequestInit & { token?: string } = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (init.token) {
    headers.set("Authorization", `Bearer ${init.token}`);
  }
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response;
}
