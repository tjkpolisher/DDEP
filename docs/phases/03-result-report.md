# Phase 03 Result Report

## 산출물
- `backend/src/ddep_backend/result_report/`: 저장소와 분리된 Pydantic 리포트 DTO 및 순수 builder.
- `POST /result-report/preview`: 기존 `DiagnosisResult` 입력을 받아 저장 없이 `ResultReport`를 반환하는 stateless preview API.
- `frontend/src/lib/result-report.ts`: 리포트 응답을 검증하는 Zod 스키마.
- `frontend/src/app/page.tsx`: 도메인 프로파일, 취약 concept tag, 학습 로드맵, 재진단 대상, 비교 영역을 렌더링하는 내부 리포트 화면.

## 리포트 계약
- 단일 통과/실패 등급을 만들지 않고 6개 도메인별 점수, 신뢰도, 근거 문항 수, 취약 태그를 노출합니다.
- 학습 로드맵은 취약 개념의 prerequisite chain을 먼저 배치한 뒤 해당 취약 개념을 배치합니다.
- 재진단 대상은 취약 개념을 우선하고, 취약 개념이 없으면 근거가 부족한 도메인을 제안합니다.
- 비교 구조는 도메인 점수 변화, 해소된 취약 개념, 새 취약 개념을 제공합니다.

## 검증 방법
- `uv run pytest tests/test_result_report.py`
- 전체 Phase gate: `uv run pytest`, `uv run ruff check`, `uv run mypy src`, `npm run lint`, `npm run build`

## 남은 리스크
- Phase 03은 저장하지 않습니다. 결과 snapshot 보존과 사용자별 비교 권한은 Phase 05에서 처리합니다.
- 화면은 Phase 05 API 연결 전까지 typed demo report로 구조를 고정합니다.
