"""
AI Test File Writer.
Uses Ollama to generate pytest test files for source modules.
"""

import os
import ast
import glob
import httpx


_TEST_PROMPT = """You are an expert Python test engineer using pytest.

Generate a comprehensive pytest test file for the following Python module.

MODULE PATH: {module_path}
MODULE CODE:
```python
{module_code}
```

Requirements:
- Use pytest fixtures and parametrize where appropriate
- Test happy paths, edge cases, and error conditions
- Mock external dependencies (file I/O, HTTP, DB) with unittest.mock
- Use descriptive test function names: test_<function>_<scenario>
- Include at least 5 test functions

Return ONLY the complete Python test file content. No explanation. No markdown fences."""


def _is_valid_python(code: str) -> bool:
    """Check if code parses as valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def generate_tests_for_module(
    module_path: str,
    output_dir: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
) -> str | None:
    """
    Generate a pytest test file for a single Python module.

    Returns the path to the generated test file, or None on failure.
    """
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception:
        return None

    if not code.strip() or len(code) < 50:
        return None  # Too small to bother

    prompt = _TEST_PROMPT.format(module_path=module_path, module_code=code[:3000])

    try:
        resp = httpx.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=300.0,
        )
        resp.raise_for_status()
        test_code = resp.json().get("response", "").strip()
    except Exception as e:
        print(f"[Warning] Test generation failed for {module_path}: {e}")
        return None

    if not test_code or not _is_valid_python(test_code):
        print(f"[Warning] Generated test code is invalid Python for {module_path}")
        return None

    # Build test file name: src/foo/bar.py -> tests/test_bar.py
    base = os.path.splitext(os.path.basename(module_path))[0]
    test_filename = f"test_{base}_ai_generated.py"
    test_path = os.path.join(output_dir, test_filename)

    os.makedirs(output_dir, exist_ok=True)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(f"# AI-Generated test file for {module_path}\n")
        f.write("# Review before committing — may require adjustments.\n\n")
        f.write(test_code)

    return test_path


def generate_tests_for_repo(
    repo_path: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
) -> list[str]:
    """
    Generate test files for all Python source files in the repo.

    Returns list of generated test file paths.
    """
    tests_dir = os.path.join(repo_path, "tests")
    generated = []

    py_files = glob.glob(os.path.join(repo_path, "**", "*.py"), recursive=True)

    # Exclude test files and __init__ files
    py_files = [
        f for f in py_files
        if not os.path.basename(f).startswith("test_")
        and os.path.basename(f) != "__init__.py"
        and "tests" not in f.replace("\\", "/").split("/")
    ]

    for src_file in py_files[:5]:  # Limit to 5 files to avoid long waits
        result = generate_tests_for_module(src_file, tests_dir, ollama_url, model)
        if result:
            generated.append(result)
            print(f"  ✓ Test generated: {result}")

    return generated
