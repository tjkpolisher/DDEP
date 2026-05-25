import { z } from "zod";

export const diagnosisDomainSlugSchema = z.enum([
  "airframe_aerodynamics",
  "electronics_hardware",
  "control",
  "software",
  "autonomous_ai",
  "fabrication_operations",
]);

export type DiagnosisDomainSlug = z.infer<typeof diagnosisDomainSlugSchema>;

export const domainDefinitionSchema = z.object({
  slug: diagnosisDomainSlugSchema,
  label: z.string(),
  summary: z.string(),
});

export type DomainDefinition = z.infer<typeof domainDefinitionSchema>;

export const diagnosisDomains: readonly DomainDefinition[] = [
  {
    slug: "airframe_aerodynamics",
    label: "기체/공력",
    summary: "프레임, 추진계, 비행 성능, 공력 기본 개념",
  },
  {
    slug: "electronics_hardware",
    label: "전장/하드웨어",
    summary: "전원, 센서, 통신, 임베디드 하드웨어 구성",
  },
  {
    slug: "control",
    label: "제어",
    summary: "동역학, 안정화, 제어기 튜닝, 상태 추정",
  },
  {
    slug: "software",
    label: "소프트웨어",
    summary: "펌웨어, 지상국, 데이터 파이프라인, 개발 도구",
  },
  {
    slug: "autonomous_ai",
    label: "자율비행/AI",
    summary: "경로 계획, 인지, SLAM, 임무 자동화",
  },
  {
    slug: "fabrication_operations",
    label: "제작/운용",
    summary: "조립, 정비, 안전 점검, 시험 비행 운용",
  },
] as const;
