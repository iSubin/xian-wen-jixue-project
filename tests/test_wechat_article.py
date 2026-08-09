import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src", "main", "python"))

from sheng_wen.db import TaskDB, TaskStatus
from sheng_wen.wechat_article import (
    WechatArticleCaptureError,
    build_wechat_account_history_from_payload,
    capture_wechat_article_from_html,
    extract_wechat_account_identity_from_html,
    is_wechat_article_url,
    parse_wechat_history_payload,
    read_wechat_cookie_header_from_browser,
)


SAMPLE_WECHAT_HTML = """
<html>
  <head>
    <meta property="og:title" content="测试文章">
    <meta property="og:article:author" content="测试公众号">
    <meta property="og:description" content="这是一段描述">
    <script>
      var biz = "MzTestBiz";
      var nickname = "测试公众号";
      var appmsg_token = "history-token";
      var createTime = '2026-04-09 16:58';
    </script>
  </head>
  <body>
    <div id="js_content">
      <h2>第一节</h2>
      <p>正文内容</p>
      <img data-src="https://mmbiz.qpic.cn/test.jpg">
    </div>
  </body>
</html>
"""

SAMPLE_HISTORY_PAYLOAD = {
    "ret": 0,
    "general_msg_list": json.dumps(
        {
            "list": [
                {
                    "comm_msg_info": {"datetime": 1775725080},
                    "app_msg_ext_info": {
                        "title": "主文章",
                        "content_url": "https:\\/\\/mp.weixin.qq.com\\/s\\/main?__biz=MzTestBiz",
                        "digest": "主文章摘要",
                        "cover": "https://mmbiz.qpic.cn/cover-main.jpg",
                        "multi_app_msg_item_list": [
                            {
                                "title": "副文章",
                                "content_url": "https://mp.weixin.qq.com/s/sub",
                                "digest": "副文章摘要",
                                "cover": "https://mmbiz.qpic.cn/cover-sub.jpg",
                            }
                        ],
                    },
                }
            ]
        },
        ensure_ascii=False,
    ),
}


class TaskSourceFieldsPersistenceTest(unittest.TestCase):
    def test_task_source_fields_round_trip_in_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database = TaskDB(database_url=f"sqlite:///{os.path.join(tmpdir, 'test.db')}")
            source_meta = {
                "author": "作者",
                "account": "公众号",
                "publish_time": "2026-04-09 16:58",
                "image_count": 2,
            }

            database.save_task(
                "article-task",
                {
                    "id": "article-task",
                    "video_url": "https://mp.weixin.qq.com/s/example",
                    "source_type": "wechat_article",
                    "source_url": "https://mp.weixin.qq.com/s/example",
                    "source_meta": json.dumps(source_meta, ensure_ascii=False),
                    "status": TaskStatus.SUMMARIZING,
                    "progress": 0.0,
                    "title": "文章标题",
                    "transcript": "# 文章标题\n\n正文",
                    "summary": "",
                },
            )

            task = database.get_task("article-task")

            self.assertEqual(task["source_type"], "wechat_article")
            self.assertEqual(task["source_url"], "https://mp.weixin.qq.com/s/example")
            self.assertEqual(json.loads(task["source_meta"])["account"], "公众号")

    def test_regular_video_task_defaults_to_video_source_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database = TaskDB(database_url=f"sqlite:///{os.path.join(tmpdir, 'test.db')}")
            database.save_task(
                "video-task",
                {
                    "id": "video-task",
                    "video_url": "https://www.bilibili.com/video/BV123",
                    "status": TaskStatus.PENDING,
                    "progress": 0.0,
                },
            )

            task = database.get_task("video-task")

            self.assertEqual(task["source_type"], "video")
            self.assertEqual(task["source_url"], "https://www.bilibili.com/video/BV123")
            self.assertIsNone(task["source_meta"])


class WechatArticleAdapterTest(unittest.TestCase):
    def test_is_wechat_article_url_accepts_mp_domain_only(self):
        self.assertTrue(is_wechat_article_url("https://mp.weixin.qq.com/s/example"))
        self.assertTrue(is_wechat_article_url("https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum"))
        self.assertFalse(is_wechat_article_url("https://weixin.qq.com/s/example"))
        self.assertFalse(is_wechat_article_url("https://example.com/s/example"))

    def test_capture_from_html_extracts_metadata_and_markdown(self):
        result = capture_wechat_article_from_html(
            "https://mp.weixin.qq.com/s/example",
            SAMPLE_WECHAT_HTML,
            download_images=False,
        )

        self.assertEqual(result.title, "测试文章")
        self.assertEqual(result.author, "测试公众号")
        self.assertEqual(result.publish_time, "2026-04-09 16:58")
        self.assertEqual(result.description, "这是一段描述")
        self.assertIn("## 第一节", result.raw_markdown)
        self.assertIn("正文内容", result.raw_markdown)
        self.assertEqual(result.metadata["image_count"], 1)

    def test_capture_from_html_rewrites_downloaded_image_to_public_asset_path(self):
        class FakeResponse:
            headers = {"Content-Type": "image/jpeg"}

            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size=8192):
                yield b"fake image"

        class FakeSession:
            def __init__(self):
                self.headers = {}

            def get(self, url, timeout=20, stream=True):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sheng_wen.wechat_article.requests.Session", FakeSession):
                result = capture_wechat_article_from_html(
                    "https://mp.weixin.qq.com/s/example",
                    SAMPLE_WECHAT_HTML,
                    output_dir=tmpdir,
                    markdown_image_base="/task-assets/task-1",
                )

            self.assertIn("/task-assets/task-1/images/wechat_01.jpg", result.raw_markdown)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "images", "wechat_01.jpg")))
            self.assertEqual(result.images[0].status, "downloaded")

    def test_capture_from_html_rejects_missing_body(self):
        with self.assertRaisesRegex(WechatArticleCaptureError, "无法找到文章正文"):
            capture_wechat_article_from_html(
                "https://mp.weixin.qq.com/s/example",
                "<html><body></body></html>",
                download_images=False,
            )

    def test_extract_account_identity_from_article_html(self):
        identity = extract_wechat_account_identity_from_html(
            "https://mp.weixin.qq.com/s/example",
            SAMPLE_WECHAT_HTML,
        )

        self.assertEqual(identity.biz, "MzTestBiz")
        self.assertEqual(identity.account_name, "测试公众号")
        self.assertEqual(identity.appmsg_token, "history-token")

    def test_extract_account_identity_accepts_object_property_token(self):
        html = """
        <html>
          <head>
            <meta property="og:article:author" content="对象公众号">
            <script>
              window.cgiData = {
                biz: "MzObjectBiz",
                appmsg_token: "object-token"
              };
            </script>
          </head>
          <body><div id="js_content">正文</div></body>
        </html>
        """

        identity = extract_wechat_account_identity_from_html(
            "https://mp.weixin.qq.com/s/example",
            html,
        )

        self.assertEqual(identity.biz, "MzObjectBiz")
        self.assertEqual(identity.account_name, "对象公众号")
        self.assertEqual(identity.appmsg_token, "object-token")

    def test_extract_account_identity_does_not_match_html_attribute_nickname(self):
        html = """
        <html>
          <head>
            <meta property="og:article:author" content="正确公众号">
            <script>
              var biz = "MzAttrBiz";
              window.appmsg_token = "attr-token";
            </script>
          </head>
          <body>
            <div id="js_content">
              <a data-miniprogram-nickname="错误昵称">小程序</a>
            </div>
          </body>
        </html>
        """

        identity = extract_wechat_account_identity_from_html(
            "https://mp.weixin.qq.com/s/example",
            html,
        )

        self.assertEqual(identity.account_name, "正确公众号")

    def test_read_wechat_cookie_header_from_browser_uses_browser_cookie3_when_available(self):
        class FakeCookie:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        class FakeBrowserCookie3:
            @staticmethod
            def chrome(domain_name):
                self.assertEqual(domain_name, "mp.weixin.qq.com")
                return [
                    FakeCookie("ua_id", "ua-value"),
                    FakeCookie("mm_lang", "zh_CN"),
                    FakeCookie("ua_id", "duplicate"),
                    FakeCookie("empty", ""),
                ]

        with patch.dict(sys.modules, {"browser_cookie3": FakeBrowserCookie3}):
            header, source = read_wechat_cookie_header_from_browser()

        self.assertEqual(header, "ua_id=ua-value; mm_lang=zh_CN")
        self.assertEqual(source, "Google Chrome")

    def test_parse_wechat_history_payload_expands_multi_article_messages(self):
        items = parse_wechat_history_payload(SAMPLE_HISTORY_PAYLOAD)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "主文章")
        self.assertEqual(items[0].source_url, "https://mp.weixin.qq.com/s/main?__biz=MzTestBiz")
        self.assertEqual(items[0].digest, "主文章摘要")
        self.assertEqual(items[0].publish_time, "2026-04-09 16:58:00")
        self.assertEqual(items[1].title, "副文章")
        self.assertEqual(items[1].source_url, "https://mp.weixin.qq.com/s/sub")

    def test_build_account_history_from_payload_uses_article_identity(self):
        history = build_wechat_account_history_from_payload(
            "https://mp.weixin.qq.com/s/example",
            SAMPLE_WECHAT_HTML,
            SAMPLE_HISTORY_PAYLOAD,
            limit=1,
        )

        self.assertEqual(history.account_name, "测试公众号")
        self.assertEqual(history.biz, "MzTestBiz")
        self.assertEqual(history.source_url, "https://mp.weixin.qq.com/s/example")
        self.assertEqual(len(history.items), 1)
        self.assertEqual(history.items[0].title, "主文章")


class WechatArticleTaskPayloadTest(unittest.TestCase):
    def test_article_task_payload_contains_source_metadata(self):
        from sheng_wen.api import _build_wechat_article_task_data
        from sheng_wen.wechat_article import CapturedArticle

        article = CapturedArticle(
            source_type="wechat_article",
            source_url="https://mp.weixin.qq.com/s/example",
            title="测试文章",
            author="测试公众号",
            publish_time="2026-04-09 16:58",
            description="描述",
            raw_markdown="# 测试文章\n\n正文",
            plain_text="正文",
            metadata={"author": "测试公众号", "publish_time": "2026-04-09 16:58", "image_count": 0},
        )

        payload = _build_wechat_article_task_data(
            "task-1",
            article,
            folder_id="folder-1",
            summary_mode="standard",
        )

        self.assertEqual(payload["source_type"], "wechat_article")
        self.assertEqual(payload["source_url"], "https://mp.weixin.qq.com/s/example")
        self.assertEqual(payload["video_url"], "https://mp.weixin.qq.com/s/example")
        self.assertEqual(payload["folder_id"], "folder-1")
        self.assertEqual(payload["transcript"], "# 测试文章\n\n正文")
        self.assertEqual(payload["status"], TaskStatus.SUMMARIZING)


if __name__ == "__main__":
    unittest.main()
