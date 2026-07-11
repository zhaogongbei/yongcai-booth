"""Check repository hygiene rules that keep automation reproducible."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath


BLOCKED_DIRS = {
    ".pytest_cache",
    ".vite",
    "__pycache__",
    "bin",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "obj",
}

BLOCKED_SUFFIXES = {
    ".db",
    ".log",
    ".pid",
    ".pyc",
    ".sqlite",
    ".sqlite3",
}

BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "yarn.lock",
}

BLOCKED_PATHS = {
    "ACTUAL_PROGRESS_REPORT.md",
    "CODE_IMPLEMENTATION_PROGRESS.md",
    "COMPREHENSIVE_FINAL_REPORT.md",
    "CLAUDE.md.backup",
    "CONTINUE_FROM_HERE.md",
    "D-Booth/backend/VERSION",
    "D-Booth/backend/app/services/VERSION",
    "D-Booth/frontend/VERSION",
    "D-Booth/runtime-dotnet/VERSION",
    "D-Booth/backend/.github/workflows/ci.yml",
    "D-Booth/backend/app/models/types.py",
    "FINAL_EXECUTION_REPORT.md",
    "FINAL_OPTIMIZATION_SUMMARY.md",
    "HONEST_FINAL_SUMMARY.md",
    "OPTIMIZATION_REPORT.md",
    "REALTIME_PROGRESS.md",
    "SERVICE_REFACTOR_REPORT.md",
}

REQUIRED_PATHS = {
    "D-Booth/backend/Dockerfile",
    "D-Booth/frontend/Dockerfile",
}

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TEXT = {
    ".github/workflows/ci.yml": [
        "python -m pip_audit -r requirements.txt -r requirements-dev.txt --strict",
        "npm run audit:security",
        "ruff check app/ --select E9,F63,F7,F82",
        "permissions:",
        "gh release create",
        "aquasecurity/trivy-action@v0.36.0",
        "Set up Python for dependency audit",
        "needs: [backend-test, frontend-test, runtime-test, security-scan]",
        "${{ secrets.DOCKER_USERNAME }}/dbooth-backend",
        "${{ secrets.DOCKER_USERNAME }}/dbooth-frontend",
    ],
    "D-Booth/frontend/package.json": [
        '"react": "^18.3.1"',
        '"react-dom": "^18.3.1"',
        '"@types/react": "^18.3.31"',
        '"@types/react-dom": "^18.3.7"',
    ],
}

BLOCKED_TEXT = {
    ".github/workflows/ci.yml": [
        "actions/create-release@v1",
        "@main",
        "@master",
        "continue-on-error: true",
        "dbooth/backend:",
        "dbooth/frontend:",
        "Add your deployment script here",
        "Deploying to staging environment",
        "Deploying to production environment",
        "safety check",
        "mypy app/",
    ],
    "Makefile": [
        "black . && isort . && mypy app/ && ruff check app/",
    ],
    "CLAUDE.md": [
        "pnpm typecheck",
        "pnpm test",
        "pnpm lint",
        "mypy app/",
    ],
    "CONTRIBUTING.md": [
        "推荐使用 pnpm",
        "pnpm install",
        "pnpm dev",
        "pnpm typecheck",
        "pnpm lint",
        "pnpm format",
        "使用 ESLint + Prettier",
        "mypy app",
        "使用 mypy 类型检查",
    ],
    "DEPLOYMENT.md": [
        "pnpm",
        "pnpm-lock.yaml",
    ],
    "DEVELOPER_GUIDE.md": [
        "pnpm",
        "pnpm-lock.yaml",
        "mypy app/",
        "npm run generate-types",
    ],
    "SECURITY.md": [
        "safety check",
        "pnpm audit",
    ],
    "TECH_STACK.md": [
        "**Safety** - Python 依赖安全检查",
        "**ESLint** - 代码检查",
        "**Prettier** - 代码格式化",
    ],
    "D-Booth/backend/requirements.txt": [
        "pywin32==308\n",
    ],
    "D-Booth/frontend/package.json": [
        '"@types/react": "^19',
        '"@types/react-dom": "^19',
        '"peerDependencies"',
        '"peerDependenciesMeta"',
    ],
    ".claude/settings.json": [
        "git add",
        "git commit",
        "git push",
        "VERSION=$(cat VERSION",
    ],
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        text=False,
    )
    return [
        path.decode("utf-8", errors="replace")
        for path in result.stdout.split(b"\0")
        if path
    ]


def untracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        text=False,
    )
    return [
        path.decode("utf-8", errors="replace")
        for path in result.stdout.split(b"\0")
        if path
    ]


def is_blocked(path: str) -> bool:
    parsed = PurePosixPath(path)
    parts = set(parsed.parts)
    filename = parsed.name

    return (
        path in BLOCKED_PATHS
        or bool(parts & BLOCKED_DIRS)
        or filename in BLOCKED_FILENAMES
        or any(filename.endswith(suffix) for suffix in BLOCKED_SUFFIXES)
    )


def read_repo_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def read_repo_json(path: str):
    return json.loads(read_repo_text(path))


def content_offenders() -> list[str]:
    offenders: list[str] = []

    for path in sorted(REQUIRED_PATHS):
        if not (ROOT / path).is_file():
            offenders.append(f"{path} is required for CI/CD reproducibility.")

    changelog = read_repo_text("CHANGELOG.md")
    unreleased_count = changelog.count("## [Unreleased]")
    if unreleased_count != 1:
        offenders.append(
            f"CHANGELOG.md must contain exactly one Unreleased section, found {unreleased_count}."
        )

    version_path = ROOT / "VERSION"
    if not version_path.is_file():
        offenders.append("VERSION is required as the canonical project version.")
    else:
        project_version = version_path.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+", project_version):
            offenders.append(f"VERSION must be SemVer MAJOR.MINOR.PATCH, found {project_version}.")
        else:
            readme = read_repo_text("README.md")
            config = read_repo_text("D-Booth/backend/app/core/config.py")
            version_badge = f"version-{project_version}-blue"
            config_default = f'VERSION: str = "{project_version}"'
            if version_badge not in readme:
                offenders.append(f"README.md version badge must match VERSION: {project_version}.")
            if config_default not in config:
                offenders.append(
                    f"D-Booth/backend/app/core/config.py VERSION default must match VERSION: {project_version}."
                )

            frontend_package = read_repo_json("D-Booth/frontend/package.json")
            frontend_lock = read_repo_json("D-Booth/frontend/package-lock.json")
            lock_root = frontend_lock.get("packages", {}).get("", {})
            if frontend_package.get("name") != "dbooth-frontend":
                offenders.append("D-Booth/frontend/package.json name must be dbooth-frontend.")
            if frontend_package.get("version") != project_version:
                offenders.append(
                    f"D-Booth/frontend/package.json version must match VERSION: {project_version}."
                )
            if frontend_lock.get("name") != "dbooth-frontend" or lock_root.get("name") != "dbooth-frontend":
                offenders.append("D-Booth/frontend/package-lock.json root name must be dbooth-frontend.")
            if frontend_lock.get("version") != project_version or lock_root.get("version") != project_version:
                offenders.append(
                    f"D-Booth/frontend/package-lock.json root version must match VERSION: {project_version}."
                )

    for path, patterns in EXPECTED_TEXT.items():
        content = read_repo_text(path)
        for pattern in patterns:
            if pattern not in content:
                offenders.append(f"{path} is missing required text: {pattern}")

    for path, patterns in BLOCKED_TEXT.items():
        content = read_repo_text(path)
        for pattern in patterns:
            if pattern in content:
                offenders.append(f"{path} contains blocked legacy text: {pattern}")

    return offenders


def main() -> int:
    tracked_offenders = sorted(path for path in tracked_files() if is_blocked(path))
    untracked_offenders = sorted(path for path in untracked_files() if is_blocked(path))
    text_offenders = content_offenders()
    if not tracked_offenders and not untracked_offenders and not text_offenders:
        print("Repository hygiene check passed.")
        return 0

    print("Repository hygiene check failed.")
    if tracked_offenders:
        print("Generated or local-only files are tracked.")
        print("Remove them from the Git index and keep the working copies local.")
    if untracked_offenders:
        print("Generated or local-only files are present in the working tree.")
        print("Remove them from the workspace or add an explicit ignore rule if they are intentional.")
    for path in tracked_offenders:
        print(f"- {path}")
    for path in untracked_offenders:
        print(f"- {path}")
    for offender in text_offenders:
        print(f"- {offender}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
