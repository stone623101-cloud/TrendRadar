# coding=utf-8
import tempfile
import unittest
import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


frequency = load_module("frequency_under_test", "trendradar/core/frequency.py")
builder = load_module("builder_under_test", "trendradar/report/page/builder.py")

load_frequency_words = frequency.load_frequency_words
build_unified_page_data = builder.build_unified_page_data


class FrequencyCategoryTests(unittest.TestCase):
    def test_category_directive_applies_until_next_directive(self):
        content = """
[WORD_GROUPS]

[[科技AI]]

[AI 相关]
人工智能

芯片

[[国际局势]]

[北美]
美国
加拿大
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "frequency_words.txt"
            path.write_text(content, encoding="utf-8")
            groups, _, _ = load_frequency_words(str(path))

        self.assertEqual(groups[0]["display_name"], "AI 相关")
        self.assertEqual(groups[0]["category"], "科技AI")
        self.assertEqual(groups[1]["display_name"], "芯片")
        self.assertEqual(groups[1]["category"], "科技AI")
        self.assertEqual(groups[2]["display_name"], "北美")
        self.assertEqual(groups[2]["category"], "国际局势")


class UnifiedFeedBuilderTests(unittest.TestCase):
    def test_merges_by_url_and_marks_rss_new_once(self):
        report_data = {
            "stats": [
                {
                    "word": "华为",
                    "category": "企业品牌",
                    "titles": [
                        {
                            "title": "华为发布新品",
                            "source_name": "知乎",
                            "url": "https://example.com/a",
                            "ranks": [3],
                            "time_display": "12:30",
                        }
                    ],
                }
            ],
            "new_titles": [],
        }
        rss_items = [
            {
                "word": "华为",
                "category": "企业品牌",
                "titles": [
                    {
                        "title": "华为发布新品",
                        "source_name": "BBC News",
                        "url": "https://example.com/a",
                        "time_display": "2026-06-11T12:35:00",
                    }
                ],
            }
        ]
        rss_new_items = [
            {
                "word": "华为",
                "titles": [
                    {
                        "title": "华为发布新品",
                        "url": "https://example.com/a",
                    }
                ],
            }
        ]

        page_data = build_unified_page_data(
            report_data,
            rss_items=rss_items,
            rss_new_items=rss_new_items,
        )

        self.assertEqual(page_data["total_count"], 1)
        item = page_data["items"][0]
        self.assertTrue(item["is_new"])
        self.assertEqual(item["category"], "企业品牌")
        self.assertEqual(item["heat"], 197)
        self.assertEqual([source["name"] for source in item["sources"]], ["知乎", "BBC News"])

    def test_standalone_only_does_not_gain_heat_from_rank(self):
        page_data = build_unified_page_data(
            {"stats": [], "new_titles": []},
            standalone_data={
                "platforms": [
                    {
                        "id": "zhihu",
                        "name": "知乎",
                        "category": "其他",
                        "items": [
                            {"title": "独立榜首", "url": "https://example.com/standalone", "rank": 1}
                        ],
                    }
                ]
            },
        )

        self.assertEqual(page_data["items"][0]["heat"], 0)


if __name__ == "__main__":
    unittest.main()
