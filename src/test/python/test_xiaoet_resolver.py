import os
import sys
import unittest
from urllib.parse import parse_qs, urlparse


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.downloader.xiaoet_resolver import (
    XiaoetResolveError,
    XiaoetResolvedVideo,
    XiaoetVideoResolver,
    is_xiaoet_video_url,
)


XIAOET_URL = (
    "https://appexpqpqic7617.h5.xiaoeknow.com/p/course/video/"
    "v_6a1bb3d3e4b0694c5bcd891a"
    "?product_id=course_399CpkSHAX4hucHg2pKn8vy2OWb"
    "&course_id=course_399CpkSHAX4hucHg2pKn8vy2OWb"
    "&sub_course_id=subcourse_39BgZkJNNvVbnSctrBRrXK1WRN8"
)


class FakeXiaoetResolver(XiaoetVideoResolver):
    def __init__(self):
        super().__init__(cookie_provider=lambda host: "xiaoet_session=abc; user=123")
        self.json_calls = []
        self.form_calls = []

    def _post_json(self, url, payload, headers=None):
        self.json_calls.append((url, payload, headers))
        parsed = urlparse(url)

        if parsed.path == "/xe.micro_page.navigation.get/1.0.0":
            assert parsed.netloc == "appexpqpqic7617.h5.xiaoeknow.com"
            assert payload["app_id"] == "appexpqpqic7617"
            assert payload["agent_type"] == 1
            assert "xiaoet_session=abc" in headers["Cookie"]
            return {"code": 0, "data": {"user_id": "u_69eb5b96072f4"}}

        if parsed.path == "/xe.material-center.play/getPlayUrl":
            assert parsed.netloc == "appexpqpqic7617.h5.xiaoeknow.com"
            assert payload["org_app_id"] == "appexpqpqic7617"
            assert payload["app_id"] == "appexpqpqic7617"
            assert payload["user_id"] == "u_69eb5b96072f4"
            assert payload["play_sign"] == ["play-sign-001"]
            assert payload["play_line"] == "A"
            return {
                "code": 0,
                "data": {
                    "play-sign-001": {
                        "play_list": {
                            "720p_hls": {
                                "play_url": "https://vod.example.com/720/video.m3u8?sign=720&t=t&us=u"
                            },
                            "1080p_hls": {
                                "play_url": "https://vod.example.com/1080/video.m3u8?sign=1080&t=t&us=u"
                            },
                        }
                    }
                },
            }

        raise AssertionError(f"Unexpected JSON URL: {url}")

    def _post_form(self, url, form_data, headers=None):
        self.form_calls.append((url, form_data, headers))
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        assert query == {}
        assert parsed.netloc == "appexpqpqic7617.h5.xiaoeknow.com"
        assert parsed.path == "/xe.course.business.video.detail_info.get/2.0.0"
        assert form_data["bizData[resource_id]"] == "v_6a1bb3d3e4b0694c5bcd891a"
        assert form_data["bizData[product_id]"] == "course_399CpkSHAX4hucHg2pKn8vy2OWb"
        assert form_data["bizData[opr_sys]"] == "MacIntel"
        assert "xiaoet_session=abc" in headers["Cookie"]
        return {
            "code": 0,
            "data": {
                "video_info": {
                    "title": "前7轮基钦周期详细拆解与2030-2037推演",
                    "play_sign": "play-sign-001",
                }
            },
        }


class TestXiaoetResolver(unittest.TestCase):
    def test_detects_xiaoet_video_url(self):
        self.assertTrue(is_xiaoet_video_url(XIAOET_URL))
        self.assertFalse(is_xiaoet_video_url("https://www.bilibili.com/video/BV123"))

    def test_resolves_xiaoet_page_to_best_hls_play_url(self):
        resolver = FakeXiaoetResolver()

        resolved = resolver.resolve(XIAOET_URL)

        self.assertIsInstance(resolved, XiaoetResolvedVideo)
        self.assertEqual(resolved.resource_id, "v_6a1bb3d3e4b0694c5bcd891a")
        self.assertEqual(resolved.product_id, "course_399CpkSHAX4hucHg2pKn8vy2OWb")
        self.assertEqual(resolved.quality, "1080p_hls")
        self.assertEqual(resolved.title, "前7轮基钦周期详细拆解与2030-2037推演")
        self.assertEqual(
            resolved.media_url,
            "https://vod.example.com/1080/video.m3u8?sign=1080&t=t&us=u",
        )
        self.assertEqual(len(resolver.json_calls), 2)
        self.assertEqual(len(resolver.form_calls), 1)

    def test_requires_cookie_for_xiaoet_api(self):
        resolver = XiaoetVideoResolver(cookie_provider=lambda host: "")

        with self.assertRaisesRegex(XiaoetResolveError, "Cookie"):
            resolver.resolve(XIAOET_URL)


if __name__ == "__main__":
    unittest.main()
