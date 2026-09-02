"""
STRIDE Threat Modeling via Ollama AI.
Generates a structured security threat model from violations and code diff.
"""

import httpx
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from devops_assistant.config import Violation


class ThreatEntry(BaseModel):
    category: str        # Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation
    threat: str
    affected_component: str
    mitigation: str
    severity: str = "MEDIUM"


class ThreatModel(BaseModel):
    summary: str = ""
    threats: List[ThreatEntry] = Field(default_factory=list)
    raw_response: str = ""


_STRIDE_PROMPT = """You are a senior security architect performing a STRIDE threat model analysis.

Given the following code violations and project context, produce a structured threat model.

VIOLATIONS SUMMARY:
{violations_summary}

GIT DIFF (recent changes):
{diff_snippet}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "summary": "brief executive summary of security posture",
  "threats": [
    {{
      "category": "one of: Spoofing|Tampering|Repudiation|Information Disclosure|Denial of Service|Elevation of Privilege",
      "threat": "description of the specific threat",
      "affected_component": "file or component name",
      "mitigation": "recommended mitigation step",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL"
    }}
  ]
}}

Produce at least 3 threats. Respond with JSON only, no explanation."""


def run_threat_model(
    violations: List[Violation],
    git_diff: str = "",
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
) -> ThreatModel:
    """Generate a STRIDE threat model using Ollama."""

    violations_summary = "\n".join(
        f"- [{v.severity}] {v.scanner_name}: {v.description} ({v.file_path}:{v.line_number})"
        for v in violations[:20]  # limit to top 20
    ) or "No violations detected."

    diff_snippet = git_diff[:2000] if git_diff else "No diff available."

    prompt = _STRIDE_PROMPT.format(
        violations_summary=violations_summary,
        diff_snippet=diff_snippet,
    )

    try:
        resp = httpx.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=300.0,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            threats = [ThreatEntry(**t) for t in data.get("threats", [])]
            return ThreatModel(
                summary=data.get("summary", ""),
                threats=threats,
                raw_response=raw,
            )
    except httpx.TimeoutException:
        print("[Warning] Threat model call timed out.")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[Warning] Threat model parse error: {e}")
    except Exception as e:
        print(f"[Warning] Threat model call failed: {e}")

    # Return a fallback generic threat model
    return ThreatModel(
        summary="Automated threat model unavailable. Manual review recommended.",
        threats=[
            ThreatEntry(
                category="Information Disclosure",
                threat="Sensitive data may be exposed via error messages or logs.",
                affected_component="Application",
                mitigation="Ensure error messages are generic in production.",
                severity="MEDIUM",
            )
        ],
        raw_response="",
    )
