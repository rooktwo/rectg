from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Candidate:
    url: str
    username: str
    name: str = ""
    type_hint: str | None = None
    page_url: str = ""


@dataclass(frozen=True)
class SourceSpec:
    name: str
    url: str
    selector: str
    mentions: bool = False
    attributes: tuple[str, ...] = ()
    username_routes: tuple[str, ...] = ()
    follow: tuple[str, ...] = ()
    browser_when_empty: bool = False
    browser_wait_for: str = ""


@dataclass
class SourceResult:
    source_id: str
    source_url: str
    status: str = "success"
    pages: int = 0
    candidates: list[Candidate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
