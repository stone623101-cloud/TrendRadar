# coding=utf-8
"""Render the unified TrendRadar HTML report page."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from trendradar.report.helpers import html_escape
from trendradar.report.page.builder import build_unified_page_data


def render_html_content(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    display_mode: str = "keyword",
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
    show_new_section: bool = True,
) -> str:
    """Render a single-file HTML report with a unified feed."""
    now = get_time_func() if get_time_func else datetime.now()
    page_data = build_unified_page_data(
        report_data,
        total_titles=total_titles,
        rss_items=rss_items,
        rss_new_items=rss_new_items,
        standalone_data=standalone_data,
    )
    payload = {
        "mode": mode,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "update_info": update_info or {},
        "report": page_data,
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    template = _load_template()
    return (
        template
        .replace("__PAYLOAD_JSON__", payload_json)
        .replace("__GENERATED_AT__", html_escape(payload["generated_at"]))
        .replace("__MODE__", html_escape(mode))
        .replace("__AI_CARD__", _render_ai_card(ai_analysis))
        .replace("__FAILED_SOURCES__", _render_failed_sources(report_data.get("failed_ids", [])))
    )


def _load_template() -> str:
    return (Path(__file__).with_name("template.html")).read_text(encoding="utf-8")


def _render_failed_sources(failed_ids: List[Any]) -> str:
    if not failed_ids:
        return ""
    items = []
    for failed in failed_ids:
        if isinstance(failed, dict):
            label = failed.get("name") or failed.get("id") or str(failed)
        else:
            label = str(failed)
        items.append(f"<li>{html_escape(label)}</li>")
    return f"""
        <section class="failed-sources" aria-label="请求失败的平台">
            <h2>请求失败的平台</h2>
            <ul>{''.join(items)}</ul>
        </section>
    """


def _render_ai_card(ai_analysis: Any) -> str:
    if not ai_analysis:
        return ""
    if not getattr(ai_analysis, "success", False):
        message = getattr(ai_analysis, "error", "") or ""
        if not message:
            return ""
        label = "AI 分析跳过" if getattr(ai_analysis, "skipped", False) else "AI 分析失败"
        return f"""
            <section class="ai-card is-status">
                <button class="ai-card-toggle" type="button" aria-expanded="false">
                    <span>{html_escape(label)}</span>
                    <span class="toggle-indicator">展开</span>
                </button>
                <div class="ai-card-body">
                    <p>{html_escape(str(message))}</p>
                </div>
            </section>
        """

    sections = [
        ("核心热点态势", getattr(ai_analysis, "core_trends", "")),
        ("舆论风向争议", getattr(ai_analysis, "sentiment_controversy", "")),
        ("异动与弱信号", getattr(ai_analysis, "signals", "")),
        ("RSS 深度洞察", getattr(ai_analysis, "rss_insights", "")),
        ("研判与策略建议", getattr(ai_analysis, "outlook_strategy", "")),
    ]
    summaries = [
        line
        for _, text in sections
        for line in _plain_lines(text)
    ][:3]
    if not summaries:
        return ""
    summary_html = "".join(f"<p>{html_escape(line)}</p>" for line in summaries)
    section_html = "".join(
        f"""
            <section class="ai-detail-block">
                <h3>{html_escape(title)}</h3>
                <p>{html_escape(str(text)).replace(chr(10), '<br>')}</p>
            </section>
        """
        for title, text in sections
        if text
    )
    return f"""
        <section class="ai-card">
            <button class="ai-card-toggle" type="button" aria-expanded="false">
                <span>今日要点</span>
                <span class="toggle-indicator">展开全文</span>
            </button>
            <div class="ai-summary">{summary_html}</div>
            <div class="ai-card-body">{section_html}</div>
        </section>
    """


def _plain_lines(text: Any) -> List[str]:
    if not text:
        return []
    lines = []
    for line in str(text).splitlines():
        cleaned = line.strip().lstrip("-*0123456789.、) ")
        if cleaned:
            lines.append(cleaned)
    return lines
