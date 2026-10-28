from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .config import ROOT


KNOWLEDGE_ROOT = ROOT / "demo_knowledge"
ALLOWED_SUFFIXES = {".md", ".markdown", ".mdx"}


@dataclass
class Section:
    file: str
    title: str
    line: int
    text: str


def list_files() -> list[str]:
    if not KNOWLEDGE_ROOT.exists():
        return []
    return sorted(
        str(path.relative_to(KNOWLEDGE_ROOT)).replace("\\", "/")
        for path in KNOWLEDGE_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
    )


def read_file(relative_path: str) -> str:
    root = KNOWLEDGE_ROOT.resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=400, detail="path traversal is not allowed")
    if target.suffix.lower() not in ALLOWED_SUFFIXES or not target.is_file():
        raise HTTPException(status_code=404, detail="knowledge file not found")
    return target.read_text(encoding="utf-8")


def split_sections(file: str, content: str) -> list[Section]:
    lines = content.splitlines()
    starts = [index for index, line in enumerate(lines) if re.match(r"^#{1,6}\s+", line)]
    if not starts:
        return [Section(file=file, title="(full text)", line=1, text=content)]
    sections: list[Section] = []
    if starts[0] > 0:
        sections.append(
            Section(file=file, title="(preface)", line=1, text="\n".join(lines[: starts[0]]))
        )
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else len(lines)
        title = re.sub(r"^#{1,6}\s+", "", lines[start]).strip()
        sections.append(
            Section(file=file, title=title, line=start + 1, text="\n".join(lines[start:end]))
        )
    return sections


def _terms(query: str) -> list[str]:
    normalized = str(query or "").strip().lower()
    if not normalized:
        return []
    values = {normalized}
    values.update(token for token in normalized.split() if len(token) >= 2)
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", normalized)
    values.update(cjk[index : index + 2] for index in range(max(0, len(cjk) - 1)))
    return [value for value in values if value]


def _snippet(text: str, terms: list[str], width: int = 420) -> str:
    text = "\n".join(
        line for line in text.splitlines()
        if not line.lstrip().startswith(("#", ">"))
    ).strip()
    haystack = text.lower()
    position = next((haystack.find(term) for term in terms if haystack.find(term) >= 0), 0)
    start = max(0, position - 90)
    return (
        ("..." if start else "")
        + text[start : start + width].strip()
        + ("..." if start + width < len(text) else "")
    )


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    terms = _terms(query)
    results: list[dict[str, Any]] = []
    for file in list_files():
        content = read_file(file)
        for section in split_sections(file, content):
            haystack = f"{section.title}\n{section.text}".lower()
            score = sum(haystack.count(term) * max(len(term), 2) for term in terms)
            if score <= 0:
                continue
            results.append(
                {
                    "file": section.file,
                    "title": section.title,
                    "line": section.line,
                    "score": score,
                    "snippet": _snippet(section.text, terms),
                    "ref": f"{section.file}#L{section.line}",
                }
            )
    results.sort(key=lambda item: (-item["score"], item["file"], item["line"]))
    return results[:limit]


def knowledge_files() -> list[dict[str, Any]]:
    return [
        {
            "path": file,
            "title": Path(file).stem.replace("-", " ").title(),
            "size": (KNOWLEDGE_ROOT / file).stat().st_size,
        }
        for file in list_files()
    ]
