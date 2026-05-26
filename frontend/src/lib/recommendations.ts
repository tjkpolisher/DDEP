import { z } from "zod";

export const resourceSourceTypeSchema = z.enum([
  "official_docs",
  "open_course",
  "paper",
  "technical_blog",
  "community_reference",
]);

export const resourceDifficultySchema = z.enum(["intro", "intermediate", "advanced"]);

export const scoreBreakdownSchema = z.object({
  trust: z.number(),
  level_fit: z.number(),
  freshness: z.number(),
  practice: z.number(),
  dedupe: z.number(),
  total: z.number(),
});

export const learningRecommendationSchema = z.object({
  title: z.string(),
  url: z.string().url(),
  source_name: z.string(),
  source_type: resourceSourceTypeSchema,
  difficulty: resourceDifficultySchema,
  trust_score: z.number(),
  recommendation_reason: z.string(),
  prerequisite_tags: z.array(z.string()),
  concept_tags: z.array(z.string()),
  score: scoreBreakdownSchema,
});

export const recommendationRunSchema = z.object({
  query_terms: z.array(z.string()),
  recommendations: z.array(learningRecommendationSchema),
  fallback_reasons: z.array(
    z.enum([
      "insufficient_verified_results",
      "low_trust_results_filtered",
      "no_direct_concept_match",
    ]),
  ),
  candidate_count: z.number(),
  verified_candidate_count: z.number(),
});

export type RecommendationRun = z.infer<typeof recommendationRunSchema>;
