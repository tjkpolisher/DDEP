"use client";

import { Cpu, Gauge, Plane, RadioTower, Route, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/status-pill";
import { diagnosisDomains } from "@/lib/domains";
import { fetchHealth, type HealthResponse } from "@/lib/health";

const domainIcons = [Plane, Cpu, Gauge, RadioTower, Route, Wrench];

type ApiState =
  | { status: "checking"; data: null; message: string }
  | { status: "online"; data: HealthResponse; message: string }
  | { status: "offline"; data: null; message: string };

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

  const apiDomainCount = apiState.data?.domains.length ?? 0;
  const domainCountLabel = useMemo(
    () => `${apiDomainCount || diagnosisDomains.length}개 진단 도메인`,
    [apiDomainCount],
  );

  return (
    <main className="min-h-screen bg-[#f8fafc]">
      <section className="border-b border-[#d7dde8] bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-8 sm:px-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#0f766e]">DDEP</p>
            <h1 className="text-3xl font-semibold tracking-normal text-[#111827] sm:text-4xl">
              드론 개발 역량 진단
            </h1>
            <p className="max-w-2xl text-base leading-7 text-[#475569]">
              내부 MVP 기준의 6개 도메인 구조와 백엔드 health 상태를 한 화면에서 확인합니다.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-[#d7dde8] bg-[#f8fafc] px-4 py-3">
            <StatusPill status={apiState.status} />
            <span className="text-sm text-[#475569]">{apiState.message}</span>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-6xl gap-5 px-5 py-8 sm:px-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {diagnosisDomains.map((domain, index) => {
            const Icon = domainIcons[index];

            return (
              <article
                key={domain.slug}
                className="min-h-44 rounded-md border border-[#d7dde8] bg-white p-5 shadow-sm"
              >
                <div className="mb-5 flex items-center justify-between gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#e6f4f1] text-[#0f766e]">
                    <Icon aria-hidden="true" size={21} strokeWidth={2} />
                  </div>
                  <span className="font-mono text-xs text-[#64748b]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <h2 className="text-lg font-semibold tracking-normal text-[#111827]">{domain.label}</h2>
                <p className="mt-3 text-sm leading-6 text-[#475569]">{domain.summary}</p>
              </article>
            );
          })}
        </div>

        <aside className="rounded-md border border-[#d7dde8] bg-white p-5 shadow-sm">
          <div className="space-y-5">
            <div>
              <p className="text-sm font-medium text-[#64748b]">구조</p>
              <p className="mt-2 text-2xl font-semibold text-[#111827]">{domainCountLabel}</p>
            </div>
            <div className="border-t border-[#d7dde8] pt-5">
              <p className="text-sm font-medium text-[#64748b]">API</p>
              <p className="mt-2 text-base font-semibold text-[#111827]">
                {apiState.data?.service ?? "DDEP API"}
              </p>
              <p className="mt-1 text-sm text-[#64748b]">
                {apiState.data?.environment ?? "local"}
              </p>
            </div>
            <div className="border-t border-[#d7dde8] pt-5">
              <p className="text-sm font-medium text-[#64748b]">다음 Phase</p>
              <p className="mt-2 text-sm leading-6 text-[#475569]">
                문항 스키마와 seed 데이터는 Phase 01에서 구조화합니다.
              </p>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
