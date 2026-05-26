# Phase 04 Search Agent

## 산출물
- `backend/src/ddep_backend/search_agent/`: 검색/추천 요청, 후보, 추천 결과, 점수 breakdown DTO.
- `LearningResourceProvider` 인터페이스와 `CuratedResourceProvider`: 외부 검색 API 없이 검증된 static 후보만 반환하는 MVP provider.
- `recommend_learning_resources`: 검증 필터링, 중복 억제, Phase 04 가중치 기반 ranking, fallback reason 생성.
- `POST /recommendations/preview`: 저장 없이 추천 결과를 확인하는 stateless preview API.
- 프론트엔드 리포트 화면의 추천 자료 섹션 및 Zod 스키마.

## 스코어링
기본 가중치는 Phase 04 기준을 그대로 사용합니다.

- 신뢰도: `0.35`
- 수준 적합도: `0.25`
- 최신성: `0.15`
- 실습성: `0.15`
- 중복 제거: `0.10`

검증되지 않았거나 trust score가 `0.7` 미만인 후보는 추천으로 노출하지 않습니다.

## 실패 / Fallback 정책
- 낮은 신뢰도 또는 미검증 후보가 제거되면 `low_trust_results_filtered`를 기록합니다.
- 직접 concept match가 없으면 broad curated 후보로 보강하고 `no_direct_concept_match`를 기록합니다.
- 검증 후보가 최소 개수보다 적으면 `insufficient_verified_results`를 기록합니다.
- raw 후보 목록은 API 응답에 포함하지 않습니다.

## 검증 방법
- `uv run pytest tests/test_search_agent.py`
- 전체 Phase gate: `uv run pytest`, `uv run ruff check`, `uv run mypy src`, `npm run lint`, `npm run build`

## 남은 리스크
- MVP provider는 curated/static 자료만 사용합니다. 실제 외부 검색 provider를 추가할 때는 rate limit, timeout, cache, source verification 정책을 별도 구현해야 합니다.
- 추천 이력 저장과 사용자별 노출 권한은 Phase 05에서 처리합니다.
