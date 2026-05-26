"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Gauge,
  RefreshCw,
  ShieldCheck,
  Route,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/status-pill";
import { diagnosisDomains } from "@/lib/domains";
import { fetchHealth, type HealthResponse } from "@/lib/health";
import { recommendationRunSchema, type RecommendationRun } from "@/lib/recommendations";
import { resultReportSchema, type DomainReadiness, type ResultReport } from "@/lib/result-report";
import {
  completeDiagnosis,
  createDiagnosis,
  saveAnswer,
  verifyAccess,
  type CompleteDiagnosisResponse,
  type DiagnosisSession,
} from "@/lib/service-mvp";

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

const demoRecommendations = recommendationRunSchema.parse({
  query_terms: ["imu", "sensor_fusion", "pid", "attitude_control"],
  fallback_reasons: [],
  candidate_count: 8,
  verified_candidate_count: 7,
  recommendations: [
    {
      title: "PX4 Controller Diagrams",
      url: "https://docs.px4.io/main/en/flight_stack/controller_diagrams.html",
      source_name: "PX4",
      source_type: "official_docs",
      difficulty: "intermediate",
      trust_score: 0.98,
      recommendation_reason: "pid, attitude_control 보강에 직접 연결되는 검증 자료",
      prerequisite_tags: ["imu", "sensor_fusion"],
      concept_tags: ["pid", "attitude_control", "rate_control"],
      score: {
        trust: 0.343,
        level_fit: 0.25,
        freshness: 0.135,
        practice: 0.0975,
        dedupe: 0.1,
        total: 0.9255,
      },
    },
    {
      title: "Betaflight PID Tuning Guide",
      url: "https://betaflight.com/docs/wiki/guides/current/PID-Tuning-Guide",
      source_name: "Betaflight",
      source_type: "official_docs",
      difficulty: "intermediate",
      trust_score: 0.92,
      recommendation_reason: "pid 보강에 직접 연결되는 검증 자료",
      prerequisite_tags: ["gyro"],
      concept_tags: ["pid", "flight_tuning"],
      score: {
        trust: 0.322,
        level_fit: 0.25,
        freshness: 0.129,
        practice: 0.135,
        dedupe: 0.1,
        total: 0.936,
      },
    },
    {
      title: "MIT Underactuated Robotics: State Estimation",
      url: "https://underactuated.mit.edu/state_estimation.html",
      source_name: "MIT",
      source_type: "open_course",
      difficulty: "advanced",
      trust_score: 0.93,
      recommendation_reason: "sensor_fusion 보강에 직접 연결되는 검증 자료",
      prerequisite_tags: ["linear_algebra", "probability"],
      concept_tags: ["sensor_fusion", "ekf", "state_estimation"],
      score: {
        trust: 0.3255,
        level_fit: 0.175,
        freshness: 0.1125,
        practice: 0.0525,
        dedupe: 0.1,
        total: 0.7655,
      },
    },
  ],
});

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>({
    status: "checking",
    data: null,
    message: "API 상태 확인 중",
  });
  const [inviteCode, setInviteCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [diagnosis, setDiagnosis] = useState<DiagnosisSession | null>(null);
  const [selectedChoices, setSelectedChoices] = useState<Record<string, string>>({});
  const [savedQuestionIds, setSavedQuestionIds] = useState<Set<string>>(new Set());
  const [completed, setCompleted] = useState<CompleteDiagnosisResponse | null>(null);
  const [workflowMessage, setWorkflowMessage] = useState("초대 코드로 내부 진단을 시작합니다");

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

  const report = completed?.report ?? demoReport;
  const recommendations = completed?.recommendations ?? demoRecommendations;
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
          <AccessAndDiagnosisPanel
            diagnosis={diagnosis}
            displayName={displayName}
            email={email}
            inviteCode={inviteCode}
            selectedChoices={selectedChoices}
            savedQuestionIds={savedQuestionIds}
            token={token}
            workflowMessage={workflowMessage}
            onDisplayNameChange={setDisplayName}
            onEmailChange={setEmail}
            onInviteCodeChange={setInviteCode}
            onSelectChoice={(questionId, choiceKey) =>
              setSelectedChoices((current) => ({ ...current, [questionId]: choiceKey }))
            }
            onVerify={async () => {
              try {
                const access = await verifyAccess({
                  invite_code: inviteCode,
                  display_name: displayName,
                  email: email || undefined,
                });
                setToken(access.token);
                setWorkflowMessage(`${access.user.display_name} 세션이 열렸습니다`);
              } catch (error) {
                setWorkflowMessage(error instanceof Error ? error.message : "접근 확인 실패");
              }
            }}
            onStart={async () => {
              if (!token) {
                return;
              }
              try {
                const nextDiagnosis = await createDiagnosis(token);
                setDiagnosis(nextDiagnosis);
                setCompleted(null);
                setSelectedChoices({});
                setSavedQuestionIds(new Set());
                setWorkflowMessage(`${nextDiagnosis.question_count}문항 진단이 시작됐습니다`);
              } catch (error) {
                setWorkflowMessage(error instanceof Error ? error.message : "진단 시작 실패");
              }
            }}
            onSubmitAnswer={async (questionId) => {
              if (!token || !diagnosis) {
                return;
              }
              const choiceKey = selectedChoices[questionId];
              if (!choiceKey) {
                setWorkflowMessage("선택지를 먼저 고르세요");
                return;
              }
              try {
                await saveAnswer({
                  token,
                  diagnosisId: diagnosis.id,
                  questionExternalId: questionId,
                  choiceKeys: [choiceKey],
                });
                setSavedQuestionIds((current) => new Set(current).add(questionId));
                setWorkflowMessage(`${questionId} 답변이 저장됐습니다`);
              } catch (error) {
                setWorkflowMessage(error instanceof Error ? error.message : "답변 저장 실패");
              }
            }}
            onComplete={async () => {
              if (!token || !diagnosis) {
                return;
              }
              if (savedQuestionIds.size < diagnosis.question_count) {
                setWorkflowMessage(
                  `모든 문항을 저장한 뒤 완료할 수 있습니다 (${savedQuestionIds.size}/${diagnosis.question_count})`,
                );
                return;
              }
              try {
                const result = await completeDiagnosis(token, diagnosis.id);
                setCompleted(result);
                setDiagnosis(result.diagnosis);
                setWorkflowMessage("진단 결과와 추천 자료가 저장됐습니다");
              } catch (error) {
                setWorkflowMessage(error instanceof Error ? error.message : "진단 완료 실패");
              }
            }}
          />
          <ReportSummary report={report} weakDomainLabels={weakDomainLabels} />
          <DomainGrid report={report} />
          <Roadmap report={report} />
          <Recommendations run={recommendations} />
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

function AccessAndDiagnosisPanel({
  diagnosis,
  displayName,
  email,
  inviteCode,
  selectedChoices,
  savedQuestionIds,
  token,
  workflowMessage,
  onComplete,
  onDisplayNameChange,
  onEmailChange,
  onInviteCodeChange,
  onSelectChoice,
  onStart,
  onSubmitAnswer,
  onVerify,
}: {
  diagnosis: DiagnosisSession | null;
  displayName: string;
  email: string;
  inviteCode: string;
  selectedChoices: Record<string, string>;
  savedQuestionIds: Set<string>;
  token: string | null;
  workflowMessage: string;
  onComplete: () => Promise<void>;
  onDisplayNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onInviteCodeChange: (value: string) => void;
  onSelectChoice: (questionId: string, choiceKey: string) => void;
  onStart: () => Promise<void>;
  onSubmitAnswer: (questionId: string) => Promise<void>;
  onVerify: () => Promise<void>;
}) {
  const answeredLabel = diagnosis
    ? `${savedQuestionIds.size}/${diagnosis.question_count} 저장`
    : "대기 중";
  return (
    <section className="rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold tracking-normal">내부 MVP 진단</h2>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-[#536173]">{answeredLabel}</span>
          <span className="text-sm text-[#536173]">{workflowMessage}</span>
        </div>
      </div>
      {!token ? (
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto]">
          <input
            className="rounded-md border border-[#cfd7e3] px-3 py-2 text-sm"
            onChange={(event) => onInviteCodeChange(event.target.value)}
            placeholder="Invite code"
            value={inviteCode}
          />
          <input
            className="rounded-md border border-[#cfd7e3] px-3 py-2 text-sm"
            onChange={(event) => onDisplayNameChange(event.target.value)}
            placeholder="Display name"
            value={displayName}
          />
          <input
            className="rounded-md border border-[#cfd7e3] px-3 py-2 text-sm"
            onChange={(event) => onEmailChange(event.target.value)}
            placeholder="Email"
            value={email}
          />
          <button
            className="rounded-md bg-[#087f83] px-4 py-2 text-sm font-semibold text-white"
            onClick={onVerify}
            type="button"
          >
            확인
          </button>
        </div>
      ) : null}
      {token && !diagnosis ? (
        <button
          className="rounded-md bg-[#087f83] px-4 py-2 text-sm font-semibold text-white"
          onClick={onStart}
          type="button"
        >
          진단 시작
        </button>
      ) : null}
      {diagnosis ? (
        <div className="grid gap-4">
          {diagnosis.questions.map((question, index) => (
            <div className="rounded-md border border-[#e1e7ef] p-4" key={question.external_id}>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-[#e5f4f3] px-2 py-1 text-xs font-semibold text-[#087f83]">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="rounded-md bg-[#e5f4f3] px-2 py-1 text-xs font-semibold text-[#087f83]">
                  {domainLabel.get(question.domain)}
                </span>
                <span className="rounded-md bg-[#edf2f7] px-2 py-1 text-xs text-[#536173]">
                  {question.difficulty}
                </span>
                {savedQuestionIds.has(question.external_id) ? (
                  <span className="rounded-md bg-[#eef8ed] px-2 py-1 text-xs text-[#2f7d32]">
                    저장됨
                  </span>
                ) : null}
              </div>
              <p className="text-base font-semibold leading-7">{question.prompt}</p>
              <div className="mt-4 grid gap-2">
                {question.choices.map((choice) => (
                  <label
                    className="flex items-center gap-3 rounded-md border border-[#d8dee9] px-3 py-2 text-sm"
                    key={choice.key}
                  >
                    <input
                      checked={selectedChoices[question.external_id] === choice.key}
                      name={question.external_id}
                      onChange={() => onSelectChoice(question.external_id, choice.key)}
                      type="radio"
                    />
                    <span>{choice.text}</span>
                  </label>
                ))}
              </div>
              <button
                className="mt-4 rounded-md border border-[#087f83] px-4 py-2 text-sm font-semibold text-[#087f83]"
                onClick={() => onSubmitAnswer(question.external_id)}
                type="button"
              >
                답변 저장
              </button>
            </div>
          ))}
          <div className="flex flex-wrap gap-3">
            <button
              className="rounded-md bg-[#087f83] px-4 py-2 text-sm font-semibold text-white"
              onClick={onComplete}
              type="button"
            >
              완료
            </button>
          </div>
        </div>
      ) : null}
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

function Recommendations({ run }: { run: RecommendationRun }) {
  return (
    <section className="rounded-md border border-[#d8dee9] bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck aria-hidden="true" size={19} className="text-[#087f83]" />
          <h2 className="text-lg font-semibold tracking-normal">검증 학습 자료</h2>
        </div>
        <span className="text-sm text-[#536173]">
          {run.verified_candidate_count}/{run.candidate_count} 후보 검증 통과
        </span>
      </div>
      <div className="grid gap-3 xl:grid-cols-3">
        {run.recommendations.map((recommendation) => (
          <a
            key={recommendation.url}
            href={recommendation.url}
            className="min-h-56 rounded-md border border-[#e1e7ef] p-4 transition hover:border-[#087f83]"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-[#e5f4f3] px-2 py-1 text-xs font-semibold text-[#087f83]">
                {recommendation.source_name}
              </span>
              <span className="rounded-md bg-[#edf2f7] px-2 py-1 text-xs text-[#536173]">
                {difficultyLabel(recommendation.difficulty)}
              </span>
            </div>
            <h3 className="mt-4 text-base font-semibold leading-6 tracking-normal">
              {recommendation.title}
            </h3>
            <p className="mt-3 text-sm leading-6 text-[#536173]">
              {recommendation.recommendation_reason}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {recommendation.concept_tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="rounded-md border border-[#d8dee9] px-2 py-1 font-mono text-xs text-[#536173]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </a>
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

function difficultyLabel(difficulty: RecommendationRun["recommendations"][number]["difficulty"]) {
  const labels = {
    intro: "입문",
    intermediate: "중급",
    advanced: "심화",
  };
  return labels[difficulty];
}
