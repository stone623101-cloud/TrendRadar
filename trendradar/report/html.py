# coding=utf-8
"""
HTML 报告渲染模块

提供 HTML 格式的热点新闻报告生成功能
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape, calculate_rank_trend
from trendradar.utils.time import convert_time_for_display
from trendradar.ai.formatter import render_ai_analysis_html_rich


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
    """渲染HTML内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        total_titles: 新闻总数
        mode: 报告模式 ("daily", "current", "incremental")
        update_info: 更新信息（可选）
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now）
        rss_items: RSS 统计条目列表（可选）
        rss_new_items: RSS 新增条目列表（可选）
        display_mode: 显示模式 ("keyword"=按关键词分组, "platform"=按平台分组)
        standalone_data: 独立展示区数据（可选），包含 platforms 和 rss_feeds
        ai_analysis: AI 分析结果对象（可选），AIAnalysisResult 实例
        show_new_section: 是否显示新增热点区域

    Returns:
        渲染后的 HTML 字符串
    """
    # 默认区域顺序
    default_region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
    if region_order is None:
        region_order = default_region_order

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>热点新闻分析</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap" rel="stylesheet" />
        <style>
            :root {
                --font-ui: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
                --font-title: "Newsreader", Georgia, "Times New Roman", serif;
                --bg: #faf9f7;
                --bg-outer: #f0eee9;
                --ink: #2a2824;
                --ink-2: #4a4642;
                --muted: #9a9690;
                --faint: #b8b4ac;
                --line: #e0dbd2;
                --line-2: #ece8e0;
                --panel: #f4f1ea;
                --hi: #c2610a;
                --ok: #4a6b48;
                --err: #991b1b;
                --link: #1a5c8a;
            }
            * { box-sizing: border-box; }
            body {
                font-family: var(--font-ui);
                margin: 0;
                padding: 20px 16px;
                background: var(--bg-outer);
                color: var(--ink);
                line-height: 1.55;
                font-size: 14px;
            }

            .container {
                max-width: 660px;
                margin: 0 auto;
                background: var(--bg);
                border: 1px solid var(--line);
                overflow: hidden;
            }

            .header {
                background: #1a1814;
                color: #f5f2ed;
                padding: 28px 24px 22px;
                position: relative;
                overflow: visible;
                border-bottom: 1px solid #2e2a26;
            }

            .header-watermark {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: clamp(40px, 8vw, 80px);
                font-weight: 900;
                letter-spacing: 0.05em;
                color: rgba(255, 255, 255, 0.05);
                pointer-events: none;
                z-index: 1;
                white-space: nowrap;
                user-select: none;
            }

            .save-buttons {
                position: absolute;
                top: 16px;
                right: 16px;
                display: flex;
                gap: 8px;
                z-index: 10;
            }

            .save-btn-group {
                position: relative;
                display: flex;
            }

            .save-btn {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #f5f2ed;
                padding: 8px 16px;
                border-radius: 2px 0 0 2px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                font-family: var(--font-ui);
                transition: background 0.15s;
                white-space: nowrap;
                min-height: 34px;
                border-right: none;
            }

            .save-btn:hover {
                background: rgba(255, 255, 255, 0.18);
            }

            .save-btn:active {
                transform: translateY(0);
            }

            .save-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .save-dropdown-trigger {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #f5f2ed;
                padding: 8px 10px;
                border-radius: 0 2px 2px 0;
                cursor: pointer;
                font-size: 11px;
                transition: background 0.15s;
                min-height: 34px;
                display: flex;
                align-items: center;
            }

            .save-dropdown-trigger:hover {
                background: rgba(255, 255, 255, 0.18);
            }

            .save-dropdown-menu {
                position: absolute;
                top: 100%;
                right: 0;
                margin-top: 4px;
                background: #fff;
                border: 1px solid var(--line);
                border-radius: 2px;
                padding: 4px;
                min-width: 140px;
                opacity: 0;
                visibility: hidden;
                transform: translateY(-4px);
                transition: all 0.15s;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
                z-index: 20;
            }

            .save-btn-group:hover .save-dropdown-menu,
            .save-dropdown-menu:hover {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }

            .save-dropdown-item {
                display: flex;
                align-items: center;
                width: 100%;
                padding: 8px 12px;
                background: none;
                border: none;
                color: var(--ink);
                font-size: 13px;
                font-family: var(--font-ui);
                cursor: pointer;
                text-align: left;
                transition: background 0.1s;
                white-space: nowrap;
            }

            .save-dropdown-item:hover {
                background: var(--panel);
                color: var(--hi);
            }

            .dropdown-icon {
                width: 14px;
                height: 14px;
                margin-right: 8px;
                vertical-align: -2px;
                flex-shrink: 0;
            }

            .header-title {
                font-family: var(--font-title);
                font-size: 26px;
                font-weight: 600;
                margin: 0 0 18px 0;
                position: relative;
                z-index: 2;
                letter-spacing: 0;
                line-height: 1.2;
                color: #f5f2ed;
            }

            .header-info {
                position: relative;
                z-index: 2;
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 12px;
                font-size: 12px;
                border-top: 1px solid rgba(255,255,255,0.12);
                padding-top: 14px;
            }

            .info-item {
                text-align: left;
            }

            .info-label {
                display: block;
                font-size: 10px;
                opacity: 0.5;
                margin-bottom: 3px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .info-value {
                font-weight: 600;
                font-size: 13px;
                color: #f5f2ed;
            }

            .content {
                padding: 0;
            }

            .word-group {
                margin-bottom: 0;
                border-bottom: 1px solid var(--line-2);
            }

            .word-group:last-child {
                border-bottom: none;
            }

            .word-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 20px 10px;
                background: var(--panel);
                border-bottom: 1px solid var(--line-2);
            }

            .word-info {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .word-name {
                font-family: var(--font-ui);
                font-size: 11px;
                font-weight: 700;
                color: var(--ink);
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .word-count {
                color: var(--muted);
                font-size: 12px;
                font-weight: 500;
            }

            .word-count.hot { color: var(--err); font-weight: 700; }
            .word-count.warm { color: var(--hi); font-weight: 600; }

            .word-index {
                color: var(--faint);
                font-size: 11px;
            }

            .news-item {
                padding: 11px 20px;
                border-bottom: 1px solid var(--line-2);
                position: relative;
                display: flex;
                gap: 10px;
                align-items: flex-start;
            }

            .news-item:last-child {
                border-bottom: none;
            }

            .news-item.new::after {
                content: "NEW";
                position: absolute;
                top: 11px;
                right: 20px;
                background: #fbbf24;
                color: #92400e;
                font-size: 9px;
                font-weight: 700;
                padding: 2px 5px;
                border-radius: 2px;
                letter-spacing: 0.5px;
            }

            .news-number {
                color: var(--faint);
                font-size: 11px;
                font-weight: 600;
                min-width: 18px;
                text-align: center;
                flex-shrink: 0;
                background: var(--line-2);
                border-radius: 50%;
                width: 22px;
                height: 22px;
                display: flex;
                align-items: center;
                justify-content: center;
                align-self: flex-start;
                margin-top: 1px;
                position: relative;
                cursor: pointer;
                transition: background 0.15s, color 0.15s;
            }
            .news-number .num-text { transition: opacity 0.15s; }
            .news-number .copy-icon {
                position: absolute;
                opacity: 0;
                transition: opacity 0.15s;
            }
            .news-item:hover .news-number .num-text { opacity: 0; }
            .news-item:hover .news-number .copy-icon { opacity: 1; }
            .news-item:hover .news-number {
                background: #fef3e8;
                color: var(--hi);
            }
            .news-number.copied {
                background: #ecfdf5 !important;
            }
            .news-number.copied .num-text { opacity: 0 !important; }
            .news-number.copied .copy-icon { opacity: 1 !important; }
            body.dark-mode .news-item:hover .news-number {
                background: #3a2a18;
                color: #e0a060;
            }
            body.dark-mode .news-number.copied {
                background: #1a2e20 !important;
            }

            .news-content {
                flex: 1;
                min-width: 0;
                padding-right: 40px;
            }

            .news-item.new .news-content {
                padding-right: 52px;
            }

            .news-header {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 4px;
                flex-wrap: wrap;
            }

            .source-name {
                color: var(--muted);
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .keyword-tag {
                color: var(--link);
                font-size: 11px;
                font-weight: 500;
                background: #e4eef6;
                padding: 1px 5px;
                border-radius: 2px;
            }

            .rank-num {
                color: #fff;
                background: var(--muted);
                font-size: 10px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 2px;
                min-width: 16px;
                text-align: center;
            }

            .rank-num.top { background: var(--err); }
            .rank-num.high { background: var(--hi); }

            .trend-up, .trend-down {
                font-size: 11px;
                margin-left: 2px;
                vertical-align: middle;
            }

            .time-info {
                color: var(--faint);
                font-size: 11px;
            }

            .count-info {
                color: var(--ok);
                font-size: 11px;
                font-weight: 600;
            }

            .news-title {
                font-family: var(--font-title);
                font-size: 15px;
                line-height: 1.4;
                color: var(--ink);
                margin: 0;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 8px;
                width: 100%;
            }

            .news-link {
                color: var(--ink);
                text-decoration: none;
                flex: 1 1 auto;
                min-width: 0;
            }

            .news-link:hover {
                color: var(--hi);
            }

            .news-link:visited {
                color: var(--ink-2);
            }

            /* 通用区域分割线样式 */
            .section-divider {
                margin-top: 0;
                padding-top: 0;
                border-top: 2px solid var(--line);
            }

            /* 热榜统计区样式 */
            .hotlist-section { }

            .new-section {
                border-top: 2px solid var(--line);
                padding: 18px 20px;
            }

            .new-section-title {
                color: var(--ink);
                font-size: 11px;
                font-weight: 700;
                margin: 0 0 14px 0;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .new-source-group {
                margin-bottom: 18px;
            }

            .new-source-title {
                color: var(--muted);
                font-size: 11px;
                font-weight: 600;
                margin: 0 0 10px 0;
                padding-bottom: 5px;
                border-bottom: 1px solid var(--line-2);
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .new-item {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 7px 0;
                border-bottom: 1px solid var(--line-2);
            }

            .new-item:last-child {
                border-bottom: none;
            }

            .new-item-number {
                color: var(--faint);
                font-size: 11px;
                font-weight: 600;
                min-width: 16px;
                text-align: center;
                flex-shrink: 0;
                background: var(--line-2);
                border-radius: 50%;
                width: 18px;
                height: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .new-item-rank {
                color: #fff;
                background: var(--muted);
                font-size: 10px;
                font-weight: 700;
                padding: 2px 5px;
                border-radius: 2px;
                min-width: 18px;
                text-align: center;
                flex-shrink: 0;
            }

            .new-item-rank.top { background: var(--err); }
            .new-item-rank.high { background: var(--hi); }

            .new-item-content {
                flex: 1;
                min-width: 0;
            }

            .new-item-title {
                font-family: var(--font-title);
                font-size: 14px;
                line-height: 1.4;
                color: var(--ink);
                margin: 0;
            }

            .error-section {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 2px;
                padding: 14px;
                margin: 16px 20px;
            }

            .error-title {
                color: var(--err);
                font-size: 13px;
                font-weight: 600;
                margin: 0 0 8px 0;
            }

            .error-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }

            .error-item {
                color: #991b1b;
                font-size: 12px;
                padding: 2px 0;
                font-family: 'SF Mono', Consolas, monospace;
            }

            .footer {
                padding: 16px 20px;
                background: var(--panel);
                border-top: 1px solid var(--line);
                text-align: center;
            }

            .footer-content {
                font-size: 12px;
                color: var(--muted);
                line-height: 1.6;
            }

            .footer-link {
                color: var(--hi);
                text-decoration: none;
                font-weight: 500;
            }

            .footer-link:hover {
                text-decoration: underline;
            }

            .project-name {
                font-weight: 600;
                color: var(--ink-2);
            }

            @media (max-width: 480px) {
                body { padding: 0; }
                .container { border: none; }
                .header { padding: 20px 16px; }
                .header-info { grid-template-columns: repeat(2, 1fr); }
                .word-header { padding: 10px 16px; }
                .news-item { padding: 10px 16px; gap: 8px; }
                .news-content { padding-right: 36px; }
                .new-section { padding: 14px 16px; }
                .news-number { width: 20px; height: 20px; font-size: 11px; }
                .save-buttons {
                    position: static;
                    margin-bottom: 14px;
                    display: flex;
                    gap: 6px;
                    justify-content: center;
                    width: 100%;
                }
                .save-btn-group {
                    flex: 1;
                }
                .save-btn {
                    width: 100%;
                }
            }

            /* RSS 订阅内容样式 */
            .rss-section,
            .standalone-section,
            .ai-section {
                border-top: 2px solid var(--line);
            }
            .section-divider.rss-section,
            .section-divider.standalone-section,
            .section-divider.ai-section {
                border-top: none;
            }

            .rss-section-header,
            .standalone-section-header,
            .ai-section-header {
                display: flex;
                align-items: center;
                justify-content: flex-start;
                gap: 8px;
                padding: 12px 20px 10px;
                background: var(--panel);
                border-bottom: 1px solid var(--line-2);
            }

            .rss-section-title,
            .standalone-section-title,
            .ai-section-title {
                font-size: 11px;
                font-weight: 700;
                color: var(--ok);
                letter-spacing: 0.08em;
                text-transform: uppercase;
                min-width: 0;
            }

            .rss-section-count,
            .standalone-section-count,
            .ai-section-badge {
                color: var(--muted);
                font-size: 12px;
                margin-left: auto;
            }

            .feed-group {
                border-bottom: 1px solid var(--line-2);
            }

            .feed-group:last-child {
                border-bottom: none;
            }

            .feed-header,
            .standalone-header,
            .ai-block-header {
                display: flex;
                align-items: center;
                justify-content: flex-start;
                gap: 8px;
                padding: 9px 20px 8px;
                border-bottom: 1px solid var(--line-2);
                background: var(--bg);
            }

            .feed-header {
                border-left: 2px solid var(--ok);
            }

            .feed-name,
            .standalone-name,
            .ai-block-title {
                font-size: 11px;
                font-weight: 700;
                color: var(--ink);
                letter-spacing: 0.06em;
                text-transform: uppercase;
                min-width: 0;
            }

            .feed-name {
                color: var(--ok);
            }

            .feed-count,
            .standalone-count,
            .ai-block-count {
                color: var(--muted);
                font-size: 12px;
            }

            .rss-item {
                padding: 10px 20px;
                border-bottom: 1px solid var(--line-2);
                border-left: 2px solid var(--ok);
            }

            .rss-item:last-child {
                border-bottom: none;
            }

            .rss-meta {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 4px;
                flex-wrap: wrap;
            }

            .rss-time {
                color: var(--faint);
                font-size: 11px;
            }

            .rss-author {
                color: var(--ok);
                font-size: 11px;
                font-weight: 600;
            }

            .rss-title {
                font-family: var(--font-title);
                font-size: 14px;
                line-height: 1.45;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 8px;
                width: 100%;
            }

            .rss-link {
                color: var(--ink);
                text-decoration: none;
                flex: 1 1 auto;
                min-width: 0;
            }

            .rss-link:hover {
                color: var(--ok);
            }

            .rss-summary {
                font-size: 12px;
                color: var(--muted);
                line-height: 1.5;
                margin: 0;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }

            /* 独立展示区样式 */
            .standalone-group {
                border-bottom: 1px solid var(--line-2);
            }

            .standalone-group:last-child {
                border-bottom: none;
            }

            /* AI 分析区块样式 */
            .ai-section-title {
                color: var(--hi);
            }

            .ai-section-badge {
                color: var(--hi);
                font-weight: 700;
            }

            .ai-block {
                background: var(--panel);
                border-bottom: 1px solid var(--line-2);
            }

            .ai-block:last-child {
                border-bottom: none;
            }

            .ai-block-title {
                color: var(--hi);
            }

            .ai-block-count {
                color: var(--muted);
                font-size: 12px;
            }

            .ai-block-content {
                font-family: var(--font-title);
                font-size: 14px;
                line-height: 1.65;
                color: var(--ink-2);
                white-space: pre-wrap;
                padding: 12px 20px 14px;
            }

            .ai-error,
            .ai-warning,
            .ai-info {
                margin: 14px 20px;
                padding: 14px;
                border-radius: 2px;
                font-size: 13px;
            }

            .ai-error {
                background: #fef2f2;
                border: 1px solid #fecaca;
                color: #991b1b;
            }

            .ai-warning {
                background: #fffbeb;
                border: 1px solid #fde68a;
                color: #92400e;
            }

            .ai-info {
                background: #f0f9ff;
                border: 1px solid #bae6fd;
                color: #0369a1;
            }

            /* ===== 浏览器增强样式 ===== */

            /* 宽屏模式 */
            body.wide-mode .container { max-width: 1280px; }
            body.wide-mode .header-info { grid-template-columns: repeat(8, 1fr); }
            body.wide-mode .rss-feeds-grid { display: grid; grid-template-columns: 1fr 1fr; }
            body.wide-mode .feed-group { margin-bottom: 0; }
            body.wide-mode .ai-section .ai-blocks-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
            body.wide-mode .ai-block { margin-bottom: 0; }
            body.wide-mode .new-section .new-sources-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            body.wide-mode .new-source-group { margin-bottom: 0; }
            body.wide-mode .standalone-section .standalone-groups-grid { display: grid; grid-template-columns: 1fr 1fr; }
            body.wide-mode .standalone-group { margin-bottom: 0; }

            /* Tab 栏 */
            .tab-bar-wrapper {
                position: sticky; top: 0; z-index: 10;
                background: var(--bg); display: none;
                align-items: stretch; border-bottom: 1px solid var(--line);
            }
            body.wide-mode .tab-bar-wrapper { display: flex; }
            body.wide-mode .tab-bar-wrapper.tab-hidden { display: none; }

            .tab-bar {
                flex: 1; min-width: 0; display: flex; overflow-x: auto;
                white-space: nowrap; padding: 0 20px;
                -webkit-overflow-scrolling: touch; scrollbar-width: none; -ms-overflow-style: none; gap: 0;
                mask-image: linear-gradient(to right, transparent, black 24px, black calc(100% - 24px), transparent);
                -webkit-mask-image: linear-gradient(to right, transparent, black 24px, black calc(100% - 24px), transparent);
            }
            .tab-bar::-webkit-scrollbar { display: none; }
            .tab-bar.scroll-start { mask-image: linear-gradient(to right, black, black calc(100% - 24px), transparent); -webkit-mask-image: linear-gradient(to right, black, black calc(100% - 24px), transparent); }
            .tab-bar.scroll-end { mask-image: linear-gradient(to right, transparent, black 24px, black); -webkit-mask-image: linear-gradient(to right, transparent, black 24px, black); }
            .tab-bar.scroll-start.scroll-end, .tab-bar.no-overflow { mask-image: none; -webkit-mask-image: none; }

            .tab-arrow {
                flex-shrink: 0; width: 28px; display: none; align-items: center; justify-content: center;
                background: none; border: none; color: var(--faint); font-size: 18px; cursor: pointer; padding: 0; transition: color 0.15s;
            }
            .tab-arrow:hover { color: var(--hi); }
            .tab-arrow.visible { display: flex; }

            .tab-scroll-indicator { position: absolute; bottom: 0; left: 0; width: 0; height: 2px; background: var(--hi); transition: width 0.1s linear; }

            .tab-btn {
                display: inline-flex; align-items: center; gap: 5px;
                padding: 10px 14px 11px; border: none; background: none;
                color: var(--muted); border-bottom: 2px solid transparent;
                cursor: pointer; font-size: 11px; font-weight: 700;
                font-family: var(--font-ui); letter-spacing: 0.07em; text-transform: uppercase;
                white-space: nowrap; transition: all 0.15s; flex-shrink: 0;
            }
            .tab-btn:hover { color: var(--ink); }
            .tab-btn.active { color: var(--ink); border-bottom-color: var(--ink); }
            .tab-count { font-size: 10px; background: var(--line-2); padding: 1px 5px; border-radius: 8px; }
            .tab-btn.active .tab-count { background: var(--line); }

            /* 搜索栏 */
            .search-bar { display: none; padding: 10px 20px; border-bottom: 1px solid var(--line); }
            .search-input {
                width: 100%; padding: 8px 14px; border: 1px solid var(--line);
                background: var(--bg); color: var(--ink);
                font-size: 13px; font-family: var(--font-ui);
                outline: none; transition: border-color 0.15s; box-sizing: border-box; border-radius: 2px;
            }
            .search-input:focus { border-color: var(--hi); }
            .search-input::placeholder { color: var(--faint); }

            /* 右下角悬浮工具栏 */
            .fab-bar {
                position: fixed; bottom: 24px; right: 24px; display: flex;
                flex-direction: column; gap: 8px; z-index: 100;
                opacity: 0; transform: translateY(10px);
                transition: opacity 0.3s, transform 0.3s; pointer-events: none;
            }
            .fab-bar.visible { opacity: 1; transform: translateY(0); pointer-events: auto; }
            .fab-btn {
                width: 38px; height: 38px; border-radius: 50%; background: var(--hi); color: white;
                border: none; cursor: pointer; font-size: 15px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: transform 0.2s, background 0.2s;
                display: flex; align-items: center; justify-content: center; position: relative;
            }
            .fab-btn:hover { transform: scale(1.1); background: #a0500a; }
            body.dark-mode .fab-btn { background: #c2610a; }
            body.dark-mode .fab-btn:hover { background: #d47020; }

            /* 快捷键 tooltip */
            .fab-tooltip {
                position: absolute; bottom: 0; right: 50px;
                background: rgba(26,24,20,0.95); color: #f5f2ed;
                border-radius: 4px; padding: 10px 14px; white-space: nowrap;
                font-size: 12px; font-family: var(--font-ui); line-height: 1.8;
                box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                opacity: 0; visibility: hidden; transform: translateY(6px);
                transition: all 0.2s; pointer-events: none;
            }
            .fab-btn:hover .fab-tooltip, .fab-btn.show-tip .fab-tooltip { opacity: 1; visibility: visible; transform: translateY(0); pointer-events: auto; }
            .fab-tooltip .tip-row { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
            .fab-tooltip .tip-key { background: rgba(255,255,255,0.15); border-radius: 2px; padding: 1px 6px; font-size: 11px; margin-left: 8px; }

            /* 折叠/展开 */
            .collapse-icon { display: none; margin-right: 6px; font-size: 11px; color: var(--faint); transition: transform 0.2s; user-select: none; }
            .word-header.collapsible, .rss-section-header.collapsible, .feed-header.collapsible, .ai-block-header.collapsible, .ai-section-header.collapsible, .standalone-section-header.collapsible, .standalone-header.collapsible { cursor: pointer; }
            .word-header.collapsible .collapse-icon, .rss-section-header.collapsible .collapse-icon, .feed-header.collapsible .collapse-icon, .ai-block-header.collapsible .collapse-icon, .ai-section-header.collapsible .collapse-icon, .standalone-section-header.collapsible .collapse-icon, .standalone-header.collapsible .collapse-icon { display: inline; }
            .word-header.collapsible:hover, .rss-section-header.collapsible:hover, .feed-header.collapsible:hover, .ai-block-header.collapsible:hover, .ai-section-header.collapsible:hover, .standalone-section-header.collapsible:hover, .standalone-header.collapsible:hover { background: #ebe8e0; }
            .word-group.collapsed .news-item { display: none; }
            .word-group.collapsed .collapse-icon { transform: rotate(-90deg); }
            .rss-section.collapsed .rss-feeds-grid { display: none; }
            .rss-section.collapsed .collapse-icon { transform: rotate(-90deg); }
            .feed-group.collapsed .rss-item { display: none; }
            .feed-group.collapsed .collapse-icon { transform: rotate(-90deg); }
            .ai-block.collapsed .ai-block-content { display: none; }
            .ai-block.collapsed .collapse-icon { transform: rotate(-90deg); }
            .ai-section.collapsed .ai-blocks-grid { display: none; }
            .ai-section.collapsed .collapse-icon { transform: rotate(-90deg); }
            .standalone-section.collapsed .standalone-groups-grid { display: none; }
            .standalone-section.collapsed .collapse-icon { transform: rotate(-90deg); }
            .standalone-group.collapsed .news-item, .standalone-group.collapsed .rss-item { display: none; }
            .standalone-group.collapsed .collapse-icon { transform: rotate(-90deg); }

            /* Tab 切换动画 */
            body.wide-mode .word-group[data-tab-index] { animation: tabFadeIn 0.2s ease; }
            @keyframes tabFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

            /* 宽屏切换按钮 */
            .toggle-wide-btn {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #f5f2ed;
                padding: 8px 12px; border-radius: 2px; cursor: pointer;
                font-size: 14px; transition: background 0.15s; line-height: 1; min-height: 34px;
            }
            .toggle-wide-btn:hover { background: rgba(255, 255, 255, 0.18); }

            /* ===== 暗色模式 ===== */
            body.dark-mode { background: #1a1814; color: #e0dbd2; }
            body.dark-mode .container { background: #221e1a; border-color: #2e2a26; }
            body.dark-mode .header { background: #111009; border-bottom-color: #2e2a26; }
            body.dark-mode .word-header { background: #1e1b17; border-bottom-color: #2e2a26; }
            body.dark-mode .word-name, body.dark-mode .new-section-title, body.dark-mode .standalone-name, body.dark-mode .new-item-title, body.dark-mode .project-name { color: #e0dbd2; }
            body.dark-mode .word-count, body.dark-mode .word-index, body.dark-mode .source-name, body.dark-mode .time-info, body.dark-mode .feed-count, body.dark-mode .new-source-title, body.dark-mode .standalone-count, body.dark-mode .ai-block-count, body.dark-mode .rss-section-count, body.dark-mode .standalone-section-count, body.dark-mode .ai-section-badge, body.dark-mode .rss-time, body.dark-mode .rss-summary { color: #9a9690; }
            body.dark-mode .info-value { color: #e0dbd2; }
            body.dark-mode .news-link, body.dark-mode .rss-link { color: #c8c4bc; }
            body.dark-mode .news-link:hover { color: #e0a060; }
            body.dark-mode .news-link:visited { color: #a8a4a0; }
            body.dark-mode .rss-link:hover { color: #7aab78; }
            body.dark-mode .keyword-tag { background: #2a2420; color: #93b8d4; }
            body.dark-mode .count-info { color: #7aab78; }
            body.dark-mode .rss-author, body.dark-mode .feed-name, body.dark-mode .rss-section-title, body.dark-mode .standalone-section-title { color: #7aab78; }
            body.dark-mode .news-item, body.dark-mode .new-item, body.dark-mode .standalone-item, body.dark-mode .new-source-title { border-bottom-color: #2e2a26; }
            body.dark-mode .standalone-header, body.dark-mode .ai-block-header { border-bottom-color: #2e2a26; background: #221e1a; }
            body.dark-mode .section-divider { border-top-color: #2e2a26; }
            body.dark-mode .feed-header { border-bottom-color: #2e2a26; border-left-color: #4a6b48; background: #1e2218; }
            body.dark-mode .news-number, body.dark-mode .new-item-number { background: #2e2a26; color: #6b6760; }
            body.dark-mode .word-header.collapsible:hover, body.dark-mode .rss-section-header.collapsible:hover, body.dark-mode .feed-header.collapsible:hover, body.dark-mode .ai-block-header.collapsible:hover, body.dark-mode .ai-section-header.collapsible:hover, body.dark-mode .standalone-section-header.collapsible:hover, body.dark-mode .standalone-header.collapsible:hover { background: #28241f; }
            body.dark-mode .tab-bar-wrapper { background: #221e1a; border-bottom-color: #2e2a26; }
            body.dark-mode .tab-arrow { color: #6b6760; }
            body.dark-mode .tab-arrow:hover { color: #e0a060; }
            body.dark-mode .tab-scroll-indicator { background: #e0a060; }
            body.dark-mode .tab-btn { color: #6b6760; border-bottom-color: transparent; }
            body.dark-mode .tab-btn:hover { color: #e0dbd2; }
            body.dark-mode .tab-btn.active { color: #e0dbd2; border-bottom-color: #e0dbd2; }
            body.dark-mode .tab-count { background: #2e2a26; }
            body.dark-mode .tab-btn.active .tab-count { background: #3a3530; }
            body.dark-mode .search-input { background: #221e1a; border-color: #2e2a26; color: #e0dbd2; }
            body.dark-mode .search-input:focus { border-color: #e0a060; }
            body.dark-mode .search-input::placeholder { color: #6b6760; }
            body.dark-mode .rss-item { border-left-color: #4a6b48; }
            body.dark-mode .rss-section-header, body.dark-mode .standalone-section-header, body.dark-mode .ai-section-header { background: #1e2218; border-bottom-color: #2e2a26; }
            body.dark-mode .ai-section { background: #221e1a; border-left-color: #e0a060; }
            body.dark-mode .ai-section-title { color: #e0a060; }
            body.dark-mode .ai-block { background: #2a2520; border-left-color: #2e2a26; }
            body.dark-mode .ai-block-title { color: #e0a060; }
            body.dark-mode .ai-block-content { color: #c8c4bc; }
            body.dark-mode .ai-warning { background: #2a2010; border-color: #6b4810; color: #d4a060; }
            body.dark-mode .ai-error { background: #2a1414; border-color: #6b1818; color: #f08080; }
            body.dark-mode .ai-info { background: #141e2a; border-color: #1a3050; color: #80a8d0; }
            body.dark-mode .error-section { background: #1c1714; border-color: #5a2810; }
            body.dark-mode .error-title { color: #f08080; }
            body.dark-mode .error-item { color: #d07070; }
            body.dark-mode .footer { background: #1a1814; border-top-color: #2e2a26; color: #9a9690; }
            body.dark-mode .footer-link { color: #d4a060; }
            body.dark-mode .footer-link:hover { color: #e0b070; }
            body.dark-mode .save-dropdown-menu { background: #2a2520; border-color: #3a3530; }
            body.dark-mode .save-dropdown-item { color: #e0dbd2; }
            body.dark-mode .save-dropdown-item:hover { background: #3a3530; color: #e0a060; }

            /* 暗色模式切换按钮 */
            .toggle-dark-btn {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #f5f2ed; padding: 8px 12px; border-radius: 2px; cursor: pointer;
                font-size: 14px; transition: background 0.15s; line-height: 1; min-height: 34px;
            }
            .toggle-dark-btn:hover { background: rgba(255, 255, 255, 0.18); }

            /* 阅读进度条 */
            .reading-progress { position: fixed; top: 0; left: 0; width: 0; height: 2px; background: var(--hi); z-index: 9999; transition: width 0.1s linear; }
            body.dark-mode .reading-progress { background: #e0a060; }

            /* 新上榜标记 */
            .badge-new {
                display: inline-block; background: var(--hi); color: white;
                font-size: 10px; font-weight: 700; padding: 1px 5px;
                border-radius: 2px; margin-left: 6px; vertical-align: middle; letter-spacing: 0.5px;
            }
            body.dark-mode .badge-new { background: #c2610a; }

            /* ── Bookmark button ── */
            .bm-btn {
                background: none; border: none; cursor: pointer;
                opacity: 0; transition: opacity 0.15s, color 0.15s;
                padding: 0 4px; vertical-align: middle; line-height: 1;
                color: var(--ok); flex-shrink: 0;
                display: flex; align-items: center; justify-content: center;
                align-self: flex-start;
                margin-left: auto;
                margin-top: 2px;
            }
            .bm-btn svg {
                transition: fill 0.15s, stroke 0.15s;
            }
            .news-title:hover .bm-btn,
            .rss-title:hover .bm-btn { opacity: 0.4; }
            .bm-btn:hover { opacity: 1 !important; }
            .bm-btn.saved {
                opacity: 1 !important;
                color: #e0a060 !important;
            }
            .bm-btn.saved svg {
                fill: currentColor;
            }
            .bm-toast {
                position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
                background: #2a2824; color: #faf9f7; padding: 8px 18px;
                border-radius: 20px; font-size: 12px; z-index: 9999;
                opacity: 0; transition: opacity 0.25s; pointer-events: none;
                font-family: var(--font-ui);
            }
            .bm-toast.show { opacity: 1; }

            /* ── 热度标签 ── */
            .heat-badge {
                display: inline-flex; align-items: center; gap: 1px;
                font-size: 10px; font-weight: 700;
                padding: 1px 5px; border-radius: 2px; flex-shrink: 0;
            }
            .heat-1 { background: #f3f4f6; color: #9ca3af; }
            .heat-2 { background: #fef9c3; color: #ca8a04; }
            .heat-3 { background: #ffedd5; color: #ea580c; }
            .heat-4 { background: #fee2e2; color: #dc2626; }
            .heat-5 { background: #dc2626; color: #fff; }
            body.dark-mode .heat-1 { background: #2a2824; color: #6b6760; }
            body.dark-mode .heat-2 { background: #2a2310; color: #ca8a04; }
            body.dark-mode .heat-3 { background: #2a1e10; color: #e0903a; }
            body.dark-mode .heat-4 { background: #2a1414; color: #f08080; }
            body.dark-mode .heat-5 { background: #991b1b; color: #fecaca; }

            /* ── 筛选栏（chips + 搜索框）── */
            .filter-bar {
                padding: 10px 20px 8px;
                border-bottom: 1px solid var(--line);
                background: var(--bg);
                display: flex; flex-direction: column; gap: 8px;
            }
            .chip-row { display: flex; flex-wrap: wrap; gap: 5px; }
            .filter-chip {
                padding: 3px 10px; border: 1px solid var(--line);
                border-radius: 12px; background: var(--panel);
                color: var(--ink-2); font-size: 11px; font-family: var(--font-ui);
                font-weight: 500; cursor: pointer; transition: all 0.15s;
                white-space: nowrap; line-height: 1.6;
            }
            .filter-chip:hover { border-color: var(--hi); color: var(--hi); }
            .filter-chip.active { background: var(--hi); border-color: var(--hi); color: #fff; }
            .filter-input {
                width: 100%; padding: 6px 12px; border: 1px solid var(--line);
                background: var(--panel); color: var(--ink);
                font-size: 12px; font-family: var(--font-ui);
                outline: none; transition: border-color 0.15s;
                border-radius: 2px; box-sizing: border-box;
            }
            .filter-input:focus { border-color: var(--hi); }
            .filter-input::placeholder { color: var(--faint); }
            .word-group.focused > .word-header { border-left: 3px solid var(--hi); padding-left: 17px; }
            body.dark-mode .filter-bar { background: #221e1a; border-bottom-color: #2e2a26; }
            body.dark-mode .filter-chip { background: #1e1b17; border-color: #2e2a26; color: #9a9690; }
            body.dark-mode .filter-chip:hover { border-color: #e0a060; color: #e0a060; }
            body.dark-mode .filter-chip.active { background: #c2610a; border-color: #c2610a; color: #fff; }
            body.dark-mode .filter-input { background: #1e1b17; border-color: #2e2a26; color: #e0dbd2; }
            body.dark-mode .filter-input:focus { border-color: #e0a060; }
            body.dark-mode .filter-input::placeholder { color: #6b6760; }
            body.dark-mode .word-group.focused > .word-header { border-left-color: #e0a060; }
        </style>
    </head>
    <body>
        <div class="reading-progress"></div>
        <div class="container">
            <div class="header">
                <div class="header-watermark">TrendRadar</div>
                <div class="save-buttons">
                    <button class="toggle-wide-btn" onclick="toggleWideMode()" title="切换宽屏/窄屏">⛶</button>
                    <button class="toggle-dark-btn" onclick="toggleDarkMode()" title="切换暗色/亮色">☽</button>
                    <div class="save-btn-group">
                        <button class="save-btn" onclick="saveAsImage(event)">导出</button>
                        <button class="save-dropdown-trigger">▾</button>
                        <div class="save-dropdown-menu">
                            <button class="save-dropdown-item" onclick="saveAsImage(event)"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><circle cx="8" cy="7.5" r="2.5"/><path d="M12 4h.01"/></svg>整页截图</button>
                            <button class="save-dropdown-item" onclick="saveAsMultipleImages(event)"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="4" width="10" height="10" rx="1.5"/><path d="M5 4V2.5A1.5 1.5 0 016.5 1h7A1.5 1.5 0 0115 2.5v7a1.5 1.5 0 01-1.5 1.5H12"/></svg>分段截图</button>
                            <button class="save-dropdown-item" onclick="saveAsMarkdown()"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2.5 2h11A1.5 1.5 0 0115 3.5v9a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9A1.5 1.5 0 012.5 2z"/><path d="M4 11V5l2.5 3L9 5v6"/><path d="M11.5 8v3m0 0l-1.5-2m1.5 2l1.5-2"/></svg>Markdown</button>
                        </div>
                    </div>
                </div>
                <div class="header-title">热点新闻分析</div>
                <div class="header-info">"""

    # 使用提供的时间函数或默认 datetime.now
    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()

    # 处理报告类型显示
    if mode == "current":
        mode_display = "当前榜单"
    elif mode == "incremental":
        mode_display = "增量分析"
    else:
        mode_display = "全天汇总"

    # 计算各项数据
    hot_news_count = sum(len(stat["titles"]) for stat in report_data["stats"])
    new_count = report_data.get("total_new_count", 0)

    # 从元数据获取 RSS 和平台信息
    hotlist_total = report_data.get("hotlist_total", total_titles)
    platform_total = report_data.get("platform_total", 0)
    failed_count = len(report_data.get("failed_ids", []))
    platform_success = platform_total - failed_count if platform_total else 0
    rss_matched = report_data.get("rss_matched_count", 0)
    rss_total = report_data.get("rss_total_count", 0)
    rss_source_total = report_data.get("rss_source_total", 0)
    rss_source_failed = report_data.get("rss_source_failed", 0)
    rss_source_success = max(0, rss_source_total - rss_source_failed)

    # 1. 报告类型
    html += f"""
                    <div class="info-item">
                        <span class="info-label">报告类型</span>
                        <span class="info-value">{mode_display}</span>
                    </div>"""

    # 2. 生成时间
    html += f"""
                    <div class="info-item">
                        <span class="info-label">生成时间</span>
                        <span class="info-value">{now.strftime("%m-%d %H:%M")}</span>
                    </div>"""

    # 3. 热榜命中
    html += f"""
                    <div class="info-item">
                        <span class="info-label">热榜命中</span>
                        <span class="info-value">{hot_news_count} / {hotlist_total}</span>
                    </div>"""

    # 4. RSS 命中
    if rss_source_total > 0:
        rss_value = f"{rss_matched} / {rss_total}"
    else:
        rss_value = "未启用"
    html += f"""
                    <div class="info-item">
                        <span class="info-label">RSS 命中</span>
                        <span class="info-value">{rss_value}</span>
                    </div>"""

    # 5. 热榜平台
    if platform_total > 0:
        platform_value = f"{platform_success}/{platform_total}"
    else:
        platform_value = "--"
    html += f"""
                    <div class="info-item">
                        <span class="info-label">热榜平台</span>
                        <span class="info-value">{platform_value}</span>
                    </div>"""

    # 6. RSS 源
    if rss_source_total > 0:
        rss_source_value = f"{rss_source_success}/{rss_source_total}"
    else:
        rss_source_value = "--"
    html += f"""
                    <div class="info-item">
                        <span class="info-label">RSS 源</span>
                        <span class="info-value">{rss_source_value}</span>
                    </div>"""

    # 7. 新增热点（热榜新增 + RSS 新增）
    rss_new_count = sum(len(stat.get("titles", [])) for stat in (rss_new_items or []))
    total_new = new_count + rss_new_count
    new_value = f"{new_count} + {rss_new_count}" if total_new > 0 else "0"
    html += f"""
                    <div class="info-item">
                        <span class="info-label">新增热点</span>
                        <span class="info-value">{new_value}</span>
                    </div>"""

    # 8. AI 分析
    if ai_analysis and getattr(ai_analysis, "success", False):
        hotlist_analyzed = getattr(ai_analysis, "hotlist_analyzed", 0)
        rss_analyzed = getattr(ai_analysis, "rss_analyzed", 0)
        standalone_analyzed = getattr(ai_analysis, "standalone_analyzed", 0)
        ai_include_rss = getattr(ai_analysis, "include_rss", True)
        ai_include_standalone = getattr(ai_analysis, "include_standalone", False)

        ai_parts = [str(hotlist_analyzed)]
        if ai_include_rss:
            ai_parts.append(str(rss_analyzed))
        if ai_include_standalone:
            ai_parts.append(str(standalone_analyzed))
        ai_value = " + ".join(ai_parts) if sum(int(p) for p in ai_parts) > 0 else "0"
    elif ai_analysis:
        if getattr(ai_analysis, "skipped", False):
            ai_value = "已跳过"
        else:
            ai_value = "待配置"
    else:
        ai_value = "未启用"
    html += f"""
                    <div class="info-item">
                        <span class="info-label">AI 分析</span>
                        <span class="info-value">{ai_value}</span>
                    </div>"""

    html += """
                </div>
            </div>

            <div class="content">
                <div class="filter-bar">
                    <div class="chip-row" id="chip-row"></div>
                    <input type="text" class="filter-input" id="filter-input" placeholder="搜索关键词，匹配词组排到前面… 如：英国 AI" oninput="handleFilterInput(this.value)">
                </div>
                <div class="search-bar">
                    <input type="text" class="search-input" placeholder="搜索新闻标题..." oninput="handleSearch(this.value)">
                </div>"""

    # 处理失败ID错误信息
    if report_data["failed_ids"]:
        html += """
                <div class="error-section">
                    <div class="error-title">⚠️ 请求失败的平台</div>
                    <ul class="error-list">"""
        for id_value in report_data["failed_ids"]:
            html += f'<li class="error-item">{html_escape(id_value)}</li>'
        html += """
                    </ul>
                </div>"""

    # 生成热点词汇统计部分的HTML
    stats_html = ""
    tab_bar_html = ""
    if report_data["stats"]:
        total_count = len(report_data["stats"])

        # Tab 栏已由顶部关键词 chips 替代，不再生成
        tab_bar_html = ""

        for i, stat in enumerate(report_data["stats"], 1):
            count = stat["count"]

            # 确定热度等级
            if count >= 10:
                count_class = "hot"
            elif count >= 5:
                count_class = "warm"
            else:
                count_class = ""

            escaped_word = html_escape(stat["word"])

            stats_html += f"""
                <div class="word-group" data-tab-index="{i - 1}" data-word="{escaped_word}">
                    <div class="word-header">
                        <div class="word-info">
                            <div class="word-name">{escaped_word}</div>
                            <div class="word-count {count_class}">{count} 条</div>
                        </div>
                        <div class="word-index"><span class="collapse-icon">▼</span>{i}/{total_count}</div>
                    </div>"""

            # 处理每个词组下的新闻标题，给每条新闻标上序号
            for j, title_data in enumerate(stat["titles"], 1):
                is_new = title_data.get("is_new", False)
                new_class = "new" if is_new else ""

                # 预计算热度分 1-5 (rank 60% + count 40%)
                _rnks = title_data.get("ranks", [])
                _cnt = title_data.get("count", 1)
                _rth = title_data.get("rank_threshold", 10)
                _mr = min(_rnks) if _rnks else 99
                _rs = 5 if _mr <= 3 else 4 if _mr <= _rth else 3 if _mr <= _rth * 2 else 2 if _mr <= _rth * 4 else 1
                _cs = 5 if _cnt >= 10 else 4 if _cnt >= 5 else 3 if _cnt >= 3 else 2 if _cnt >= 2 else 1
                _heat = max(1, min(5, round(_rs * 0.6 + _cs * 0.4)))

                stats_html += f"""
                    <div class="news-item {new_class}">
                        <div class="news-number">{j}</div>
                        <div class="news-content">
                            <div class="news-header"><span class="heat-badge heat-{_heat}">⚡{_heat}</span>"""

                # 根据 display_mode 决定显示来源还是关键词
                if display_mode == "keyword":
                    # keyword 模式：显示来源
                    stats_html += f'<span class="source-name">{html_escape(title_data["source_name"])}</span>'
                else:
                    # platform 模式：显示关键词
                    matched_keyword = title_data.get("matched_keyword", "")
                    if matched_keyword:
                        stats_html += f'<span class="keyword-tag">[{html_escape(matched_keyword)}]</span>'

                # 处理排名显示
                ranks = title_data.get("ranks", [])
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    rank_threshold = title_data.get("rank_threshold", 10)

                    # 确定排名等级
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= rank_threshold:
                        rank_class = "high"
                    else:
                        rank_class = ""

                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"

                    # 计算趋势箭头
                    rank_timeline = title_data.get("rank_timeline", [])
                    trend = calculate_rank_trend(rank_timeline, ranks)
                    trend_html = ""
                    if trend == "up":
                        trend_html = '<span class="trend-up">📈</span>'
                    elif trend == "down":
                        trend_html = '<span class="trend-down">📉</span>'

                    stats_html += f'<span class="rank-num {rank_class}">{rank_text}</span>{trend_html}'

                # 处理时间显示
                time_display = title_data.get("time_display", "")
                if time_display:
                    # 简化时间显示格式，将波浪线替换为~
                    simplified_time = (
                        time_display.replace(" ~ ", "~")
                        .replace("[", "")
                        .replace("]", "")
                    )
                    stats_html += (
                        f'<span class="time-info">{html_escape(simplified_time)}</span>'
                    )

                # 处理出现次数
                count_info = title_data.get("count", 1)
                if count_info > 1:
                    stats_html += f'<span class="count-info">{count_info}次</span>'

                stats_html += """
                            </div>
                            <div class="news-title">"""

                # 处理标题和链接
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    stats_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a><button class="bm-btn" onclick="saveBookmark(event,this)" data-title="{escaped_title}" data-url="{escaped_url}" data-source="热榜" title="保存书签"><svg width="13" height="16" viewBox="0 0 13 16" fill="none"><path d="M1.5 1.5h10v13l-5-3.5-5 3.5V1.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg></button>'
                else:
                    stats_html += escaped_title

                stats_html += """
                            </div>
                        </div>
                    </div>"""

            stats_html += """
                </div>"""

    # 给热榜统计添加外层包装
    if stats_html:
        stats_html = f"""
                <div class="hotlist-section">{tab_bar_html}{stats_html}
                </div>"""

    # 生成新增新闻区域的HTML
    new_titles_html = ""
    if show_new_section and report_data["new_titles"]:
        new_titles_html += f"""
                <div class="new-section">
                    <div class="new-section-title">本次新增热点 (共 {report_data['total_new_count']} 条)</div>
                    <div class="new-sources-grid">"""

        for source_data in report_data["new_titles"]:
            escaped_source = html_escape(source_data["source_name"])
            titles_count = len(source_data["titles"])

            new_titles_html += f"""
                    <div class="new-source-group">
                        <div class="new-source-title">{escaped_source} · {titles_count}条</div>"""

            # 为新增新闻也添加序号
            for idx, title_data in enumerate(source_data["titles"], 1):
                ranks = title_data.get("ranks", [])

                # 处理新增新闻的排名显示
                rank_class = ""
                if ranks:
                    min_rank = min(ranks)
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= title_data.get("rank_threshold", 10):
                        rank_class = "high"

                    if len(ranks) == 1:
                        rank_text = str(ranks[0])
                    else:
                        rank_text = f"{min(ranks)}-{max(ranks)}"
                else:
                    rank_text = "?"

                new_titles_html += f"""
                        <div class="new-item">
                            <div class="new-item-number">{idx}</div>
                            <div class="new-item-rank {rank_class}">{rank_text}</div>
                            <div class="new-item-content">
                                <div class="new-item-title">"""

                # 处理新增新闻的链接
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    new_titles_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    new_titles_html += escaped_title

                new_titles_html += """
                                </div>
                            </div>
                        </div>"""

            new_titles_html += """
                    </div>"""

        new_titles_html += """
                    </div>
                </div>"""

    # 生成 RSS 统计内容
    def render_rss_stats_html(stats: List[Dict], title: str = "RSS 订阅更新") -> str:
        """渲染 RSS 统计区块 HTML

        Args:
            stats: RSS 分组统计列表，格式与热榜一致：
                [
                    {
                        "word": "关键词",
                        "count": 5,
                        "titles": [
                            {
                                "title": "标题",
                                "source_name": "Feed 名称",
                                "time_display": "12-29 08:20",
                                "url": "...",
                                "is_new": True/False
                            }
                        ]
                    }
                ]
            title: 区块标题

        Returns:
            渲染后的 HTML 字符串
        """
        if not stats:
            return ""

        # 计算总条目数
        total_count = sum(stat.get("count", 0) for stat in stats)
        if total_count == 0:
            return ""

        rss_html = f"""
                <div class="rss-section collapsed">
                    <div class="rss-section-header">
                        <span class="collapse-icon">▼</span>
                        <div class="rss-section-title">{title}</div>
                        <div class="rss-section-count">{total_count} 条</div>
                    </div>
                    <div class="rss-feeds-grid">"""

        # 按关键词分组渲染（与热榜格式一致）
        for stat in stats:
            keyword = stat.get("word", "")
            titles = stat.get("titles", [])
            if not titles:
                continue

            keyword_count = len(titles)

            rss_html += f"""
                    <div class="feed-group collapsed">
                        <div class="feed-header">
                            <span class="collapse-icon">▼</span>
                            <div class="feed-name">{html_escape(keyword)}</div>
                            <div class="feed-count">{keyword_count} 条</div>
                        </div>"""

            for title_data in titles:
                item_title = title_data.get("title", "")
                url = title_data.get("url", "")
                time_display = title_data.get("time_display", "")
                source_name = title_data.get("source_name", "")
                is_new = title_data.get("is_new", False)

                rss_html += """
                        <div class="rss-item">
                            <div class="rss-meta">"""

                if time_display:
                    rss_html += f'<span class="rss-time">{html_escape(time_display)}</span>'

                if source_name:
                    rss_html += f'<span class="rss-author">{html_escape(source_name)}</span>'

                if is_new:
                    rss_html += '<span class="rss-author" style="color: #dc2626;">NEW</span>'

                rss_html += """
                            </div>
                            <div class="rss-title">"""

                escaped_title = html_escape(item_title)
                escaped_source_bm = html_escape(source_name or keyword or "RSS")
                if url:
                    escaped_url = html_escape(url)
                    rss_html += f'<a href="{escaped_url}" target="_blank" class="rss-link">{escaped_title}</a><button class="bm-btn" onclick="saveBookmark(event,this)" data-title="{escaped_title}" data-url="{escaped_url}" data-source="{escaped_source_bm}" title="保存书签"><svg width="13" height="16" viewBox="0 0 13 16" fill="none"><path d="M1.5 1.5h10v13l-5-3.5-5 3.5V1.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg></button>'
                else:
                    rss_html += escaped_title

                rss_html += """
                            </div>
                        </div>"""

            rss_html += """
                    </div>"""

        rss_html += """
                    </div>
                </div>"""
        return rss_html

    # 生成独立展示区内容
    def render_standalone_html(data: Optional[Dict]) -> str:
        """渲染独立展示区 HTML（复用热点词汇统计区样式）

        Args:
            data: 独立展示数据，格式：
                {
                    "platforms": [
                        {
                            "id": "zhihu",
                            "name": "知乎热榜",
                            "items": [
                                {
                                    "title": "标题",
                                    "url": "链接",
                                    "rank": 1,
                                    "ranks": [1, 2, 1],
                                    "first_time": "08:00",
                                    "last_time": "12:30",
                                    "count": 3,
                                }
                            ]
                        }
                    ],
                    "rss_feeds": [
                        {
                            "id": "hacker-news",
                            "name": "Hacker News",
                            "items": [
                                {
                                    "title": "标题",
                                    "url": "链接",
                                    "published_at": "2025-01-07T08:00:00",
                                    "author": "作者",
                                }
                            ]
                        }
                    ]
                }

        Returns:
            渲染后的 HTML 字符串
        """
        if not data:
            return ""

        platforms = data.get("platforms", [])
        rss_feeds = data.get("rss_feeds", [])

        if not platforms and not rss_feeds:
            return ""

        # 计算总条目数
        total_platform_items = sum(len(p.get("items", [])) for p in platforms)
        total_rss_items = sum(len(f.get("items", [])) for f in rss_feeds)
        total_count = total_platform_items + total_rss_items

        if total_count == 0:
            return ""

        standalone_html = f"""
                <div class="standalone-section collapsed">
                    <div class="standalone-section-header">
                        <span class="collapse-icon">▼</span>
                        <div class="standalone-section-title">独立展示区</div>
                        <div class="standalone-section-count">{total_count} 条</div>
                    </div>"""


        standalone_html += """
                    <div class="standalone-groups-grid">"""

        # 渲染热榜平台（复用 word-group 结构）
        for platform in platforms:
            platform_name = platform.get("name", platform.get("id", ""))
            items = platform.get("items", [])
            if not items:
                continue

            standalone_html += f"""
                    <div class="standalone-group collapsed">
                        <div class="standalone-header">
                            <span class="collapse-icon">▼</span>
                            <div class="standalone-name">{html_escape(platform_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            # 渲染每个条目（复用 news-item 结构）
            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "") or item.get("mobileUrl", "")
                rank = item.get("rank", 0)
                ranks = item.get("ranks", [])
                first_time = item.get("first_time", "")
                last_time = item.get("last_time", "")
                count = item.get("count", 1)

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                # 排名显示（复用 rank-num 样式，无 # 前缀）
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)

                    # 确定排名等级
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= 10:
                        rank_class = "high"
                    else:
                        rank_class = ""

                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"

                    standalone_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'
                elif rank > 0:
                    if rank <= 3:
                        rank_class = "top"
                    elif rank <= 10:
                        rank_class = "high"
                    else:
                        rank_class = ""
                    standalone_html += f'<span class="rank-num {rank_class}">{rank}</span>'

                # 时间显示（复用 time-info 样式，将 HH-MM 转换为 HH:MM）
                if first_time and last_time and first_time != last_time:
                    first_time_display = convert_time_for_display(first_time)
                    last_time_display = convert_time_for_display(last_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}~{html_escape(last_time_display)}</span>'
                elif first_time:
                    first_time_display = convert_time_for_display(first_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}</span>'

                # 出现次数（复用 count-info 样式）
                if count > 1:
                    standalone_html += f'<span class="count-info">{count}次</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                # 标题和链接（复用 news-link 样式）
                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a><button class="bm-btn" onclick="saveBookmark(event,this)" data-title="{escaped_title}" data-url="{escaped_url}" data-source="热榜" title="保存书签"><svg width="13" height="16" viewBox="0 0 13 16" fill="none"><path d="M1.5 1.5h10v13l-5-3.5-5 3.5V1.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg></button>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""

            standalone_html += """
                    </div>"""

        # 渲染 RSS 源（复用相同结构）
        for feed in rss_feeds:
            feed_name = feed.get("name", feed.get("id", ""))
            items = feed.get("items", [])
            if not items:
                continue

            standalone_html += f"""
                    <div class="standalone-group collapsed">
                        <div class="standalone-header">
                            <span class="collapse-icon">▼</span>
                            <div class="standalone-name">{html_escape(feed_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "")
                published_at = item.get("published_at", "")
                author = item.get("author", "")

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                # 时间显示（格式化 ISO 时间）
                if published_at:
                    try:
                        from datetime import datetime as dt
                        if "T" in published_at:
                            dt_obj = dt.fromisoformat(published_at.replace("Z", "+00:00"))
                            time_display = dt_obj.strftime("%m-%d %H:%M")
                        else:
                            time_display = published_at
                    except:
                        time_display = published_at

                    standalone_html += f'<span class="time-info">{html_escape(time_display)}</span>'

                # 作者显示
                if author:
                    standalone_html += f'<span class="source-name">{html_escape(author)}</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                escaped_title = html_escape(title)
                escaped_feed_bm = html_escape(feed_name)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a><button class="bm-btn" onclick="saveBookmark(event,this)" data-title="{escaped_title}" data-url="{escaped_url}" data-source="{escaped_feed_bm}" title="保存书签"><svg width="13" height="16" viewBox="0 0 13 16" fill="none"><path d="M1.5 1.5h10v13l-5-3.5-5 3.5V1.5z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg></button>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""

            standalone_html += """
                    </div>"""

        standalone_html += """
                    </div>
                </div>"""
        return standalone_html

    # 生成 RSS 统计和新增 HTML
    rss_stats_html = render_rss_stats_html(rss_items, "RSS 订阅更新") if rss_items else ""
    rss_new_html = render_rss_stats_html(rss_new_items, "RSS 新增更新") if rss_new_items else ""

    # 生成独立展示区 HTML
    standalone_html = render_standalone_html(standalone_data)

    # 生成 AI 分析 HTML
    ai_html = render_ai_analysis_html_rich(ai_analysis) if ai_analysis else ""

    # 准备各区域内容映射
    region_contents = {
        "hotlist": stats_html,
        "rss": rss_stats_html,
        "new_items": (new_titles_html, rss_new_html),  # 元组，分别处理
        "standalone": standalone_html,
        "ai_analysis": ai_html,
    }

    def add_section_divider(content: str) -> str:
        """为内容的外层 div 添加 section-divider 类"""
        if not content or 'class="' not in content:
            return content
        first_class_pos = content.find('class="')
        if first_class_pos != -1:
            insert_pos = first_class_pos + len('class="')
            return content[:insert_pos] + "section-divider " + content[insert_pos:]
        return content

    # 按 region_order 顺序组装内容，动态添加分割线
    has_previous_content = False
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            # 特殊处理 new_items 区域（包含热榜新增和 RSS 新增两部分）
            new_html, rss_new = content
            if new_html:
                if has_previous_content:
                    new_html = add_section_divider(new_html)
                html += new_html
                has_previous_content = True
            if rss_new:
                if has_previous_content:
                    rss_new = add_section_divider(rss_new)
                html += rss_new
                has_previous_content = True
        elif content:
            if has_previous_content:
                content = add_section_divider(content)
            html += content
            has_previous_content = True

    html += """
            </div>

            <div class="footer">
                <div class="footer-content">
                    由 <span class="project-name">TrendRadar</span> 生成 ·
                    <a href="https://github.com/sansan0/TrendRadar" target="_blank" class="footer-link">
                        GitHub 开源项目
                    </a>"""

    if update_info:
        html += f"""
                    <br>
                    <span style="color: #ea580c; font-weight: 500;">
                        发现新版本 {update_info['remote_version']}，当前版本 {update_info['current_version']}
                    </span>"""

    html += """
                </div>
            </div>
        </div>

        <div class="fab-bar">
            <button class="fab-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="返回顶部">↑</button>
            <button class="fab-btn fab-help">
                <span>?</span>
                <div class="fab-tooltip">
                    <div class="tip-row"><span>切换宽屏</span><span class="tip-key">W</span></div>
                    <div class="tip-row"><span>暗色模式</span><span class="tip-key">D</span></div>
                    <div class="tip-row"><span>关注词</span><span class="tip-key">F</span></div>
                    <div class="tip-row"><span>搜索</span><span class="tip-key">/</span></div>
                    <div class="tip-row"><span>序号可复制</span><span class="tip-key">点击</span></div>
                </div>
            </button>
        </div>

        <script>
            // ===== 浏览器增强功能 =====

            function toggleWideMode() {
                document.body.classList.toggle('wide-mode');
                var isWide = document.body.classList.contains('wide-mode');
                try { localStorage.setItem('trendradar-wide-mode', isWide ? '1' : '0'); } catch(e) {}
                var btn = document.querySelector('.toggle-wide-btn');
                if (btn) btn.textContent = isWide ? '⊡' : '⛶';
                initTabVisibility();
                initCollapseVisibility();
            }

            function toggleDarkMode() {
                var isDark = document.body.classList.toggle('dark-mode');
                try { localStorage.setItem('trendradar-dark-mode', isDark ? '1' : '0'); } catch(e) {}
                var btn = document.querySelector('.toggle-dark-btn');
                if (btn) btn.textContent = isDark ? '☀' : '☽';
            }

            function initTabScroll(tabBar) {
                var wrapper = tabBar.closest('.tab-bar-wrapper') || tabBar.parentNode;
                var leftArrow = wrapper.querySelector('.tab-arrow-left');
                var rightArrow = wrapper.querySelector('.tab-arrow-right');
                var indicator = wrapper.querySelector('.tab-scroll-indicator');
                if (!leftArrow) {
                    leftArrow = document.createElement('button');
                    leftArrow.className = 'tab-arrow tab-arrow-left';
                    leftArrow.innerHTML = '‹';
                    rightArrow = document.createElement('button');
                    rightArrow.className = 'tab-arrow tab-arrow-right';
                    rightArrow.innerHTML = '›';
                    indicator = document.createElement('div');
                    indicator.className = 'tab-scroll-indicator';
                    wrapper.insertBefore(leftArrow, tabBar);
                    tabBar.after(rightArrow);
                    wrapper.appendChild(indicator);
                }
                var scrollStep = 200;
                leftArrow.addEventListener('click', function(e) {
                    e.stopPropagation();
                    tabBar.scrollBy({ left: -scrollStep, behavior: 'smooth' });
                });
                rightArrow.addEventListener('click', function(e) {
                    e.stopPropagation();
                    tabBar.scrollBy({ left: scrollStep, behavior: 'smooth' });
                });
                function updateArrows() {
                    var sl = tabBar.scrollLeft;
                    var sw = tabBar.scrollWidth;
                    var cw = tabBar.clientWidth;
                    var noOverflow = sw <= cw + 1;
                    var atStart = sl <= 1;
                    var atEnd = sl + cw >= sw - 1;
                    leftArrow.classList.toggle('visible', !noOverflow && !atStart);
                    rightArrow.classList.toggle('visible', !noOverflow && !atEnd);
                    tabBar.classList.toggle('scroll-start', atStart);
                    tabBar.classList.toggle('scroll-end', atEnd);
                    tabBar.classList.toggle('no-overflow', noOverflow);
                    var progress = noOverflow ? 0 : sl / (sw - cw);
                    indicator.style.width = (progress * 100) + '%';
                }
                tabBar.addEventListener('scroll', updateArrows, { passive: true });
                tabBar.addEventListener('wheel', function(e) {
                    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                        tabBar.scrollLeft += e.deltaY;
                        e.preventDefault();
                    }
                }, { passive: false });
                updateArrows();
                new ResizeObserver(updateArrows).observe(tabBar);
            }

            function initTabs() {
                var wrapper = document.querySelector('.tab-bar-wrapper');
                var tabBar = wrapper ? wrapper.querySelector('.tab-bar') : null;
                if (!tabBar) return;
                var tabs = tabBar.querySelectorAll('.tab-btn');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                initTabVisibility();
                initTabScroll(tabBar);

                function activateTab(index, scroll) {
                    tabs.forEach(function(t) { t.classList.remove('active'); });
                    if (index === 'all') {
                        var allBtn = tabBar.querySelector('[data-tab-index="all"]');
                        if (allBtn) {
                            allBtn.classList.add('active');
                            if (scroll !== false) allBtn.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                        }
                        groups.forEach(function(g) { g.style.display = ''; });
                        try { history.replaceState(null, '', '#all'); } catch(e) {}
                        return;
                    }
                    var idx = parseInt(index);
                    tabs.forEach(function(t) {
                        if (parseInt(t.dataset.tabIndex) === idx) t.classList.add('active');
                    });
                    if (document.body.classList.contains('wide-mode') && !wrapper.classList.contains('tab-hidden')) {
                        groups.forEach(function(g) {
                            g.style.display = (parseInt(g.dataset.tabIndex) === idx) ? '' : 'none';
                        });
                    }
                    var activeBtn = tabBar.querySelector('.tab-btn.active');
                    if (scroll !== false && activeBtn) activeBtn.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                    try { history.replaceState(null, '', '#tab-' + idx); } catch(e) {}
                }

                tabs.forEach(function(tab) {
                    tab.addEventListener('click', function() {
                        var idx = tab.dataset.tabIndex;
                        activateTab(idx === 'all' ? 'all' : parseInt(idx));
                    });
                });

                tabBar.addEventListener('keydown', function(e) {
                    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                        var tabsArr = Array.from(tabs);
                        var ci = tabsArr.findIndex(function(t) { return t.classList.contains('active'); });
                        var dir = e.key === 'ArrowRight' ? 1 : -1;
                        var ni = Math.max(0, Math.min(tabsArr.length - 1, ci + dir));
                        var nt = tabsArr[ni];
                        activateTab(nt.dataset.tabIndex === 'all' ? 'all' : parseInt(nt.dataset.tabIndex));
                        nt.focus();
                        e.preventDefault();
                    }
                });

                var hash = window.location.hash;
                if (hash === '#all') { activateTab('all'); }
                else if (hash.indexOf('#tab-') === 0) { activateTab(parseInt(hash.replace('#tab-', ''))); }
                else { activateTab(0, false); }
            }

            function initTabVisibility() {
                var wrapper = document.querySelector('.tab-bar-wrapper');
                if (!wrapper) return;
                var tabBar = wrapper.querySelector('.tab-bar');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                var isWide = document.body.classList.contains('wide-mode');
                if (!isWide || groups.length <= 2) {
                    wrapper.classList.add('tab-hidden');
                    groups.forEach(function(g) { g.style.display = ''; });
                } else {
                    wrapper.classList.remove('tab-hidden');
                    var activeTab = tabBar.querySelector('.tab-btn.active');
                    if (activeTab) { activeTab.click(); }
                    else {
                        var firstTab = tabBar.querySelector('.tab-btn[data-tab-index="0"]');
                        if (firstTab) firstTab.click();
                    }
                }
            }

            var handleSearch = (function() {
                var timer = null;
                return function(query) {
                    clearTimeout(timer);
                    timer = setTimeout(function() {
                        query = query.toLowerCase();
                        document.querySelectorAll('.news-item').forEach(function(item) {
                            var title = (item.querySelector('.news-title') || {}).textContent || '';
                            item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
                        });
                        document.querySelectorAll('.rss-item').forEach(function(item) {
                            var title = (item.querySelector('.rss-title') || {}).textContent || '';
                            item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
                        });
                    }, 200);
                };
            })();

            function initBackToTop() {
                var fabBar = document.querySelector('.fab-bar');
                if (!fabBar) return;
                var ticking = false;
                window.addEventListener('scroll', function() {
                    if (!ticking) {
                        requestAnimationFrame(function() {
                            fabBar.classList.toggle('visible', window.scrollY > 300);
                            ticking = false;
                        });
                        ticking = true;
                    }
                });
            }

            function initCollapse() {
                document.querySelectorAll('.word-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var group = header.closest('.word-group');
                        if (group) group.classList.toggle('collapsed');
                    });
                });
                document.querySelectorAll('.rss-section-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var section = header.closest('.rss-section');
                        if (section) section.classList.toggle('collapsed');
                    });
                });
                document.querySelectorAll('.feed-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var group = header.closest('.feed-group');
                        if (group) group.classList.toggle('collapsed');
                    });
                });
                document.querySelectorAll('.ai-block-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var block = header.closest('.ai-block');
                        if (block) block.classList.toggle('collapsed');
                    });
                });
                document.querySelectorAll('.ai-section-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var section = header.closest('.ai-section');
                        if (section) section.classList.toggle('collapsed');
                    });
                });
                document.querySelectorAll('.standalone-section-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var section = header.closest('.standalone-section');
                        if (section) section.classList.toggle('collapsed');
                    });
                });
                document.querySelectorAll('.standalone-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var group = header.closest('.standalone-group');
                        if (group) group.classList.toggle('collapsed');
                    });
                });
                initCollapseVisibility();
            }

            function initCollapseVisibility() {
                var headers = document.querySelectorAll('.word-header, .rss-section-header, .feed-header, .ai-block-header, .ai-section-header, .standalone-section-header, .standalone-header');
                headers.forEach(function(h) {
                    h.classList.add('collapsible');
                });
            }

            function prepareForScreenshot() {
                var state = {
                    wasWide: document.body.classList.contains('wide-mode'),
                    hiddenGroups: []
                };
                document.body.classList.remove('wide-mode');
                state.wasDark = document.body.classList.contains('dark-mode');
                document.body.classList.remove('dark-mode');
                document.querySelectorAll('.word-group[data-tab-index]').forEach(function(g, i) {
                    if (g.style.display === 'none') {
                        state.hiddenGroups.push(i);
                        g.style.display = '';
                    }
                });
                document.querySelectorAll('.tab-bar-wrapper, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
                    el.dataset.prevDisplay = el.style.display || '';
                    el.style.display = 'none';
                });
                document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
                    el.dataset.prevDisplay = el.style.display || ''; el.style.display = 'none';
                });
                document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = 'none'; });
                document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = 'none'; });
                return state;
            }

            function restoreAfterScreenshot(state) {
                if (state.wasWide) document.body.classList.add('wide-mode');
                if (state.wasDark) document.body.classList.add('dark-mode');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                state.hiddenGroups.forEach(function(i) {
                    if (groups[i]) groups[i].style.display = 'none';
                });
                document.querySelectorAll('.tab-bar-wrapper, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
                    el.style.display = el.dataset.prevDisplay || '';
                    delete el.dataset.prevDisplay;
                });
                document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
                    el.style.display = el.dataset.prevDisplay || ''; delete el.dataset.prevDisplay;
                });
                document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = ''; });
                document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = ''; });
                initTabVisibility();
                initCollapseVisibility();
                var fabBar = document.querySelector('.fab-bar');
                if (fabBar && window.scrollY > 300) fabBar.classList.add('visible');
            }

            // ===== 截图功能 =====

            async function saveAsImage(e) {
                const button = e.target.closest('.save-dropdown-item') || e.target;
                const originalHTML = button.innerHTML;
                var screenshotState = null;

                try {
                    button.textContent = '生成中...';
                    button.disabled = true;
                    window.scrollTo(0, 0);

                    // 等待页面稳定
                    await new Promise(resolve => setTimeout(resolve, 200));

                    // 截图前准备：切回窄屏布局
                    screenshotState = prepareForScreenshot();

                    // 截图前隐藏按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 再次等待确保按钮完全隐藏
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const container = document.querySelector('.container');

                    const canvas = await html2canvas(container, {
                        backgroundColor: '#ffffff',
                        scale: 1.5,
                        useCORS: true,
                        allowTaint: false,
                        imageTimeout: 10000,
                        removeContainer: false,
                        foreignObjectRendering: false,
                        logging: false,
                        width: container.offsetWidth,
                        height: container.offsetHeight,
                        x: 0,
                        y: 0,
                        scrollX: 0,
                        scrollY: 0,
                        windowWidth: window.innerWidth,
                        windowHeight: window.innerHeight
                    });

                    buttons.style.visibility = 'visible';
                    restoreAfterScreenshot(screenshotState);

                    const link = document.createElement('a');
                    const now = new Date();
                    const filename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

                    link.download = filename;
                    link.href = canvas.toDataURL('image/png', 1.0);

                    // 触发下载
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);

                    button.textContent = '保存成功!';
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    if (screenshotState) { restoreAfterScreenshot(screenshotState); }
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);
                }
            }

            async function saveAsMultipleImages(e) {
                const button = e.target.closest('.save-dropdown-item') || e.target;
                const originalHTML = button.innerHTML;
                const container = document.querySelector('.container');
                const scale = 1.5;
                const maxHeight = 5000 / scale;
                var screenshotState2 = null;

                try {
                    screenshotState2 = prepareForScreenshot();
                    button.textContent = '分析中...';
                    button.disabled = true;

                    // 获取所有可能的分割元素
                    const newsItems = Array.from(container.querySelectorAll('.news-item'));
                    const wordGroups = Array.from(container.querySelectorAll('.word-group'));
                    const newSection = container.querySelector('.new-section');
                    const errorSection = container.querySelector('.error-section');
                    const header = container.querySelector('.header');
                    const footer = container.querySelector('.footer');

                    // 计算元素位置和高度
                    const containerRect = container.getBoundingClientRect();
                    const elements = [];

                    // 添加header作为必须包含的元素
                    elements.push({
                        type: 'header',
                        element: header,
                        top: 0,
                        bottom: header.offsetHeight,
                        height: header.offsetHeight
                    });

                    // 添加错误信息（如果存在）
                    if (errorSection) {
                        const rect = errorSection.getBoundingClientRect();
                        elements.push({
                            type: 'error',
                            element: errorSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 按word-group分组处理news-item
                    wordGroups.forEach(group => {
                        const groupRect = group.getBoundingClientRect();
                        const groupNewsItems = group.querySelectorAll('.news-item');

                        // 添加word-group的header部分
                        const wordHeader = group.querySelector('.word-header');
                        if (wordHeader) {
                            const headerRect = wordHeader.getBoundingClientRect();
                            elements.push({
                                type: 'word-header',
                                element: wordHeader,
                                parent: group,
                                top: groupRect.top - containerRect.top,
                                bottom: headerRect.bottom - containerRect.top,
                                height: headerRect.height
                            });
                        }

                        // 添加每个news-item
                        groupNewsItems.forEach(item => {
                            const rect = item.getBoundingClientRect();
                            elements.push({
                                type: 'news-item',
                                element: item,
                                parent: group,
                                top: rect.top - containerRect.top,
                                bottom: rect.bottom - containerRect.top,
                                height: rect.height
                            });
                        });
                    });

                    // 添加新增新闻部分
                    if (newSection) {
                        const rect = newSection.getBoundingClientRect();
                        elements.push({
                            type: 'new-section',
                            element: newSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 添加footer
                    const footerRect = footer.getBoundingClientRect();
                    elements.push({
                        type: 'footer',
                        element: footer,
                        top: footerRect.top - containerRect.top,
                        bottom: footerRect.bottom - containerRect.top,
                        height: footer.offsetHeight
                    });

                    // 计算分割点
                    const segments = [];
                    let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
                    let headerHeight = header.offsetHeight;
                    currentSegment.height = headerHeight;

                    for (let i = 1; i < elements.length; i++) {
                        const element = elements[i];
                        const potentialHeight = element.bottom - currentSegment.start;

                        // 检查是否需要创建新分段
                        if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                            // 在前一个元素结束处分割
                            currentSegment.end = elements[i - 1].bottom;
                            segments.push(currentSegment);

                            // 开始新分段
                            currentSegment = {
                                start: currentSegment.end,
                                end: 0,
                                height: element.bottom - currentSegment.end,
                                includeHeader: false
                            };
                        } else {
                            currentSegment.height = potentialHeight;
                            currentSegment.end = element.bottom;
                        }
                    }

                    // 添加最后一个分段
                    if (currentSegment.height > 0) {
                        currentSegment.end = container.offsetHeight;
                        segments.push(currentSegment);
                    }

                    button.textContent = `生成中 (0/${segments.length})...`;

                    // 隐藏保存按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 为每个分段生成图片
                    const images = [];
                    for (let i = 0; i < segments.length; i++) {
                        const segment = segments[i];
                        button.textContent = `生成中 (${i + 1}/${segments.length})...`;

                        // 创建临时容器用于截图
                        const tempContainer = document.createElement('div');
                        tempContainer.style.cssText = `
                            position: absolute;
                            left: -9999px;
                            top: 0;
                            width: ${container.offsetWidth}px;
                            background: white;
                        `;
                        tempContainer.className = 'container';

                        // 克隆容器内容
                        const clonedContainer = container.cloneNode(true);

                        // 移除克隆内容中的保存按钮
                        const clonedButtons = clonedContainer.querySelector('.save-buttons');
                        if (clonedButtons) {
                            clonedButtons.style.display = 'none';
                        }

                        tempContainer.appendChild(clonedContainer);
                        document.body.appendChild(tempContainer);

                        // 等待DOM更新
                        await new Promise(resolve => setTimeout(resolve, 100));

                        // 使用html2canvas截取特定区域
                        const canvas = await html2canvas(clonedContainer, {
                            backgroundColor: '#ffffff',
                            scale: scale,
                            useCORS: true,
                            allowTaint: false,
                            imageTimeout: 10000,
                            logging: false,
                            width: container.offsetWidth,
                            height: segment.end - segment.start,
                            x: 0,
                            y: segment.start,
                            windowWidth: window.innerWidth,
                            windowHeight: window.innerHeight
                        });

                        images.push(canvas.toDataURL('image/png', 1.0));

                        // 清理临时容器
                        document.body.removeChild(tempContainer);
                    }

                    // 恢复按钮显示
                    buttons.style.visibility = 'visible';

                    // 下载所有图片
                    const now = new Date();
                    const baseFilename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

                    for (let i = 0; i < images.length; i++) {
                        const link = document.createElement('a');
                        link.download = `${baseFilename}_part${i + 1}.png`;
                        link.href = images[i];
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);

                        // 延迟一下避免浏览器阻止多个下载
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    button.textContent = `已保存 ${segments.length} 张图片!`;
                    restoreAfterScreenshot(screenshotState2);
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    console.error('分段保存失败:', error);
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    if (screenshotState2) { restoreAfterScreenshot(screenshotState2); }
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);
                }
            }

            function saveAsMarkdown() {
                var lines = [];
                var now = new Date();
                var dateStr = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
                var timeStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

                // 标题
                var headerTitle = document.querySelector('.header-title');
                lines.push('# ' + (headerTitle ? headerTitle.textContent.trim() : 'TrendRadar'));
                lines.push('');

                // 报告元信息
                var infoItems = document.querySelectorAll('.header-info .info-item');
                if (infoItems.length) {
                    infoItems.forEach(function(item) {
                        var label = item.querySelector('.info-label');
                        var value = item.querySelector('.info-value');
                        if (label && value) {
                            lines.push('- **' + label.textContent.trim() + '**: ' + value.textContent.trim());
                        }
                    });
                    lines.push('');
                }

                // 提取 news-item 通用函数
                function extractItem(item, idx) {
                    var titleEl = item.querySelector('.news-title a');
                    var titleText = '';
                    var url = '';
                    if (titleEl) {
                        titleText = titleEl.textContent.trim();
                        url = titleEl.href || '';
                    } else {
                        var titleDiv = item.querySelector('.news-title') || item.querySelector('.new-item-title');
                        if (titleDiv) titleText = titleDiv.textContent.trim();
                    }
                    if (!titleText) return '';

                    var meta = [];
                    var rank = item.querySelector('.rank-num, .new-item-rank');
                    if (rank && rank.textContent.trim() && rank.textContent.trim() !== '?') meta.push('#' + rank.textContent.trim());
                    var source = item.querySelector('.source-name');
                    if (source) meta.push(source.textContent.trim());
                    var keyword = item.querySelector('.keyword-tag');
                    if (keyword) meta.push(keyword.textContent.trim());
                    var time = item.querySelector('.time-info');
                    if (time) meta.push(time.textContent.trim());
                    var count = item.querySelector('.count-info');
                    if (count) meta.push(count.textContent.trim());

                    var line = idx + '. ';
                    if (url) {
                        line += '[' + titleText.replace(/[[\\]]/g, '') + '](' + url + ')';
                    } else {
                        line += titleText;
                    }
                    if (meta.length) line += '  `' + meta.join(' | ') + '`';
                    return line;
                }

                // 热点关键词区
                var wordGroups = document.querySelectorAll('.hotlist-section > .word-group');
                if (wordGroups.length) {
                    lines.push('## 热点新闻');
                    lines.push('');
                    wordGroups.forEach(function(group) {
                        var wordName = group.querySelector('.word-name');
                        var wordCount = group.querySelector('.word-count');
                        if (wordName) {
                            lines.push('### ' + wordName.textContent.trim() + (wordCount ? ' (' + wordCount.textContent.trim() + ')' : ''));
                            lines.push('');
                        }
                        var items = group.querySelectorAll('.news-item');
                        items.forEach(function(item, i) {
                            var line = extractItem(item, i + 1);
                            if (line) lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // 新增热点区
                var newSection = document.querySelector('.new-section');
                if (newSection) {
                    var newTitle = newSection.querySelector('.new-section-title');
                    lines.push('## ' + (newTitle ? newTitle.textContent.trim() : '本次新增热点'));
                    lines.push('');
                    var sourceGroups = newSection.querySelectorAll('.new-source-group');
                    sourceGroups.forEach(function(sg) {
                        var srcTitle = sg.querySelector('.new-source-title');
                        if (srcTitle) {
                            lines.push('### ' + srcTitle.textContent.trim());
                            lines.push('');
                        }
                        var items = sg.querySelectorAll('.new-item');
                        items.forEach(function(item, i) {
                            var line = extractItem(item, i + 1);
                            if (line) lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // RSS 订阅更新区
                var rssSection = document.querySelector('.rss-section');
                if (rssSection) {
                    var rssSectionTitle = rssSection.querySelector('.rss-section-title');
                    lines.push('## ' + (rssSectionTitle ? rssSectionTitle.textContent.trim() : 'RSS 订阅更新'));
                    lines.push('');
                    var feedGroups = rssSection.querySelectorAll('.feed-group');
                    feedGroups.forEach(function(group) {
                        var feedName = group.querySelector('.feed-name');
                        var feedCount = group.querySelector('.feed-count');
                        if (feedName) {
                            lines.push('### ' + feedName.textContent.trim() + (feedCount ? ' (' + feedCount.textContent.trim() + ')' : ''));
                            lines.push('');
                        }
                        var items = group.querySelectorAll('.rss-item');
                        items.forEach(function(item, i) {
                            var titleEl = item.querySelector('.rss-title a');
                            var titleText = titleEl ? titleEl.textContent.trim() : '';
                            var url = titleEl ? (titleEl.href || '') : '';
                            if (!titleText) return;
                            var meta = [];
                            var time = item.querySelector('.rss-time');
                            if (time) meta.push(time.textContent.trim());
                            var author = item.querySelector('.rss-author');
                            if (author) meta.push(author.textContent.trim());
                            var line = (i + 1) + '. ';
                            if (url) { line += '[' + titleText.replace(/[\\[\\]]/g, '') + '](' + url + ')'; }
                            else { line += titleText; }
                            if (meta.length) line += '  `' + meta.join(' | ') + '`';
                            lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // AI 热点分析区
                var aiSection = document.querySelector('.ai-section');
                if (aiSection) {
                    var aiError = aiSection.querySelector('.ai-error') || aiSection.querySelector('.ai-warning');
                    var aiInfo = aiSection.querySelector('.ai-info');
                    if (aiError) {
                        lines.push('## AI 分析');
                        lines.push('');
                        lines.push('> ' + aiError.textContent.trim());
                        lines.push('');
                    } else if (aiInfo) {
                        // 跳过 info 提示（如"跳过"）
                    } else {
                        var aiTitle = aiSection.querySelector('.ai-section-title');
                        lines.push('## ' + (aiTitle ? aiTitle.textContent.trim() : 'AI 热点分析'));
                        lines.push('');
                        var aiBlocks = aiSection.querySelectorAll('.ai-block');
                        aiBlocks.forEach(function(block) {
                            var blockTitle = block.querySelector('.ai-block-title');
                            var blockContent = block.querySelector('.ai-block-content');
                            if (blockTitle) {
                                lines.push('### ' + blockTitle.textContent.trim());
                                lines.push('');
                            }
                            if (blockContent) {
                                lines.push(blockContent.textContent.trim());
                                lines.push('');
                            }
                        });
                    }
                }

                // 独立展示区（热榜平台 + RSS）
                var standaloneSection = document.querySelector('.standalone-section');
                if (standaloneSection) {
                    var standaloneTitle = standaloneSection.querySelector('.standalone-section-title');
                    lines.push('## ' + (standaloneTitle ? standaloneTitle.textContent.trim() : '独立展示区'));
                    lines.push('');
                    var groups = standaloneSection.querySelectorAll('.standalone-group');
                    groups.forEach(function(group) {
                        var name = group.querySelector('.standalone-name');
                        var cnt = group.querySelector('.standalone-count');
                        if (name) {
                            lines.push('### ' + name.textContent.trim() + (cnt ? ' (' + cnt.textContent.trim() + ')' : ''));
                            lines.push('');
                        }
                        var items = group.querySelectorAll('.news-item');
                        items.forEach(function(item, i) {
                            var line = extractItem(item, i + 1);
                            if (line) lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // 错误区
                var errorSection = document.querySelector('.error-section');
                if (errorSection) {
                    var errorItems = errorSection.querySelectorAll('.error-item');
                    if (errorItems.length) {
                        lines.push('## 抓取异常');
                        lines.push('');
                        errorItems.forEach(function(item) {
                            lines.push('- ' + item.textContent.trim());
                        });
                        lines.push('');
                    }
                }

                // 页脚
                lines.push('---');
                lines.push('*Generated by TrendRadar*');

                // 下载
                var md = lines.join('\\n');
                var blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
                var link = document.createElement('a');
                var filename = 'TrendRadar_' + dateStr + '_' + timeStr.replace(':', '') + '.md';
                link.download = filename;
                link.href = URL.createObjectURL(blob);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(link.href);
            }

            // ── 筛选栏（chips + 搜索框）──

            function initFilterBar() {
                var groups = Array.from(document.querySelectorAll('.word-group[data-word]'));
                var chipRow = document.getElementById('chip-row');
                if (!chipRow || !groups.length) return;
                groups.forEach(function(g) {
                    var word = g.dataset.word;
                    var chip = document.createElement('button');
                    chip.className = 'filter-chip';
                    chip.textContent = word;
                    chip.dataset.word = word;
                    chip.addEventListener('click', function() {
                        chip.classList.toggle('active');
                        var activeWords = Array.from(chipRow.querySelectorAll('.filter-chip.active')).map(function(c) { return c.dataset.word; });
                        var combined = activeWords.join(' ');
                        var input = document.getElementById('filter-input');
                        if (input) input.value = combined;
                        _applyFilter(combined);
                        try {
                            if (combined) localStorage.setItem('trendradar-filter', combined);
                            else localStorage.removeItem('trendradar-filter');
                        } catch(e) {}
                    });
                    chipRow.appendChild(chip);
                });
            }

            function handleFilterInput(value) {
                var lv = value.trim().toLowerCase();
                document.querySelectorAll('.filter-chip').forEach(function(c) {
                    var cw = c.dataset.word.toLowerCase();
                    c.classList.toggle('active', lv.length > 0 && (cw.indexOf(lv) !== -1 || lv.indexOf(cw) !== -1));
                });
                _applyFilter(value);
                try {
                    if (value.trim()) localStorage.setItem('trendradar-filter', value);
                    else localStorage.removeItem('trendradar-filter');
                } catch(e) {}
            }

            function _applyFilter(value) {
                var section = document.querySelector('.hotlist-section');
                if (!section) return;
                var groups = Array.from(section.querySelectorAll('.word-group'));
                if (!groups.length) return;
                groups.forEach(function(g) { g.classList.remove('focused'); });
                var lv = value.trim().toLowerCase();
                if (!lv) return;
                var kws = lv.split(/[\\s,，、]+/).filter(Boolean);
                var matched = [], unmatched = [];
                groups.forEach(function(g) {
                    var word = (g.dataset.word || '').toLowerCase();
                    var hit = kws.some(function(kw) { return word.indexOf(kw) !== -1; });
                    if (hit) { g.classList.add('focused'); matched.push(g); }
                    else { unmatched.push(g); }
                });
                var parent = groups[0].parentNode;
                matched.concat(unmatched).forEach(function(g) { parent.appendChild(g); });
            }

            document.addEventListener('DOMContentLoaded', function() {
                window.scrollTo(0, 0);

                // 自动检测宽屏模式
                var savedMode = null;
                try { savedMode = localStorage.getItem('trendradar-wide-mode'); } catch(e) {}
                if (savedMode === '1' || (savedMode === null && window.innerWidth > 768)) {
                    document.body.classList.add('wide-mode');
                    var btn = document.querySelector('.toggle-wide-btn');
                    if (btn) btn.textContent = '⊡';
                }

                // 暗色模式恢复
                var savedDark = null;
                try { savedDark = localStorage.getItem('trendradar-dark-mode'); } catch(e) {}
                if (savedDark === '1') {
                    document.body.classList.add('dark-mode');
                    var darkBtn = document.querySelector('.toggle-dark-btn');
                    if (darkBtn) darkBtn.textContent = '☀';
                }

                // 启用搜索栏
                var searchBar = document.querySelector('.search-bar');
                if (searchBar) searchBar.style.display = 'block';

                // 初始化增强功能
                initTabs();
                initBackToTop();
                initCollapse();

                // 初始化筛选栏并恢复上次状态
                initFilterBar();
                (function() {
                    var saved = null;
                    try { saved = localStorage.getItem('trendradar-filter'); } catch(e) {}
                    if (saved) {
                        var fi = document.getElementById('filter-input');
                        if (fi) { fi.value = saved; handleFilterInput(saved); }
                    }
                })();

                // 键盘快捷键
                document.addEventListener('keydown', function(e) {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
                    var helpBtn = document.querySelector('.fab-help');
                    switch(e.key) {
                        case '?':
                            if (helpBtn) {
                                helpBtn.classList.toggle('show-tip');
                                var fabBar = document.querySelector('.fab-bar');
                                if (fabBar) fabBar.classList.add('visible');
                            }
                            break;
                        case 'Escape':
                            if (helpBtn) helpBtn.classList.remove('show-tip');
                            break;
                        case 'w': case 'W': toggleWideMode(); break;
                        case 'd': case 'D': toggleDarkMode(); break;
                        case '/': e.preventDefault(); var si = document.querySelector('.search-input'); if (si) si.focus(); break;
                        case 'f': case 'F': e.preventDefault(); var fi3 = document.getElementById('filter-input'); if (fi3) fi3.focus(); break;
                    }
                });

                // 阅读进度条
                var progressBar = document.querySelector('.reading-progress');
                if (progressBar) {
                    var progressTicking = false;
                    window.addEventListener('scroll', function() {
                        if (!progressTicking) {
                            requestAnimationFrame(function() {
                                var h = document.documentElement.scrollHeight - window.innerHeight;
                                progressBar.style.width = (h > 0 ? (window.scrollY / h * 100) : 0) + '%';
                                progressTicking = false;
                            });
                            progressTicking = true;
                        }
                    });
                }

                // 一键复制：hover 时数字变复制图标
                var copySvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M5 11H3.5A1.5 1.5 0 012 9.5v-7A1.5 1.5 0 013.5 1h7A1.5 1.5 0 0112 2.5V5"/></svg>';
                var checkSvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="#22c55e" stroke-width="2"><path d="M3 8.5l3.5 3.5 7-7"/></svg>';
                document.querySelectorAll('.news-item .news-number').forEach(function(numEl) {
                    var item = numEl.closest('.news-item');
                    var titleEl = item ? item.querySelector('.news-title a') : null;
                    if (!titleEl) return;
                    var numText = numEl.textContent.trim();
                    numEl.innerHTML = '<span class="num-text">' + numText + '</span><span class="copy-icon">' + copySvg + '</span>';
                    numEl.title = '点击复制标题和链接';
                    numEl.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var text = titleEl.textContent.trim() + ' ' + titleEl.href;
                        function onCopySuccess() {
                            numEl.classList.add('copied');
                            numEl.querySelector('.copy-icon').innerHTML = checkSvg;
                            setTimeout(function() {
                                numEl.classList.remove('copied');
                                numEl.querySelector('.copy-icon').innerHTML = copySvg;
                            }, 1500);
                        }
                        function fallbackCopy(str, cb) {
                            var ta = document.createElement('textarea');
                            ta.value = str; ta.style.position = 'fixed'; ta.style.opacity = '0';
                            document.body.appendChild(ta); ta.select();
                            try { document.execCommand('copy'); cb(); } catch(ex) {}
                            document.body.removeChild(ta);
                        }
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            navigator.clipboard.writeText(text).then(onCopySuccess).catch(function() {
                                fallbackCopy(text, onCopySuccess);
                            });
                        } else {
                            fallbackCopy(text, onCopySuccess);
                        }
                    });
                });



                // Header watermark 鼠标跟随揭示
                (function() {
                    var header = document.querySelector('.header');
                    var watermark = document.querySelector('.header-watermark');
                    if (!header || !watermark) return;

                    var radius = 100;

                    header.addEventListener('mousemove', function(e) {
                        var rect = watermark.getBoundingClientRect();
                        var x = e.clientX - rect.left;
                        var y = e.clientY - rect.top;
                        var maskVal = 'radial-gradient(circle ' + radius + 'px at ' + x + 'px ' + y + 'px, rgba(0,0,0,1) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0) 100%)';
                        watermark.style.webkitMaskImage = maskVal;
                        watermark.style.maskImage = maskVal;
                        watermark.style.color = 'rgba(255, 255, 255, 0.25)';
                    });

                    header.addEventListener('mouseleave', function() {
                        watermark.style.webkitMaskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)';
                        watermark.style.maskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)';
                        watermark.style.color = 'rgba(255, 255, 255, 0.15)';
                    });
                })();
            });
        </script>

        <!-- Firebase Bookmarks -->
        <div class="bm-toast" id="bm-toast"></div>
        <script type="module">
            import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js';
            import { getFirestore, collection, addDoc, getDocs, deleteDoc, doc, serverTimestamp } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js';

            const app = initializeApp({
                apiKey: "AIzaSyDDHpJD68ZMsheIK9SzNhIB7CAJk8_F6IU",
                authDomain: "retail-ai-analytics-scm.firebaseapp.com",
                projectId: "retail-ai-analytics-scm",
                storageBucket: "retail-ai-analytics-scm.firebasestorage.app",
                messagingSenderId: "1092173935797",
                appId: "1:1092173935797:web:ba58d7e2bbc7c4f9557afc"
            });
            const db = getFirestore(app);

            function showToast(msg) {
                var t = document.getElementById('bm-toast');
                t.textContent = msg;
                t.classList.add('show');
                setTimeout(function() { t.classList.remove('show'); }, 2000);
            }

            window.saveBookmark = async function(e, btn) {
                e.preventDefault();
                e.stopPropagation();

                var title = btn.dataset.title;
                var url   = btn.dataset.url;
                var src   = btn.dataset.source || '';

                if (btn.classList.contains('saved')) {
                    // 取消收藏
                    var docId = btn.dataset.docId;
                    if (!docId) {
                        try {
                            const querySnapshot = await getDocs(collection(db, 'bookmarks'));
                            querySnapshot.forEach((doc) => {
                                if (doc.data().url === url) {
                                    docId = doc.id;
                                }
                            });
                        } catch (err) {
                            showToast('获取书签失败：' + err.message);
                            return;
                        }
                    }
                    if (docId) {
                        try {
                            await deleteDoc(doc(db, 'bookmarks', docId));
                            btn.classList.remove('saved');
                            delete btn.dataset.docId;
                            btn.title = '保存书签';
                            showToast('已取消收藏');
                        } catch (err) {
                            showToast('取消收藏失败：' + err.message);
                        }
                    } else {
                        showToast('未找到该收藏记录');
                    }
                    return;
                }

                // 保存书签
                try {
                    const docRef = await addDoc(collection(db, 'bookmarks'), {
                        title: title,
                        url: url,
                        source: src,
                        savedAt: serverTimestamp()
                    });
                    btn.classList.add('saved');
                    btn.dataset.docId = docRef.id;
                    btn.title = '已保存';
                    showToast('已保存到书签 ·  sparkstudio.info/bookmarks');
                } catch(err) {
                    showToast('保存失败：' + err.message);
                }
            };

            async function syncSavedBookmarks() {
                try {
                    const querySnapshot = await getDocs(collection(db, 'bookmarks'));
                    const savedUrls = {};
                    querySnapshot.forEach((doc) => {
                        const data = doc.data();
                        if (data && data.url) {
                            savedUrls[data.url] = doc.id;
                        }
                    });
                    document.querySelectorAll('.bm-btn').forEach(btn => {
                        const url = btn.dataset.url;
                        if (url && savedUrls[url]) {
                            btn.classList.add('saved');
                            btn.dataset.docId = savedUrls[url];
                            btn.title = '已保存';
                        }
                    });
                } catch (err) {
                    console.error('同步书签状态失败:', err);
                }
            }

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', syncSavedBookmarks);
            } else {
                syncSavedBookmarks();
            }
        </script>
    </body>
    </html>
    """

    return html
