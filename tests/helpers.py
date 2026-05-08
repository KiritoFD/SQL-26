from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def path(relative_path: str) -> Path:
    return ROOT / relative_path


def read(relative_path: str) -> str:
    return path(relative_path).read_text(encoding="utf-8")


def exists(relative_path: str) -> bool:
    return path(relative_path).exists()


def read_many(*relative_paths: str) -> str:
    return "\n".join(read(relative_path) for relative_path in relative_paths)
