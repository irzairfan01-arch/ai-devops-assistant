import os
import ast
from typing import Dict, List, Set


class ProjectGraph:
    """Builds a lightweight AST-based architectural graph of a Python project."""

    def __init__(self, target_path: str):
        self.target_path = os.path.abspath(target_path)
        self.file_ast_map: Dict[str, ast.Module] = {}
        self.file_code_map: Dict[str, str] = {}
        self._build_graph()

    def _build_graph(self):
        """Scans the directory and parses all Python files into ASTs."""
        for root, dirs, files in os.walk(self.target_path):
            # Skip irrelevant directories
            dirs[:] = [d for d in dirs if d not in (".git", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "ci_reports")]
            for file in files:
                if file.endswith(".py"):
                    fpath = os.path.join(root, file)
                    rel_path = os.path.relpath(fpath, self.target_path)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            code = f.read()
                        self.file_code_map[rel_path] = code
                        self.file_ast_map[rel_path] = ast.parse(code, filename=rel_path)
                    except Exception as e:
                        print(f"[Graphify] Failed to parse {rel_path}: {e}")

    def _extract_signatures_from_ast(self, tree: ast.Module) -> str:
        """Extracts class and function signatures from an AST module."""
        lines = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                lines.append(f"class {node.name}:")
                doc = ast.get_docstring(node)
                if doc:
                    lines.append(f'    """{doc.split(chr(10))[0]}"""')
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        args = [a.arg for a in child.args.args]
                        arg_str = ", ".join(args)
                        lines.append(f"    def {child.name}({arg_str}): ...")
            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                arg_str = ", ".join(args)
                lines.append(f"def {node.name}({arg_str}): ...")
                doc = ast.get_docstring(node)
                if doc:
                    lines.append(f'    """{doc.split(chr(10))[0]}"""')
        return "\n".join(lines)

    def get_project_signatures(self, exclude_files: List[str] = None) -> str:
        """Returns a string containing the signatures of all classes and functions in the project."""
        exclude_files = exclude_files or []
        output = []
        for rel_path, tree in self.file_ast_map.items():
            # Skip test files and excluded files in the global map
            if rel_path in exclude_files or rel_path.startswith("test_") or "tests\\" in rel_path or "tests/" in rel_path:
                continue
            
            signatures = self._extract_signatures_from_ast(tree)
            if signatures.strip():
                output.append(f"--- FILE: {rel_path} ---")
                output.append(signatures)
                output.append("")
        return "\n".join(output)
