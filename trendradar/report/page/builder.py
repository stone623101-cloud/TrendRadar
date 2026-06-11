# coding=utf-8
"""Build the unified report feed used by the HTML page."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
import string
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_CATEGORY = "其他"


@dataclass
class SourceRef:
    name: str
    rank: int = 0
    type: str = "hotlist"

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "rank": self.rank, "type": self.type}


@dataclass
class UnifiedItem:
    title: str
    url: str = ""
    mobile_url: str = ""
    sources: List[SourceRef] = field(default_factory=list)
    category: str = DEFAULT_CATEGORY
    keyword_group: str = ""
    is_new: bool = False
    time_display: str = ""
    published_at: str = ""
    heat: int = 0
    time_score: int = -1

    def as_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "mobile_url": self.mobile_url,
            "sources": [source.as_dict() for source in self.sources],
            "category": self.category or DEFAULT_CATEGORY,
            "keyword_group": self.keyword_group,
            "is_new": self.is_new,
            "time_display": self.time_display,
            "published_at": self.published_at,
            "heat": self.heat,
            "time_score": self.time_score,
        }


def build_unified_page_data(
    report_data: Dict[str, Any],
    *,
    total_titles: int = 0,
    rss_items: Optional[List[Dict[str, Any]]] = None,
    rss_new_items: Optional[List[Dict[str, Any]]] = None,
    standalone_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge hotlist, RSS, and standalone content into one sortable feed."""
    builder = _UnifiedFeedBuilder()
    rss_new_keys = _collect_item_keys_from_stats(rss_new_items or [])
    hotlist_new_keys = _collect_item_keys_from_new_titles(report_data.get("new_titles", []))

    for stat in report_data.get("stats", []) or []:
        builder.add_stat_group(stat, source_type="hotlist", new_keys=hotlist_new_keys)

    for stat in rss_items or []:
        builder.add_stat_group(stat, source_type="rss", new_keys=rss_new_keys)

    for platform in (standalone_data or {}).get("platforms", []) or []:
        builder.add_standalone_platform(platform)

    for feed in (standalone_data or {}).get("rss_feeds", []) or []:
        builder.add_standalone_rss(feed, new_keys=rss_new_keys)

    items = builder.items()
    category_counts: Dict[str, int] = {}
    for item in items:
        category = item.category or DEFAULT_CATEGORY
        category_counts[category] = category_counts.get(category, 0) + 1

    sorted_items = sorted(items, key=lambda item: (-item.heat, -item.time_score, item.title))
    return {
        "items": [item.as_dict() for item in sorted_items],
        "category_counts": category_counts,
        "total_count": len(sorted_items),
        "new_count": sum(1 for item in sorted_items if item.is_new),
        "source_count": sum(len(item.sources) for item in sorted_items),
        "input_total_titles": total_titles,
    }


class _UnifiedFeedBuilder:
    def __init__(self):
        self._items: List[UnifiedItem] = []
        self._url_index: Dict[str, UnifiedItem] = {}
        self._title_index: Dict[str, UnifiedItem] = {}

    def items(self) -> List[UnifiedItem]:
        return self._items

    def add_stat_group(
        self,
        stat: Dict[str, Any],
        *,
        source_type: str,
        new_keys: Optional[set] = None,
    ) -> None:
        keyword_group = str(stat.get("word", "") or "")
        category = str(stat.get("category", "") or DEFAULT_CATEGORY)
        for title_data in stat.get("titles", []) or []:
            title = str(title_data.get("title", "") or "").strip()
            if not title:
                continue
            url = str(title_data.get("url", "") or "")
            mobile_url = str(
                title_data.get("mobileUrl")
                or title_data.get("mobile_url")
                or ""
            )
            ranks = _coerce_ranks(title_data.get("ranks", []))
            best_rank = min(ranks) if ranks else 0
            is_new = bool(title_data.get("is_new", False))
            if _matches_keys(title, url, new_keys):
                is_new = True
            item = UnifiedItem(
                title=title,
                url=url,
                mobile_url=mobile_url,
                sources=[
                    SourceRef(
                        name=str(title_data.get("source_name") or keyword_group or source_type.upper()),
                        rank=best_rank,
                        type=source_type,
                    )
                ],
                category=category,
                keyword_group=keyword_group,
                is_new=is_new,
                time_display=str(title_data.get("time_display", "") or ""),
                published_at=str(title_data.get("published_at", "") or ""),
            )
            self._merge(item)

    def add_standalone_platform(self, platform: Dict[str, Any]) -> None:
        source_name = str(platform.get("name") or platform.get("id") or "独立展示")
        category = str(platform.get("category") or DEFAULT_CATEGORY)
        for raw_item in platform.get("items", []) or []:
            title = str(raw_item.get("title", "") or "").strip()
            if not title:
                continue
            ranks = _coerce_ranks(raw_item.get("ranks", []))
            rank = _coerce_int(raw_item.get("rank", 0))
            if rank and rank not in ranks:
                ranks.append(rank)
            best_rank = min(ranks) if ranks else rank
            item = UnifiedItem(
                title=title,
                url=str(raw_item.get("url", "") or ""),
                mobile_url=str(raw_item.get("mobileUrl") or raw_item.get("mobile_url") or ""),
                sources=[SourceRef(name=source_name, rank=best_rank, type="standalone")],
                category=category,
                keyword_group="",
                is_new=bool(raw_item.get("is_new", False)),
                time_display=_format_standalone_time(raw_item),
            )
            self._merge(item)

    def add_standalone_rss(self, feed: Dict[str, Any], *, new_keys: Optional[set] = None) -> None:
        source_name = str(feed.get("name") or feed.get("id") or "RSS")
        category = str(feed.get("category") or DEFAULT_CATEGORY)
        for raw_item in feed.get("items", []) or []:
            title = str(raw_item.get("title", "") or "").strip()
            if not title:
                continue
            url = str(raw_item.get("url", "") or "")
            item = UnifiedItem(
                title=title,
                url=url,
                sources=[SourceRef(name=source_name, rank=0, type="standalone")],
                category=category,
                keyword_group="",
                is_new=_matches_keys(title, url, new_keys),
                time_display=str(raw_item.get("published_at", "") or ""),
                published_at=str(raw_item.get("published_at", "") or ""),
            )
            self._merge(item)

    def _merge(self, incoming: UnifiedItem) -> None:
        incoming.time_score = _time_score(incoming.published_at or incoming.time_display)
        incoming.heat = _calculate_heat(incoming.sources)
        key_url = _normalize_url(incoming.url)
        key_title = _normalize_title(incoming.title)

        existing = None
        if key_url:
            existing = self._url_index.get(key_url)
        if existing is None and key_title:
            existing = self._title_index.get(key_title)

        if existing is None:
            self._items.append(incoming)
            if key_url:
                self._url_index[key_url] = incoming
            if key_title:
                self._title_index[key_title] = incoming
            return

        if incoming.url and not existing.url:
            existing.url = incoming.url
        if incoming.mobile_url and not existing.mobile_url:
            existing.mobile_url = incoming.mobile_url
        if incoming.keyword_group and not existing.keyword_group:
            existing.keyword_group = incoming.keyword_group
        if existing.category == DEFAULT_CATEGORY and incoming.category != DEFAULT_CATEGORY:
            existing.category = incoming.category
        existing.is_new = existing.is_new or incoming.is_new
        existing.sources = _merge_sources(existing.sources, incoming.sources)
        if incoming.time_score > existing.time_score:
            existing.time_score = incoming.time_score
            existing.time_display = incoming.time_display or existing.time_display
            existing.published_at = incoming.published_at or existing.published_at
        elif not existing.time_display and incoming.time_display:
            existing.time_display = incoming.time_display
        if key_url:
            self._url_index[key_url] = existing
        if key_title:
            self._title_index[key_title] = existing
        existing.heat = _calculate_heat(existing.sources)


def _collect_item_keys_from_stats(stats: Iterable[Dict[str, Any]]) -> set:
    keys = set()
    for stat in stats or []:
        for item in stat.get("titles", []) or []:
            _add_keys(keys, item.get("title", ""), item.get("url", ""))
    return keys


def _collect_item_keys_from_new_titles(new_titles: Iterable[Dict[str, Any]]) -> set:
    keys = set()
    for source_group in new_titles or []:
        for item in source_group.get("titles", []) or []:
            _add_keys(keys, item.get("title", ""), item.get("url", ""))
    return keys


def _add_keys(keys: set, title: Any, url: Any) -> None:
    normalized_url = _normalize_url(str(url or ""))
    normalized_title = _normalize_title(str(title or ""))
    if normalized_url:
        keys.add(("url", normalized_url))
    if normalized_title:
        keys.add(("title", normalized_title))


def _matches_keys(title: str, url: str, keys: Optional[set]) -> bool:
    if not keys:
        return False
    normalized_url = _normalize_url(url)
    normalized_title = _normalize_title(title)
    return (
        bool(normalized_url and ("url", normalized_url) in keys)
        or bool(normalized_title and ("title", normalized_title) in keys)
    )


def _normalize_url(url: str) -> str:
    return str(url or "").strip()


def _normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(title or "")).casefold()
    return "".join(
        char
        for char in normalized
        if not char.isspace()
        and char not in string.punctuation
        and not unicodedata.category(char).startswith("P")
    )


def _coerce_ranks(value: Any) -> List[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    ranks = []
    for raw_rank in value:
        rank = _coerce_int(raw_rank)
        if rank > 0:
            ranks.append(rank)
    return ranks


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _merge_sources(existing: List[SourceRef], incoming: List[SourceRef]) -> List[SourceRef]:
    seen = {(source.name, source.rank, source.type) for source in existing}
    merged = list(existing)
    for source in incoming:
        key = (source.name, source.rank, source.type)
        if key not in seen:
            merged.append(source)
            seen.add(key)
    return sorted(merged, key=lambda source: (_source_priority(source.type), source.rank or 9999, source.name))


def _source_priority(source_type: str) -> int:
    return {"hotlist": 0, "rss": 1, "standalone": 2}.get(source_type, 9)


def _calculate_heat(sources: List[SourceRef]) -> int:
    hotlist_sources = [source for source in sources if source.type == "hotlist"]
    if not hotlist_sources:
        return 0
    best_rank = min((source.rank for source in hotlist_sources if source.rank > 0), default=100)
    return len({source.name for source in hotlist_sources}) * 100 + (100 - min(best_rank, 100))


def _time_score(raw_time: str) -> int:
    text = str(raw_time or "").strip()
    if not text:
        return -1
    iso_text = text.replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(iso_text).timestamp())
    except ValueError:
        pass
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour * 60 + minute
    return -1


def _format_standalone_time(item: Dict[str, Any]) -> str:
    first_time = str(item.get("first_time", "") or "")
    last_time = str(item.get("last_time", "") or "")
    if first_time and last_time and first_time != last_time:
        return f"{_display_hotlist_time(first_time)} ~ {_display_hotlist_time(last_time)}"
    if first_time:
        return _display_hotlist_time(first_time)
    return str(item.get("published_at", "") or "")


def _display_hotlist_time(value: str) -> str:
    return str(value or "").replace("-", ":")
