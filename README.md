# DDEP, Drone Diagnosis and Education Platform

드론 개발 역량 진단 플랫폼 작업공간입니다.

## MVP 방향

- 대상: 팀원 및 가까운 베타 그룹
- 목적: 드론 개발 역량을 6개 도메인 기준으로 진단하고 학습 로드맵을 추천
- 범위: 진단, 결과 리포트, 검색 에이전트 기반 추천 자료까지 MVP에 포함
- 제외: 수학/물리 기초 독립 도메인, 결제, 팀 관리자 대시보드, 자체 강의 콘텐츠
- Python 패키지 관리는 `uv`를 사용

## Phase 구조

1. `phases/00-foundation`: 프로젝트 기본 동작, 스택, 공통 규칙
2. `phases/01-question-db`: 문항 DB 구축
3. `phases/02-diagnosis-engine`: 진단 엔진
4. `phases/03-result-report`: 결과 리포트
5. `phases/04-search-agent`: 검색 에이전트
6. `phases/05-service-mvp`: 서비스화 MVP

