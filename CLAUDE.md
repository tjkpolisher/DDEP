# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DDEP, Drone Diagnosis and Education Platform**: A competency assessment platform for drone development engineers. Users complete a 15-30 minute assessment across 6 domains, receive a detailed competency profile, identify knowledge gaps (via concept tags), and get personalized learning resource recommendations.

### MVP Scope
- Internal users (CAELUM team + close beta group)
- 6 diagnostic domains (Airframe/Aerodynamics, Electronics/Hardware, Control, Software, Autonomous Flight/AI, Manufacturing/Operations)
- Adaptive diagnostic engine
- Learning resource search agent
- No payment, authentication, or custom learning content in MVP

### Excluded from MVP
- Math/physics as a standalone domain (only as prerequisite tags)
- Payment/subscription features
- Team admin dashboard
- Custom course content

## Phase-Based Architecture

This project is organized into **6 sequential phases**. Each phase is a complete, shippable outcome with its own scope, completion criteria, and AGENTS.md file.

```
phases/
├── 00-foundation/        # Base infrastructure, tech stack, common schemas
├── 01-question-db/       # Question schema, tag system, initial question set
├── 02-diagnosis-engine/  # Scoring, adaptive question selection, weakness extraction
├── 03-result-report/     # Domain profiles, learning roadmaps, reassessment UX
├── 04-search-agent/      # Search, filtering, resource ranking and recommendations
└── 05-service-mvp/       # Authentication, persistence, deployment, beta ops
```

**Important**: Work must follow phase order. Read each phase's `phases/*/AGENTS.md` before starting work. Phase AGENTS.md files override this root CLAUDE.md.

## Tech Stack & Standards

### Frontend
- **Framework**: Next.js + TypeScript
- **UI Library**: shadcn/ui components + Tailwind CSS
- **Schema Validation**: Zod
- **Build**: Next.js default (development: `npm run dev`)

### Backend
- **Framework**: FastAPI + Python 3.10+
- **Package Manager**: `uv` (required for all Python work)
- **Schema**: Pydantic models
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Vector Search**: pgvector (if needed for search agent)
- **Cache/Queue**: Redis + RQ or Celery (optional, reviewed during Phase 04)
- **Development**: `uv run` for all Python execution

### Infrastructure
- **Local Dev**: Docker Compose (reproducibility first)
- **Environment**: `.env` files for local config
- **Deployment**: Deferred beyond MVP (Phase 05 placeholder)

## Core Development Principles

1. **Phase Integrity**: Never implement features beyond current phase scope. Document out-of-scope work as TODO.

2. **Structured Data**: All domain/question/diagnostic/resource data must use explicit schemas:
   - Python: Pydantic models + SQLAlchemy
   - TypeScript: Zod schemas
   - **Never**: Parse data with regex or ad-hoc string splitting

3. **Dependency Management**:
   - Python: Always use `uv add`, `uv sync`, `uv run`
   - Update `pyproject.toml` (explicit) and `uv.lock` (locked versions)

4. **External Services**:
   - Document all API call paths, error cases, and fallback behavior
   - Search agent calls (Phase 04) require explicit resilience design
   - No unvalidated search results in recommendations

## 6 Diagnostic Domains

These are **fixed** and used in questions, scoring, and result reporting:

1. 기체/공력 (Airframe/Aerodynamics)
2. 전장/하드웨어 (Electronics/Hardware)
3. 제어 (Control)
4. 소프트웨어 (Software)
5. 자율비행/AI (Autonomous Flight/AI)
6. 제작/운용 (Manufacturing/Operations)

## Common Data Models Location

**To be established in Phase 00** (foundation). Future phases will import shared schemas from a central location (likely `common/schemas.py` for backend, `common/types.ts` for frontend).

## Key Development Commands

These will be finalized in Phase 00. Expected patterns:

```bash
# Python (backend)
uv add <package>        # Add dependency
uv sync                 # Install locked dependencies
uv run <script.py>      # Run Python script with uv environment

# TypeScript/Next.js (frontend)
npm install
npm run dev             # Start dev server
npm run build           # Build for production
npm run lint            # Run linter (ESlint)

# Docker Compose (full stack local)
docker-compose up -d    # Start all services
docker-compose down     # Stop all services
```

Full commands with testing, linting, and database setup will be documented once Phase 00 is complete.

## How to Approach Each Phase

When starting work on a phase:

1. **Read Phase AGENTS.md**: Understand scope, completion criteria, and constraints
2. **Check Dependencies**: Confirm all prior phases are stable
3. **Establish/Reuse Schemas**: Use shared models; add new ones to common location
4. **Implement in Isolation**: Keep phase changes within its directory
5. **Document Outcomes**: Update `docs/phases/` with deliverables and risk notes (if Phase 00 docs structure is defined)

## Important Constraints & Guardrails

### Must Follow
- Explicit schema definitions (Pydantic, Zod, SQLAlchemy) for all data structures
- Docker Compose for reproducible local development
- Sequential phase progression (no skipping)
- Reference phase AGENTS.md as source of truth for scope

### Must NOT Do
- Hardcode questions/domains into code constants
- Implement LLM-based scoring as core diagnostic path (objective/short-answer focus only)
- Build payment or multi-tenant team features in MVP
- Deploy to production without Phase 05 completion

## File Structure & Conventions

```
drone-diagnosis-platform/
├── CLAUDE.md              # This file
├── README.md              # Project overview & how to run
├── AGENTS.md              # Root-level work rules
├── docs/
│   ├── prd-v0.2-decisions.md    # Product decisions
│   └── phases/                   # Phase outcomes (to be created)
└── phases/
    ├── 00-foundation/
    ├── 01-question-db/
    ├── 02-diagnosis-engine/
    ├── 03-result-report/
    ├── 04-search-agent/
    └── 05-service-mvp/
        └── AGENTS.md             # Each phase documents its own scope
```

## Debugging & Development Tips

- **Python Development**: Always use `uv run` (not bare `python`) to ensure dependencies are correct
- **Schema Changes**: Update both the model/schema AND any corresponding migrations or seed scripts
- **Database**: Use SQLAlchemy + Alembic for migrations (setup expected in Phase 00)
- **Type Safety**: Leverage Pydantic validation on backend and Zod on frontend; catch errors early
- **Search Agent**: Phase 04 will document resilience patterns for external API calls

## Questions or Issues?

- If AGENTS.md and this file conflict, **AGENTS.md takes priority**
- Phase-specific guidance always overrides root guidance
- Escalate cross-phase architecture questions before implementation
