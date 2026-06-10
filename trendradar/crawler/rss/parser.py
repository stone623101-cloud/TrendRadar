# coding=utf-8
"""
RSS 解析器

支持 RSS 2.0、Atom 和 JSON Feed 1.1 格式的解析
"""

import re
import html
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from email.utils import parsedate_to_datetime

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    feedparser = None


@dataclass
class ParsedRSSItem:
    """解析后的 RSS 条目"""
    title: str
    url: str
    published_at: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    guid: Optional[str] = None


class RSSParser:
    """RSS 解析器"""

    def __init__(self, max_summary_length: int = 500):
        """
        初始化解析器

        Args:
            max_summary_length: 摘要最大长度
        """
        if not HAS_FEEDPARSER:
            raise ImportError("RSS 解析需要安装 feedparser: pip install feedparser")

        self.max_summary_length = max_summary_length

    def parse(self, content: str, feed_url: str = "") -> List[ParsedRSSItem]:
        """
        解析 RSS/Atom/JSON Feed 内容

        Args:
            content: Feed 内容（XML 或 JSON）
            feed_url: Feed URL（用于错误提示）

        Returns:
            解析后的条目列表
        """
        # 拦截并解析 TradingView 新闻页面
        if feed_url and "tradingview.com/news" in feed_url:
            return self._parse_tradingview(content, feed_url)

        # 拦截并解析 Current Market Valuation 的巴菲特指标页面
        if feed_url and "currentmarketvaluation.com/models/buffett-indicator.php" in feed_url:
            return self._parse_currentmarketvaluation_buffett(content, feed_url)

        # 先尝试检测 JSON Feed
        if self._is_json_feed(content):
            return self._parse_json_feed(content, feed_url)

        # 使用 feedparser 解析 RSS/Atom
        feed = feedparser.parse(content)

        if feed.bozo and not feed.entries:
            raise ValueError(f"RSS 解析失败 ({feed_url}): {feed.bozo_exception}")

        items = []
        for entry in feed.entries:
            item = self._parse_entry(entry)
            if item:
                items.append(item)

        return items

    def _is_json_feed(self, content: str) -> bool:
        """
        检测内容是否为 JSON Feed 格式

        JSON Feed 必须包含 version 字段，值为 https://jsonfeed.org/version/1 或 1.1
        """
        content = content.strip()
        if not content.startswith("{"):
            return False

        try:
            data = json.loads(content)
            version = data.get("version", "")
            return "jsonfeed.org" in version
        except (json.JSONDecodeError, TypeError):
            return False

    def _parse_json_feed(self, content: str, feed_url: str = "") -> List[ParsedRSSItem]:
        """
        解析 JSON Feed 1.1 格式

        JSON Feed 规范: https://www.jsonfeed.org/version/1.1/

        Args:
            content: JSON Feed 内容
            feed_url: Feed URL（用于错误提示）

        Returns:
            解析后的条目列表
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON Feed 解析失败 ({feed_url}): {e}")

        items_data = data.get("items", [])
        if not items_data:
            return []

        items = []
        for item_data in items_data:
            item = self._parse_json_feed_item(item_data)
            if item:
                items.append(item)

        return items

    def _parse_json_feed_item(self, item_data: Dict[str, Any]) -> Optional[ParsedRSSItem]:
        """解析单个 JSON Feed 条目"""
        url = item_data.get("url", "") or item_data.get("external_url", "")

        title = item_data.get("title", "")
        if not title:
            content_text = item_data.get("content_text", "")
            if content_text:
                title = content_text[:20] + ("..." if len(content_text) > 20 else "")

        title = self._clean_text(title)
        if not title and url:
            title = url
        if not title:
            return None

        # 发布时间（ISO 8601 格式）
        published_at = None
        date_str = item_data.get("date_published") or item_data.get("date_modified")
        if date_str:
            published_at = self._parse_iso_date(date_str)

        # 摘要：优先 summary，否则使用 content_text
        summary = item_data.get("summary", "")
        if not summary:
            content_text = item_data.get("content_text", "")
            content_html = item_data.get("content_html", "")
            summary = content_text or self._clean_text(content_html)

        if summary:
            summary = self._clean_text(summary)
            if len(summary) > self.max_summary_length:
                summary = summary[:self.max_summary_length] + "..."

        # 作者
        author = None
        authors = item_data.get("authors", [])
        if authors:
            names = [a.get("name", "") for a in authors if isinstance(a, dict) and a.get("name")]
            if names:
                author = ", ".join(names)

        # GUID
        guid = item_data.get("id", "") or url

        return ParsedRSSItem(
            title=title,
            url=url,
            published_at=published_at,
            summary=summary or None,
            author=author,
            guid=guid,
        )

    def _parse_iso_date(self, date_str: str) -> Optional[str]:
        """解析 ISO 8601 日期格式"""
        if not date_str:
            return None

        try:
            # 处理常见的 ISO 8601 格式
            # 替换 Z 为 +00:00
            date_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(date_str)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass

        return None

    def parse_url(self, url: str, timeout: int = 10) -> List[ParsedRSSItem]:
        """
        从 URL 解析 RSS

        Args:
            url: RSS URL
            timeout: 超时时间（秒）

        Returns:
            解析后的条目列表
        """
        import requests

        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "TrendRadar/2.0 RSS Reader"
        })
        response.raise_for_status()

        return self.parse(response.text, url)

    def _parse_entry(self, entry: Any) -> Optional[ParsedRSSItem]:
        """解析单个条目"""
        title = self._clean_text(entry.get("title", ""))

        url = entry.get("link", "")
        if not url:
            links = entry.get("links", [])
            for link in links:
                if link.get("rel") == "alternate" or link.get("type", "").startswith("text/html"):
                    url = link.get("href", "")
                    break
            if not url and links:
                url = links[0].get("href", "")

        if not title:
            raw_summary = entry.get("summary") or entry.get("description", "")
            if not raw_summary:
                content = entry.get("content", [])
                if content and isinstance(content, list):
                    raw_summary = content[0].get("value", "")
            if raw_summary:
                title = self._clean_text(raw_summary)
                if len(title) > 20:
                    title = title[:20] + "..."
            if not title and url:
                title = url

        if not title:
            return None

        published_at = self._parse_date(entry)
        summary = self._parse_summary(entry)
        author = self._parse_author(entry)
        guid = entry.get("id") or entry.get("guid", {}).get("value") or url

        return ParsedRSSItem(
            title=title,
            url=url,
            published_at=published_at,
            summary=summary,
            author=author,
            guid=guid,
        )

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""

        # 解码 HTML 实体
        text = html.unescape(text)

        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _parse_date(self, entry: Any) -> Optional[str]:
        """解析发布日期"""
        # feedparser 会自动解析日期到 published_parsed
        date_struct = entry.get("published_parsed") or entry.get("updated_parsed")

        if date_struct:
            try:
                dt = datetime(*date_struct[:6])
                return dt.isoformat()
            except (ValueError, TypeError):
                pass

        # 尝试手动解析
        date_str = entry.get("published") or entry.get("updated")
        if date_str:
            try:
                dt = parsedate_to_datetime(date_str)
                return dt.isoformat()
            except (ValueError, TypeError):
                pass

            # 尝试 ISO 格式
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.isoformat()
            except (ValueError, TypeError):
                pass

        return None

    def _parse_summary(self, entry: Any) -> Optional[str]:
        """解析摘要"""
        summary = entry.get("summary") or entry.get("description", "")

        if not summary:
            # 尝试从 content 获取
            content = entry.get("content", [])
            if content and isinstance(content, list):
                summary = content[0].get("value", "")

        if not summary:
            return None

        summary = self._clean_text(summary)

        # 截断过长的摘要
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length] + "..."

        return summary

    def _parse_author(self, entry: Any) -> Optional[str]:
        """解析作者"""
        author = entry.get("author")
        if author:
            return self._clean_text(author)

        # 尝试从 dc:creator 获取
        author = entry.get("dc_creator")
        if author:
            return self._clean_text(author)

        # 尝试从 authors 列表获取
        authors = entry.get("authors", [])
        if authors:
            names = [a.get("name", "") for a in authors if a.get("name")]
            if names:
                return ", ".join(names)

        return None

    def _parse_tradingview(self, content: str, feed_url: str) -> List[ParsedRSSItem]:
        """解析 TradingView HTML 页面中的嵌入 JSON 新闻数据"""
        import json
        import re
        from urllib.parse import urlparse
        from datetime import datetime
        import pytz

        # 匹配包含 widgets 的 script 标签
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        
        target_script = None
        for script in scripts:
            if '"widgets"' in script and '"news"' in script:
                target_script = script
                break

        if not target_script:
            # 回退方案：寻找看起来像完整 JSON 且包含 widgets 的脚本标签
            for script in scripts:
                script_trimmed = script.strip()
                if script_trimmed.startswith('{') and script_trimmed.endswith('}'):
                    try:
                        data = json.loads(script_trimmed)
                        for k, v in data.items():
                            if isinstance(v, dict) and 'widgets' in v:
                                target_script = script_trimmed
                                break
                    except Exception:
                        continue
                if target_script:
                    break

        if not target_script:
            raise ValueError(f"Could not find TradingView news data script in HTML for {feed_url}")

        # 解析 JSON 数据
        try:
            data = json.loads(target_script.strip())
        except Exception as e:
            # 尝试提取大括号界限
            start_idx = target_script.find('{')
            end_idx = target_script.rfind('}')
            if start_idx != -1 and end_idx != -1:
                try:
                    data = json.loads(target_script[start_idx:end_idx+1])
                except Exception as e2:
                    raise ValueError(f"Failed to parse extracted JSON from TradingView script: {e2}")
            else:
                raise ValueError(f"Failed to parse TradingView script JSON: {e}")

        # 查找包含 widgets 的根字典
        widgets = None
        for k, v in data.items():
            if isinstance(v, dict) and 'widgets' in v:
                widgets = v['widgets']
                break

        if not widgets:
            raise ValueError("No widgets dictionary found in parsed TradingView JSON")

        stories = []
        seen_ids = set()
        
        # 排序策略：优先合并以下常用 widget 里的文章
        widget_keys = list(widgets.keys())
        prioritized = ['news_top_stories', 'news_markets', 'news_corp_activity']
        for pk in reversed(prioritized):
            if pk in widget_keys:
                widget_keys.remove(pk)
                widget_keys.insert(0, pk)

        for w_key in widget_keys:
            widget_data = widgets[w_key]
            try:
                items = widget_data['data']['news']['data']['items']
                for item in items:
                    item_id = item.get('id')
                    if item_id and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        stories.append(item)
            except (KeyError, TypeError):
                continue

        parsed_items = []
        parsed_url = urlparse(feed_url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        for item in stories:
            title = self._clean_text(item.get('title', ''))
            story_path = item.get('storyPath', '')
            url = origin + story_path if story_path else item.get('link', '')

            published_at = None
            pub_timestamp = item.get('published')
            if pub_timestamp:
                try:
                    dt = datetime.fromtimestamp(pub_timestamp, tz=pytz.UTC)
                    published_at = dt.isoformat()
                except Exception:
                    pass

            provider = item.get('provider', {})
            author = provider.get('name') if isinstance(provider, dict) else None

            related = item.get('relatedSymbols', [])
            summary = ""
            if related and isinstance(related, list):
                symbols = [s.get('symbol') for s in related if isinstance(s, dict) and s.get('symbol')]
                if symbols:
                    summary = f"Related symbols: {', '.join(symbols)}"

            parsed_items.append(
                ParsedRSSItem(
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=summary or None,
                    author=author,
                    guid=item.get('id', url)
                )
            )

        return parsed_items

    def _parse_currentmarketvaluation_buffett(self, content: str, feed_url: str) -> List[ParsedRSSItem]:
        """解析 Current Market Valuation 的巴菲特指标页面"""
        # 提取更新日期
        date_match = re.search(r'Updated on\s*</span>\s*<span class="card-author">\s*([^<]+)\s*</span>', content, re.IGNORECASE)
        if not date_match:
            date_match = re.search(r'As of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', content, re.IGNORECASE)
        
        date_str = date_match.group(1).strip() if date_match else ""
        
        # 提取当前数值
        val_match = re.search(r'Buffett Indicator\s*</span>\s*=\s*.*?(\d+%)', content, re.DOTALL | re.IGNORECASE)
        if not val_match:
            val_match = re.search(r'calculate the Buffett Indicator as\s+(\d+%)', content, re.IGNORECASE)
        if not val_match:
            val_match = re.search(r'fw-bold[^>]*>(\d+%)', content, re.IGNORECASE)
            
        val_str = val_match.group(1).strip() if val_match else "Unknown"
        
        # 提取状态（如 Strongly Overvalued）
        status_match = re.search(r'class="badge header-status-badge[^>]*>([^<]+)</span>', content, re.IGNORECASE)
        if not status_match:
            status_match = re.search(r'suggesting that the US stock market is\s*</span>\s*<span[^>]*>([^<]+)</span>', content, re.IGNORECASE)
        
        status_str = status_match.group(1).strip() if status_match else "Unknown"
        
        # 提取总市值和 GDP
        mkt_val_match = re.search(r'Total US Stock Market Value\s*=\s*(\$[0-9.]+[TMB])', content, re.IGNORECASE)
        gdp_match = re.search(r'Annualized GDP\s*=\s*(\$[0-9.]+[TMB])', content, re.IGNORECASE)
        
        mkt_val = mkt_val_match.group(1).strip() if mkt_val_match else ""
        gdp_val = gdp_match.group(1).strip() if gdp_match else ""
        
        # 格式化发布时间
        published_at = None
        if date_str:
            try:
                clean_date = re.sub(r'\s+', ' ', date_str)
                dt = datetime.strptime(clean_date, "%B %d, %Y")
                published_at = dt.isoformat()
            except Exception:
                pass
                
        # 构建标题和摘要
        title = f"巴菲特指标 (Buffett Indicator): {val_str} ({status_str})"
        if date_str:
            title += f" - {date_str}"
            
        summary_parts = []
        summary_parts.append(f"最新更新时间: {date_str or '未知'}")
        summary_parts.append(f"巴菲特指标数值: {val_str}")
        summary_parts.append(f"市场估值状态: {status_str}")
        if mkt_val:
            summary_parts.append(f"美股总市值: {mkt_val}")
        if gdp_val:
            summary_parts.append(f"美国 annualized GDP: {gdp_val}")
            
        desc_match = re.search(r'The current ratio of \d+%.*?above the historical trend line.*?relative to GDP\.', content, re.DOTALL)
        if desc_match:
            summary_parts.append(self._clean_text(desc_match.group(0)))
            
        summary = "\n".join(summary_parts)
        
        guid_seed = date_str or val_str
        guid_clean = re.sub(r'[^a-zA-Z0-9]', '', guid_seed).lower()
        guid = f"currentmarketvaluation-buffett-{guid_clean}"
        
        return [
            ParsedRSSItem(
                title=title,
                url=feed_url,
                published_at=published_at,
                summary=summary,
                author="Current Market Valuation",
                guid=guid
            )
        ]
