from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DiagnosisDomain(StrEnum):
    AIRFRAME_AERODYNAMICS = "airframe_aerodynamics"
    ELECTRONICS_HARDWARE = "electronics_hardware"
    CONTROL = "control"
    SOFTWARE = "software"
    AUTONOMOUS_AI = "autonomous_ai"
    FABRICATION_OPERATIONS = "fabrication_operations"


class DomainDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: DiagnosisDomain
    label: str
    summary: str


DIAGNOSIS_DOMAINS: tuple[DomainDefinition, ...] = (
    DomainDefinition(
        slug=DiagnosisDomain.AIRFRAME_AERODYNAMICS,
        label="기체/공력",
        summary="프레임, 추진계, 비행 성능, 공력 기본 개념",
    ),
    DomainDefinition(
        slug=DiagnosisDomain.ELECTRONICS_HARDWARE,
        label="전장/하드웨어",
        summary="전원, 센서, 통신, 임베디드 하드웨어 구성",
    ),
    DomainDefinition(
        slug=DiagnosisDomain.CONTROL,
        label="제어",
        summary="동역학, 안정화, 제어기 튜닝, 상태 추정",
    ),
    DomainDefinition(
        slug=DiagnosisDomain.SOFTWARE,
        label="소프트웨어",
        summary="펌웨어, 지상국, 데이터 파이프라인, 개발 도구",
    ),
    DomainDefinition(
        slug=DiagnosisDomain.AUTONOMOUS_AI,
        label="자율비행/AI",
        summary="경로 계획, 인지, SLAM, 임무 자동화",
    ),
    DomainDefinition(
        slug=DiagnosisDomain.FABRICATION_OPERATIONS,
        label="제작/운용",
        summary="조립, 정비, 안전 점검, 시험 비행 운용",
    ),
)
