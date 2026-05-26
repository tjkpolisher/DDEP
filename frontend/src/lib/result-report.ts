import { z } from "zod";

import { diagnosisDomainSlugSchema } from "@/lib/domains";

export const domainReadinessSchema = z.enum(["strong", "developing", "weak", "unmeasured"]);

export const reportSnapshotSchema = z.object({
  generated_at: z.string(),
  algorithm_version: z.string(),
  status: z.enum(["active", "completed"]),
  answered_question_count: z.number(),
  average_domain_score: z.number(),
  weakest_domain: diagnosisDomainSlugSchema.nullable(),
  strongest_domain: diagnosisDomainSlugSchema.nullable(),
});

export const domainReportProfileSchema = z.object({
  domain: diagnosisDomainSlugSchema,
  score: z.number(),
  confidence: z.number(),
  evidence_weight: z.number(),
  attempted_questions: z.number(),
  readiness: domainReadinessSchema,
  uncertainty: z.string(),
  weak_concept_count: z.number(),
  weak_concept_tags: z.array(z.string()),
});

export const strengthWeaknessSummarySchema = z.object({
  strength_domains: z.array(diagnosisDomainSlugSchema),
  weakness_domains: z.array(diagnosisDomainSlugSchema),
  weak_concept_tags: z.array(z.string()),
  confidence_notes: z.array(z.string()),
});

export const roadmapItemSchema = z.object({
  order: z.number(),
  concept_slug: z.string(),
  domain: diagnosisDomainSlugSchema.nullable(),
  prerequisite_chain: z.array(z.string()),
  reason: z.string(),
  priority_score: z.number(),
});

export const retestTargetSchema = z.object({
  domain: diagnosisDomainSlugSchema,
  concept_slug: z.string().nullable(),
  reason: z.string(),
  priority: z.number(),
});

export const domainScoreDeltaSchema = z.object({
  domain: diagnosisDomainSlugSchema,
  previous_score: z.number(),
  current_score: z.number(),
  delta: z.number(),
  previous_confidence: z.number(),
  current_confidence: z.number(),
});

export const reportComparisonSchema = z.object({
  domain_deltas: z.array(domainScoreDeltaSchema),
  resolved_weak_concepts: z.array(z.string()),
  new_weak_concepts: z.array(z.string()),
});

export const resultReportSchema = z.object({
  snapshot: reportSnapshotSchema,
  domain_profiles: z.array(domainReportProfileSchema),
  strength_weakness: strengthWeaknessSummarySchema,
  roadmap: z.array(roadmapItemSchema),
  retest_targets: z.array(retestTargetSchema),
  comparison: reportComparisonSchema.nullable(),
});

export type DomainReadiness = z.infer<typeof domainReadinessSchema>;
export type ResultReport = z.infer<typeof resultReportSchema>;
