"""
Unit tests for static analysis scanners.
"""

import os
import tempfile
from devops_assistant.scanners import run_ruff, run_bandit, run_semgrep


def test_ruff_and_bandit_scanners():
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "sample.py")
        with open(sample_file, "w") as f:
            # Code containing intentionally unformatted line and bandit issue (eval)
            f.write("import os\n\ndef bad_func(x):\n    eval(x)\n")

        v_ruff = run_ruff(tmpdir)
        v_bandit = run_bandit(tmpdir)
        v_semgrep = run_semgrep(tmpdir)

        # Bandit should flag eval() call (B307)
        bandit_rules = [v.rule_id for v in v_bandit]
        assert len(v_bandit) >= 1
        assert "B307" in bandit_rules or any("eval" in v.description.lower() for v in v_bandit)
