import unittest
from datetime import timezone

from src.main.python.xianwen.homeway_subscription import (
    HomewayListItem,
    HomewaySubscriptionAdapter,
    HomewaySubscriptionError,
    parse_homeway_datetime,
    parse_homeway_lecturer_url,
    render_homeway_markdown,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.headers = {}
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.payloads:
            raise AssertionError("unexpected request")
        return FakeResponse(self.payloads.pop(0))


def list_item(*, is_charge=False, image_urls=None):
    return HomewayListItem(
        external_item_id="198488",
        lecturer_id="1669029704",
        lecturer_name="枪大侠",
        published_at=parse_homeway_datetime("2026-08-14 10:09:16"),
        published_at_text="2026-08-14 10:09:16",
        preview_text="【短线】市场观察",
        image_urls=image_urls or [],
        is_charge=is_charge,
        tag_id="66",
        tag_name="实战圈·机会点评",
    )


class HomewaySubscriptionAdapterTest(unittest.TestCase):
    def test_recognizes_only_graphic_lecturer_urls(self):
        self.assertEqual(
            parse_homeway_lecturer_url(
                "https://tyds.homeway.com.cn/#/GraphicLecturer?lecturerId=1669029704"
            ),
            "1669029704",
        )
        with self.assertRaises(HomewaySubscriptionError):
            parse_homeway_lecturer_url(
                "https://tyds.homeway.com.cn/#/GraphicVideo?key=198488"
            )

    def test_previews_lecturer_and_text_menu(self):
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "lecturer": {
                            "id": "1669029704",
                            "name": "枪大侠",
                            "intro": "讲师介绍",
                            "full_avatar_url": "https://tyds-cos.homeway.com.cn/avatar.png",
                        }
                    },
                },
                {
                    "code": 1000,
                    "data": {
                        "lecturersMenu": {
                            "allSubMenu": [
                                {"id": 0, "name": "全部"},
                                {"id": 1, "name": "观点"},
                            ]
                        }
                    },
                },
            ]
        )
        preview = HomewaySubscriptionAdapter(session).preview_subscription(
            "https://tyds.homeway.com.cn/#/GraphicLecturer?lecturerId=1669029704",
            token="secret-token",
        )
        self.assertEqual(preview.display_name, "枪大侠")
        self.assertEqual(preview.text_menu_name, "观点")
        self.assertEqual(session.calls[0][1]["params"]["token"], "secret-token")

    def test_lists_only_atomic_text_items_and_parses_source_time(self):
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "outlook": [
                            {
                                "id": "198488",
                                "data_type": "outlook",
                                "content_type": "lecturer_feed",
                                "lecturer_id": "1669029704",
                                "lecturer_name": "枪大侠",
                                "published_at": "2026-08-14 10:09:16",
                                "real_content": "【短线】市场观察",
                                "get_imgs": [
                                    "https://tyds-cos.homeway.com.cn/article/image.png"
                                ],
                                "is_charge": False,
                                "tag_id": "66",
                                "tag_name": "机会点评",
                            }
                        ],
                        "video": [
                            {
                                "id": "video-1",
                                "data_type": "video",
                                "content_type": "video",
                                "published_at": "2026-08-14 09:00:00",
                            }
                        ],
                    },
                }
            ]
        )
        items = HomewaySubscriptionAdapter(session).list_items(
            "1669029704",
            token="secret-token",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].external_item_id, "198488")
        self.assertEqual(items[0].published_at.tzinfo, timezone.utc)
        self.assertEqual(session.calls[0][1]["params"]["subMenuId"], 1)

    def test_free_item_captures_text_and_image(self):
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "lecturer": {"id": "1669029704", "name": "枪大侠", "is_vip": False},
                        "lecturer_feed": {
                            "id": "198488",
                            "content": '<p>公开正文<img src="https://tyds-cos.homeway.com.cn/article/a.png"></p>',
                            "vip_content": "",
                            "is_blocked": False,
                            "signature": "来源声明",
                            "published_at": "2026-08-14 10:09:16",
                        },
                    },
                }
            ]
        )
        captured = HomewaySubscriptionAdapter(session).capture_item(list_item())
        self.assertEqual(captured.capture_status, "CAPTURED")
        self.assertEqual(captured.access_scope, "public")
        self.assertIn("公开正文", captured.raw_html)
        self.assertEqual(len(captured.image_urls), 1)

    def test_keeps_preview_image_when_detail_html_omits_it(self):
        image_url = "https://tyds-cos.homeway.com.cn/article/preview.png"
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "lecturer": {"id": "1669029704", "name": "枪大侠", "is_vip": False},
                        "lecturer_feed": {
                            "id": "198488",
                            "content": "<p>公开正文</p>",
                            "vip_content": "",
                            "is_blocked": False,
                        },
                    },
                }
            ]
        )
        captured = HomewaySubscriptionAdapter(session).capture_item(
            list_item(image_urls=[image_url])
        )
        self.assertEqual(captured.image_urls, [image_url])
        self.assertIn(image_url, captured.raw_html)

    def test_paid_item_fails_closed_without_positive_membership_permission(self):
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "vipPermissionLecIds": "",
                        "vipNeedSignLecturerIds": "",
                        "vipReSignLecturerIds": "",
                    },
                }
            ]
        )
        captured = HomewaySubscriptionAdapter(session).capture_item(
            list_item(is_charge=True),
            token="secret-token",
        )
        self.assertEqual(captured.capture_status, "LOCKED")
        self.assertEqual(captured.raw_html, "")
        self.assertEqual(len(session.calls), 1)
        self.assertIn("queryUserEvaluationInfo", session.calls[0][0])

    def test_paid_item_uses_vip_content_only_with_positive_entitlement(self):
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "vipPermissionLecIds": "1669029704",
                        "vipNeedSignLecturerIds": "",
                        "vipReSignLecturerIds": "",
                    },
                },
                {
                    "code": 1000,
                    "data": {
                        "lecturer": {"id": "1669029704", "name": "枪大侠", "is_vip": False},
                        "lecturer_feed": {
                            "id": "198488",
                            "content": "<p>公开预览</p>",
                            "vip_content": "<p>已授权全文</p>",
                            "is_blocked": False,
                        },
                    },
                }
            ]
        )
        captured = HomewaySubscriptionAdapter(session).capture_item(
            list_item(is_charge=True),
            token="secret-token",
        )
        self.assertEqual(captured.capture_status, "CAPTURED")
        self.assertEqual(captured.access_scope, "entitled")
        self.assertIn("已授权全文", captured.raw_html)
        self.assertIn("queryUserEvaluationInfo", session.calls[0][0])
        self.assertIn("topicDetail", session.calls[1][0])

    def test_paid_item_stays_locked_while_membership_requires_resign(self):
        session = FakeSession(
            [
                {
                    "code": 1000,
                    "data": {
                        "vipPermissionLecIds": ["1669029704"],
                        "vipNeedSignLecturerIds": "",
                        "vipReSignLecturerIds": "1669029704",
                    },
                }
            ]
        )
        captured = HomewaySubscriptionAdapter(session).capture_item(
            list_item(is_charge=True),
            token="secret-token",
        )
        self.assertEqual(captured.capture_status, "LOCKED")
        self.assertEqual(len(session.calls), 1)

    def test_markdown_rewrites_downloaded_images(self):
        original = "https://tyds-cos.homeway.com.cn/article/a.png"
        markdown = render_homeway_markdown(
            f'<p>正文<img src="{original}"></p>',
            {original: "/task-assets/task/homeway/1/image_01.png"},
        )
        self.assertIn("正文", markdown)
        self.assertIn("/task-assets/task/homeway/1/image_01.png", markdown)


if __name__ == "__main__":
    unittest.main()
