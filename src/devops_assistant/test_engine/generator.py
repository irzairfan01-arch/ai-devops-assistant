"""
Ollama AI Test Generator with Iterative Self-Correction Loop.
"""

import os
import re
import httpx
from typing import List, Optional
from devops_assistant.config import TestRunResult
from devops_assistant.test_engine.runner import run_pytest


class OllamaTestGenerator:
    """Generates pytest test suites using local Ollama LLMs with iterative error correction."""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5-coder"):
        self.ollama_url = ollama_url
        self.model = model

    def is_ollama_available(self) -> bool:
        """Checks if local Ollama server is responsive."""
        try:
            r = httpx.get(f"{self.ollama_url}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate_code(self, prompt: str) -> Optional[str]:
        """Calls Ollama generate API with prompt."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            }
            r = httpx.post(f"{self.ollama_url}/api/generate", json=payload, timeout=300.0)
            if r.status_code == 200:
                return r.json().get("response", "")
        except Exception as e:
            print(f"[Warning] Ollama call failed: {e}")
        return None

    def clean_python_code(self, raw_response: str) -> str:
        """Extracts code block from markdown ```python response."""
        pattern = r"```(?:python)?\s*(.*?)\s*```"
        matches = re.findall(pattern, raw_response, re.DOTALL)
        if matches:
            return matches[0].strip()
        return raw_response.strip()

    def generate_test_file(self, source_code: str, file_path: str) -> Optional[str]:
        """Generates pytest code for a single source file."""
        prompt = f"""You are an expert Python QA automation engineer.
Write a comprehensive pytest unit test suite for the following Python code file ({file_path}).

RULES:
1. Return ONLY valid Python test code wrapped in ```python ... ``` block.
2. Include docstrings and assertions testing normal cases, edge cases, and invalid inputs.
3. Use pytest fixtures or mocks where necessary.

SOURCE CODE:
{source_code}
"""
        raw = self.generate_code(prompt)
        if raw:
            return self.clean_python_code(raw)
        return None

    def refine_test_file(self, source_code: str, test_code: str, pytest_error_log: str) -> Optional[str]:
        """Iterative correction loop: Fixes generated tests based on pytest execution error output."""
        prompt = f"""The generated pytest test suite failed when executed.

SOURCE CODE:
{source_code}

CURRENT TEST SUITE:
{test_code}

PYTEST FAILURE LOG:
{pytest_error_log}

TASK:
Analyze the pytest failure log and fix the bugs in the test suite so all tests pass cleanly.
Return ONLY the corrected Python test code wrapped in ```python ... ```.
"""
        raw = self.generate_code(prompt)
        if raw:
            return self.clean_python_code(raw)
        return None


def generate_tests_for_repo(target_path: str, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5-coder") -> Optional[TestRunResult]:
    """Scans target Python source files, generates unit tests, runs them, and attempts iterative fixes."""
    generator = OllamaTestGenerator(ollama_url=ollama_url, model=model)
    if not generator.is_ollama_available():
        print(f"[Info] Ollama server at {ollama_url} is unreachable. Skipping AI test generation.")
        return None

    # Discover target Python files (excluding existing test_ files)
    py_files = []
    for root, _, files in os.walk(target_path):
        if "tests" in root or "venv" in root or ".git" in root:
            continue
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and not file.startswith("__"):
                py_files.append(os.path.join(root, file))

    if not py_files:
        return None

    gen_test_dir = os.path.join(target_path, "tests", "generated")
    os.makedirs(gen_test_dir, exist_ok=True)
    init_file = os.path.join(gen_test_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Generated test package\n")

    for py_file in py_files[:3]:  # Limit to top 3 target files for performance
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                code_content = f.read()

            rel_path = os.path.relpath(py_file, target_path)
            basename = os.path.basename(py_file)
            test_filename = f"test_gen_{basename}"
            test_file_path = os.path.join(gen_test_dir, test_filename)

            test_code = generator.generate_test_file(code_content, rel_path)
            if test_code:
                with open(test_file_path, "w", encoding="utf-8") as tf:
                    tf.write(test_code)

                # Run pytest on generated test file
                result = run_pytest(target_path, test_dir=test_file_path)

                # If test failed, perform 1 self-correction pass
                if result.failed > 0 and result.output_log:
                    corrected_code = generator.refine_test_file(code_content, test_code, result.output_log)
                    if corrected_code:
                        with open(test_file_path, "w", encoding="utf-8") as tf:
                            tf.write(corrected_code)

        except Exception as e:
            print(f"[Warning] Failed test generation for {py_file}: {e}")

    # Return aggregated run result over generated tests
    return run_pytest(target_path, test_dir=gen_test_dir)
