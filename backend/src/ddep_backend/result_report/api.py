from pydantic import BaseModel, ConfigDict

from ddep_backend.diagnosis_engine.models import DiagnosisResult
from ddep_backend.result_report.builder import build_result_report
from ddep_backend.result_report.models import ResultReport


class ResultReportPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: DiagnosisResult
    previous_result: DiagnosisResult | None = None


def preview_result_report(request: ResultReportPreviewRequest) -> ResultReport:
    return build_result_report(request.result, previous_result=request.previous_result)
