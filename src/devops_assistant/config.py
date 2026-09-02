"""
Data models and configuration for AI DevOps Assistant.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Violation(BaseModel):
    scanner_name: str
    file_path: str
    line_number: int = 1
    rule_id: str
    description: str
    severity: Severity = Severity.MEDIUM


class TestRunResult(BaseModel):
    __test__ = False
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    coverage_percentage: float = 0.0
    output_log: str = ""
    error_details: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.total_tests >= 0


class AIReviewComment(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    category: str = "Code Quality"  # Code Quality, Security, Performance, Style
    comment: str
    suggested_code: Optional[str] = None


class AIReviewResult(BaseModel):
    quality_score: int = 85  # 0 to 100
    summary: str = ""
    comments: List[AIReviewComment] = Field(default_factory=list)


class DockerBuildResult(BaseModel):
    dockerfile_found: bool = False
    success: bool = True
    image_tag: str = ""
    duration_seconds: float = 0.0
    logs: str = ""
    failure_reason: Optional[str] = None


class PipelineConfig(BaseModel):
    repo_url: Optional[str] = None
    target_path: str = "."
    branch: str = "main"
    depth: int = 1
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder"
    run_docker: bool = True
    run_ai_review: bool = True
    run_test_generation: bool = True
    output_dir: str = "ci_reports"


class CommitInfo(BaseModel):
    commit_hash: str = "local"
    author: str = "Local User"
    message: str = "Local workspace analysis"
    branch: str = "main"


class ThreatEntry(BaseModel):
    category: str
    threat: str
    affected_component: str
    mitigation: str
    severity: str = "MEDIUM"


class ThreatModel(BaseModel):
    summary: str = ""
    threats: List[ThreatEntry] = Field(default_factory=list)
    raw_response: str = ""


class AutoFixResult(BaseModel):
    fixed: List[str] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    diffs: Dict[str, str] = Field(default_factory=dict)


class MetricsSummary(BaseModel):
    run_id: str = ""
    timestamp: str = ""
    quality_score: int = 0
    total_violations: int = 0
    coverage_percentage: float = 0.0
    score_delta: Optional[int] = None       # vs previous run
    violation_delta: Optional[int] = None   # vs previous run


class AlertConfig(BaseModel):
    min_quality_score: int = 75
    max_violations: int = 10
    slack_webhook: str = ""
    email_to: str = ""
    email_from: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_password: str = ""


class CIReportData(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    commit_info: CommitInfo = Field(default_factory=CommitInfo)
    target_path: str = "."
    violations: List[Violation] = Field(default_factory=list)
    test_result: TestRunResult = Field(default_factory=TestRunResult)
    ai_review: AIReviewResult = Field(default_factory=AIReviewResult)
    docker_result: DockerBuildResult = Field(default_factory=DockerBuildResult)
    threat_model: Optional[ThreatModel] = None
    autofix_result: Optional[AutoFixResult] = None
    overall_passed: bool = True
    quality_score: int = 100
