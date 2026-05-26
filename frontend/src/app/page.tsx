"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Gauge,
  RefreshCw,
  Route,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/status-pill";
import { diagnosisDomains } from "@/lib/domains";
import { fetchHealth, type HealthResponse } from "@/lib/health";
import { resultReportSchema, type DomainReadiness, type ResultReport } from "@/lib/result-report";

type ApiState =
  | { status: "checking"; data: null; message: string }
  | { status: "online"; data: HealthResponse; message: string }
  | { status: "offline"; data: null; message: string };

const domainLabel = new Map(diagnosisDomains.map((domain) => [domain.slug, domain.label]));

const demoReport = resultReportSchema.parse({
  snapshot: {
    generated_at: "2026-05-26T00:00:00Z",
    algorithm_version: "bayes-lite-v1",
    status: "completed",
    answered_question_count: 18,
    average_domain_score: 64,
    weakest_domain: "control",
    strongest_domain: "software",
  },
  domain_profiles: [
    {
      domain: "airframe_aerodynamics",
      score: 66,
      confidence: 0.72,
      evidence_weight: 2.4,
      attempted_questions: 3,
      readiness: "developing",
      uncertainty: "추가 문항으로 신뢰도를 높일 수 있습니다",
      weak_concept_count: 0,
      weak_concept_tags: [],
    },
    {
      domain: "electronics_hardware",
      score: 61,
      confidence: 0.64,
      evidence_weight: 2,
      attempted_questions: 3,
      readiness: "developing",
      uncertainty: "추가 문항으로 신뢰도를 높일 수 있습니다",
      weak_concept_count: 1,
      weak_concept_tags: ["power_distribution"],
    },
    {
      domain: "control",
      score: 44,
      confidence: 0.8,
      evidence_weight: 3,
      attempted_questions: 4,
      readiness: "weak",
      uncertainty: "현재 근거 기준 신뢰도가 높습니다",
      weak_concept_count: 2,
      weak_concept_tags: ["pid", "attitude_control"],
    },
    {
      domain: "software",
      score: 81,
      confidence: 0.86,
      evidence_weight: 3.2,
      attempted_questions: 4,
      readiness: "strong",
      uncertainty: "현재 근거 기준 신뢰도가 높습니다",
      weak_concept_count: 0,
      weak_concept_tags: [],
    },
    {
      domain: "autonomous_ai",
      score: 58,
      confidence: 0.48,
      evidence_weight: 1.5,
      attempted_questions: 2,
      readiness: "weak",
      uncertainty: "근거 문항이 적어 불확실성이 높습니다",
      weak_concept_count: 1,
      weak_concept_tags: ["sensor_fusion"],
    },
    {
      domain: "fabrication_operations",
      score: 72,
      confidence: 0.72,
      evidence_weight: 2.4,
      attempted_questions: 3,
      readiness: "developing",
      uncertainty: "추가 문항으로 신뢰도를 높일 수 있습니다",
      weak_concept_count: 0,
      weak_concept_tags: [],
    },
  ],
  strength_weakness: {
    strength_domains: ["software"],
    weakness_domains: ["control", "autonomous_ai", "electronics_hardware"],
    weak_concept_tags: ["power_distribution", "pid", "attitude_control", "sensor_fusion"],
    confidence_notes: [
      "electronics_hardware: 추가 문항으로 신뢰도를 높일 수 있습니다",
      "autonomous_ai: 근거 문항이 적어 불확실성이 높습니다",
    ],
  },
  roadmap: [
    {
      order: 1,
      concept_slug: "imu",
      domain: null,
      prerequisite_chain: [],
      reason: "attitude_control 학습 전 선행 개념",
      priority_score: 76,
    },
    {
      order: 2,
      concept_slug: "sensor_fusion",
      domain: "autonomous_ai",
      prerequisite_chain: ["imu"],
      reason: "진단에서 취약 개념으로 확인됨",
      priority_score: 42,
    },
    {
      order: 3,
      concept_slug: "pid",
      domain: "control",
      prerequisite_chain: [],
      reason: "진단에서 취약 개념으로 확인됨",
      priority_score: 56,
    },
    {
      order: 4,
      concept_slug: "attitude_control",
      domain: "control",
      prerequisite_chain: ["imu", "sensor_fusion"],
      reason: "진단에서 취약 개념으로 확인됨",
      priority_score: 56,
    },
  ],
  retest_targets: [
    {
      domain: "control",
      concept_slug: "attitude_control",
      reason: "취약 개념 보강 후 재진단",
      priority: 1,
    },
    {
      domain: "autonomous_ai",
      concept_slug: "sensor_fusion",
      reason: "취약 개념 보강 후 재진단",
      priority: 2,
    },
  ],
  comparison: {
    domain_deltas: [
      {
        domain: "control",
        previous_score: 38,
        current_score: 44,
        delta: 6,
        previous_confidence: 0.7,
        current_confidence: 0.8,
      },
    ],
    resolved_weak_concepts: ["mavlink"],
    new_weak_concepts: ["sensor_fusion"],
  },
});

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>({
    status: "checking",
    data: null,
    message: "API 상태 확인 중",
  });

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((data) => {
        setApiState({
          status: "online",
          data,
          message: `${data.service} · ${data.environment}`,
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setApiState({
          status: "offline",
          data: null,
          message: error instanceof Error ? error.message : "API 응답을 확인할 수 없음",
        });
      });

    return () => controller.abort();
  }, []);

  const report = demoReport;
  const weakDomainLabels = useMemo(
    () =>
      report.strength_weakness.weakness_domains
        .map((domain) => domainLabel.get(domain) ?? domain)
        .join(", "),
    [report],
  );

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-[#172033]">
      <section className="border-b border-[#d8dee9] bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-[#087f83]">DDEP 내부 진단 리포트</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-normal sm:text-3xl">
              취약 개념과 다음 학습 순서
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-[#d8dee9] bg-[#f7f8fb] px-4 py-3">
            <StatusPill status={apiState.status} />
            <span className="text-sm text-[#536173]">{apiState.message}</span>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-5 px-5 py-6 sm:px-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-5">
          <ReportSummary report={report} weakDomainLabels={weakDomainLabels} />
          <DomainGrid report={report} />
          <Roadmap report={report} />
        </div>
        <aside className="space-y-5">
          <WeakTags report={report} />
          <RetestTargets report={report} />
          <Comparison report={report} />
        </aside>
      </section>
    </main>
  );
}

function ReportSummary({
  report,
  weakDomainLabels,
}: {
  report: ResultReport;
  weakDomainLabels: string;
}) {
  return (
    <section className="grid gap-4 rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm md:grid-cols-3">
      <Metric
        icon={Gauge}
        label="평균"
        value={`${report.snapshot.average_domain_score}`}
        detail={`${report.snapshot.answered_question_count}문항 기준`}
      />
      <Metric
        icon={AlertTriangle}
        label="우선 보강"
        value={domainLabel.get(report.snapshot.weakest_domain ?? "control") ?? "-"}
        detail={weakDomainLabels || "취약 도메인 없음"}
      />
      <Metric
        icon={CheckCircle2}
        label="강점"
        value={domainLabel.get(report.snapshot.strongest_domain ?? "software") ?? "-"}
        detail={`${report.strength_weakness.strength_domains.length}개 도메인`}
      />
    </section>
  );
}

function DomainGrid({ report }: { report: ResultReport }) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {report.domain_profiles.map((profile) => (
        <article
          key={profile.domain}
          className="min-h-52 rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold tracking-normal">
                {domainLabel.get(profile.domain)}
              </h2>
              <p className="mt-1 text-sm text-[#536173]">{readinessLabel(profile.readiness)}</p>
            </div>
            <span className={scoreClass(profile.score)}>{profile.score}</span>
          </div>
          <div className="mt-5 h-2 rounded-full bg-[#e8edf3]">
            <div
              className="h-2 rounded-full bg-[#087f83]"
              style={{ width: `${profile.score}%` }}
            />
          </div>
          <p className="mt-4 text-sm leading-6 text-[#536173]">{profile.uncertainty}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {profile.weak_concept_tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md border border-[#f3c2a1] bg-[#fff4ec] px-2 py-1 font-mono text-xs text-[#994b12]"
              >
                {tag}
              </span>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

function Roadmap({ report }: { report: ResultReport }) {
  return (
    <section className="rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Route aria-hidden="true" size={19} className="text-[#087f83]" />
        <h2 className="text-lg font-semibold tracking-normal">학습 로드맵</h2>
      </div>
      <div className="grid gap-3">
        {report.roadmap.map((item) => (
          <div
            key={`${item.order}-${item.concept_slug}`}
            className="grid gap-3 rounded-md border border-[#e1e7ef] p-4 sm:grid-cols-[2.5rem_minmax(0,1fr)]"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#e5f4f3] font-semibold text-[#087f83]">
              {item.order}
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-mono text-sm font-semibold text-[#172033]">
                  {item.concept_slug}
                </h3>
                {item.domain ? (
                  <span className="text-xs text-[#536173]">{domainLabel.get(item.domain)}</span>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-[#536173]">{item.reason}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function WeakTags({ report }: { report: ResultReport }) {
  return (
    <section className="rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <ClipboardList aria-hidden="true" size={19} className="text-[#b55319]" />
        <h2 className="text-base font-semibold tracking-normal">취약 concept tag</h2>
      </div>
      <div className="flex flex-wrap gap-2">
        {report.strength_weakness.weak_concept_tags.map((tag) => (
          <span
            key={tag}
            className="rounded-md border border-[#f3c2a1] bg-[#fff4ec] px-2 py-1 font-mono text-xs text-[#994b12]"
          >
            {tag}
          </span>
        ))}
      </div>
      <div className="mt-4 space-y-2">
        {report.strength_weakness.confidence_notes.map((note) => (
          <p key={note} className="text-sm leading-6 text-[#536173]">
            {note}
          </p>
        ))}
      </div>
    </section>
  );
}

function RetestTargets({ report }: { report: ResultReport }) {
  return (
    <section className="rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <RefreshCw aria-hidden="true" size={18} className="text-[#087f83]" />
        <h2 className="text-base font-semibold tracking-normal">재진단 대상</h2>
      </div>
      <div className="space-y-3">
        {report.retest_targets.map((target) => (
          <div key={`${target.priority}-${target.domain}`} className="border-t border-[#e1e7ef] pt-3">
            <p className="font-semibold">{domainLabel.get(target.domain)}</p>
            <p className="mt-1 font-mono text-xs text-[#536173]">{target.concept_slug}</p>
            <p className="mt-2 text-sm text-[#536173]">{target.reason}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Comparison({ report }: { report: ResultReport }) {
  if (!report.comparison) {
    return null;
  }
  return (
    <section className="rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold tracking-normal">이전 진단 비교</h2>
      <div className="mt-4 space-y-3">
        {report.comparison.domain_deltas.map((delta) => (
          <div key={delta.domain} className="flex items-center justify-between gap-3">
            <span className="text-sm text-[#536173]">{domainLabel.get(delta.domain)}</span>
            <span className="font-mono text-sm font-semibold text-[#087f83]">
              {delta.delta > 0 ? "+" : ""}
              {delta.delta}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="min-h-28 rounded-md border border-[#e1e7ef] p-4">
      <div className="flex items-center gap-2 text-sm text-[#536173]">
        <Icon aria-hidden="true" size={17} />
        {label}
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-normal">{value}</p>
      <p className="mt-1 text-sm text-[#536173]">{detail}</p>
    </div>
  );
}

function readinessLabel(readiness: DomainReadiness) {
  const labels: Record<DomainReadiness, string> = {
    strong: "강점",
    developing: "보강 중",
    weak: "우선 학습",
    unmeasured: "근거 부족",
  };
  return labels[readiness];
}

function scoreClass(score: number) {
  const base = "rounded-md px-3 py-1 font-mono text-lg font-semibold";
  if (score >= 75) {
    return `${base} bg-[#e5f4f3] text-[#087f83]`;
  }
  if (score >= 60) {
    return `${base} bg-[#edf2f7] text-[#334155]`;
  }
  return `${base} bg-[#fff4ec] text-[#994b12]`;
}
