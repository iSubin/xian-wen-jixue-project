import os
import sys
import unittest
from urllib.parse import parse_qs, urlparse


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.sheng_wen.downloader.homeway_resolver import (
    HomewayResolveError,
    HomewayResolvedVideo,
    HomewayVideoResolver,
    is_homeway_graphic_video_url,
    transform_vhall_play_token,
)


class FakeHomewayResolver(HomewayVideoResolver):
    def __init__(self):
        super().__init__(
            token_provider=lambda: "login-token",
            random_int_provider=lambda: 123456789,
        )
        self.get_urls = []
        self.post_calls = []

    def _get_json(self, url, headers=None):
        self.get_urls.append(url)
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if parsed.netloc == "tydsapi.homeway.com.cn" and parsed.path == "/lecturers/video/videoInfo":
            assert query["id"] == ["5269"]
            assert query["token"] == ["login-token"]
            assert query["bigVId"] == ["41"]
            return {
                "code": 1000,
                "data": {
                    "video": {
                        "title": "第八期：维护超预期的股票池！",
                        "vh_live_id": "260368304",
                    }
                },
            }

        if parsed.netloc == "hexun.vhall.homeway.com.cn" and parsed.path == "/v3/webinars/watch/init":
            assert query["webinar_id"] == ["260368304"]
            assert query["clientType"] == ["embed"]
            return {
                "code": 200,
                "data": {
                    "interact": {
                        "paas_app_id": "15df4d3f",
                        "paas_access_token": "vhall-access-token",
                    },
                    "join_info": {
                        "join_id": 1464037827,
                        "third_party_user_id": "visit_v2053789775404568576",
                    },
                    "record": {"paas_record_id": "385ebd0b"},
                },
            }

        if parsed.netloc == "gslb.e.vhall.com" and parsed.path == "/api/dispatch_replay":
            assert query["app_id"] == ["15df4d3f"]
            assert query["webinar_id"] == ["385ebd0b"]
            assert query["uid"] == ["visit_v2053789775404568576"]
            assert query["bu"] == ["1"]
            assert query["rand"] == ["123456789"]
            assert query["app_custom_line"] == ["1"]
            assert query["uri"] == ["/vhallyun/video.m3u8"]
            assert query["quality"] == ['["a","same"]']
            return {
                "code": "200",
                "data": {
                    "token": "media-token",
                    "hls_domainnames": {
                        "same": [
                            {
                                "line": "线路1",
                                "hls_domainname": "https://cdn.example.com/vhallyun/video.m3u8",
                            }
                        ]
                    },
                },
            }

        raise AssertionError(f"Unexpected GET URL: {url}")

    def _post_form(self, url, form_data, headers=None):
        self.post_calls.append((url, form_data))
        parsed = urlparse(url)
        assert parsed.netloc == "api.vhallyun.com"
        assert parsed.path == "/sdk/v2/demand/get-record-watch-info"
        assert form_data["app_id"] == "15df4d3f"
        assert form_data["third_party_user_id"] == "visit_v2053789775404568576"
        assert form_data["client"] == "pc_browser"
        assert form_data["access_token"] == "vhall-access-token"
        assert form_data["package_check"] == "peter"
        assert form_data["record_id"] == "385ebd0b"
        return {
            "code": 200,
            "data": {
                "dispatch_server": "https://gslb.e.vhall.com",
                "default_server": {
                    "uri": "/vhallyun/video.m3u8",
                    "token": "rawtoken_media",
                },
                "log_info": {"uid": "1464037827"},
            },
        }


class TestHomewayResolver(unittest.TestCase):
    def test_detects_homeway_graphic_video_url(self):
        self.assertTrue(
            is_homeway_graphic_video_url(
                "https://tyds.homeway.com.cn/#/GraphicVideo?key=5269&time=1780159764519"
            )
        )
        self.assertFalse(is_homeway_graphic_video_url("https://www.bilibili.com/video/BV123"))

    def test_resolves_graphic_video_page_to_tokenized_hls(self):
        resolver = FakeHomewayResolver()

        resolved = resolver.resolve(
            "https://tyds.homeway.com.cn/#/GraphicVideo?key=5269&time=1780159764519"
        )

        self.assertIsInstance(resolved, HomewayResolvedVideo)
        self.assertEqual(resolved.title, "第八期：维护超预期的股票池！")
        self.assertEqual(resolved.vhall_id, "260368304")
        self.assertEqual(
            resolved.media_url,
            "https://cdn.example.com/vhallyun/video.m3u8?token=7792124F_media",
        )
        self.assertEqual(len(resolver.post_calls), 1)

    def test_transforms_vhall_origin_token_before_attaching_to_hls(self):
        self.assertEqual(transform_vhall_play_token("rawtoken_media"), "7792124F_media")

    def test_requires_login_token_for_graphic_video_api(self):
        resolver = HomewayVideoResolver(token_provider=lambda: "")

        with self.assertRaisesRegex(HomewayResolveError, "web_qtstr"):
            resolver.resolve("https://tyds.homeway.com.cn/#/GraphicVideo?key=5269")


if __name__ == "__main__":
    unittest.main()
