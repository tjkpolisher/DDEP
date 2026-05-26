from typing import Protocol

from ddep_backend.search_agent.models import LearningResourceCandidate, RecommendationRequest


class LearningResourceProvider(Protocol):
    def collect(
        self,
        request: RecommendationRequest,
        query_terms: list[str],
    ) -> list[LearningResourceCandidate]:
        """Collect resource candidates without exposing unverified raw results."""


class CuratedResourceProvider:
    def collect(
        self,
        request: RecommendationRequest,
        query_terms: list[str],
    ) -> list[LearningResourceCandidate]:
        requested = (
            set(request.weak_concept_tags) | set(request.prerequisite_tags) | set(query_terms)
        )
        if not requested:
            return CURATED_RESOURCES
        return [
            candidate
            for candidate in CURATED_RESOURCES
            if requested
            & (
                set(candidate.concept_tags)
                | set(candidate.prerequisite_tags)
                | {candidate.source_name}
            )
        ]


CURATED_RESOURCES: list[LearningResourceCandidate] = [
    LearningResourceCandidate(
        title="PX4 Controller Diagrams",
        url="https://docs.px4.io/main/en/flight_stack/controller_diagrams.html",
        source_name="PX4",
        source_type="official_docs",
        difficulty="intermediate",
        concept_tags=["pid_control", "control_mixer", "state_estimation"],
        prerequisite_tags=["imu_sensor", "coordinate_frames"],
        summary="PX4의 자세/속도 제어 구조와 제어 루프 관계를 확인할 수 있는 공식 문서입니다.",
        trust_score=0.98,
        freshness_score=0.9,
        practice_score=0.65,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="ArduPilot Copter Attitude Control",
        url="https://ardupilot.org/dev/docs/apmcopter-programming-attitude-control-2.html",
        source_name="ArduPilot",
        source_type="official_docs",
        difficulty="advanced",
        concept_tags=["pid_control", "control_mixer"],
        prerequisite_tags=["imu_sensor"],
        summary="ArduPilot Copter의 자세 제어 흐름과 코드 구조를 연결해 학습할 수 있습니다.",
        trust_score=0.96,
        freshness_score=0.85,
        practice_score=0.72,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="PX4 Sensor and Estimator Overview",
        url="https://docs.px4.io/main/en/concept/sensors.html",
        source_name="PX4",
        source_type="official_docs",
        difficulty="intro",
        concept_tags=["imu_sensor", "state_estimation"],
        prerequisite_tags=[],
        summary="센서 입력과 추정기의 역할을 공식 문서 기준으로 정리합니다.",
        trust_score=0.97,
        freshness_score=0.9,
        practice_score=0.45,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="MAVLink Developer Guide",
        url="https://mavlink.io/en/",
        source_name="MAVLink",
        source_type="official_docs",
        difficulty="intermediate",
        concept_tags=["mavlink_protocol", "mission_monitoring"],
        prerequisite_tags=["radio_link"],
        summary="드론 소프트웨어 통신 계층을 공식 메시지 정의와 함께 학습합니다.",
        trust_score=0.98,
        freshness_score=0.88,
        practice_score=0.7,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="ROS 2 Navigation Concepts",
        url="https://docs.nav2.org/concepts/index.html",
        source_name="ROS Nav2",
        source_type="official_docs",
        difficulty="intermediate",
        concept_tags=["path_planning", "geofence", "mission_monitoring"],
        prerequisite_tags=["coordinate_frames"],
        summary="자율 이동체의 경로 계획과 내비게이션 구성 요소를 공식 문서로 확인합니다.",
        trust_score=0.95,
        freshness_score=0.88,
        practice_score=0.75,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="MIT Underactuated Robotics: State Estimation",
        url="https://underactuated.mit.edu/state_estimation.html",
        source_name="MIT",
        source_type="open_course",
        difficulty="advanced",
        concept_tags=["state_estimation", "slam_basics", "perception_pipeline"],
        prerequisite_tags=["coordinate_frames"],
        summary="상태 추정의 수학적 기반을 공개 강의 노트로 학습합니다.",
        trust_score=0.93,
        freshness_score=0.75,
        practice_score=0.35,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="Betaflight PID Tuning Guide",
        url="https://betaflight.com/docs/wiki/guides/current/PID-Tuning-Guide",
        source_name="Betaflight",
        source_type="official_docs",
        difficulty="intermediate",
        concept_tags=["pid_control", "system_identification"],
        prerequisite_tags=["imu_sensor"],
        summary="실제 멀티콥터 튜닝 관점에서 PID 파라미터 영향을 학습합니다.",
        trust_score=0.92,
        freshness_score=0.86,
        practice_score=0.9,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="PX4 Power Module Setup",
        url="https://docs.px4.io/main/en/power_module/",
        source_name="PX4",
        source_type="official_docs",
        difficulty="intro",
        concept_tags=["power_distribution", "battery_monitoring"],
        prerequisite_tags=["voltage_current"],
        summary="전원 모듈과 배터리 모니터링 설정을 공식 절차로 확인합니다.",
        trust_score=0.96,
        freshness_score=0.88,
        practice_score=0.85,
        is_verified=True,
    ),
    LearningResourceCandidate(
        title="Community PID Notes",
        url="https://example.com/community/pid-notes",
        source_name="Community",
        source_type="community_reference",
        difficulty="intro",
        concept_tags=["pid_control"],
        prerequisite_tags=[],
        summary="검증되지 않은 커뮤니티 메모입니다.",
        trust_score=0.3,
        freshness_score=0.5,
        practice_score=0.6,
        is_verified=False,
    ),
]
