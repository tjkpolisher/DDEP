from pydantic import BaseModel

from ddep_backend.domains import DomainDefinition


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    domains: tuple[DomainDefinition, ...]
