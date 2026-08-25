import unittest

from fastapi import HTTPException

from src.main.python.xianwen import api as api_module


class CollectionPreviewTest(unittest.TestCase):
    def test_xiaoet_lesson_urls_are_recognized_as_one_batch(self):
        source = "\n".join(
            [
                "https://appexpqpqic7617.h5.xet.pomoho.com/p/course/video/v_lesson_1?product_id=p_course",
                "https://appexpqpqic7617.h5.xet.pomoho.com/p/course/video/v_lesson_2?product_id=p_course",
            ]
        )

        preview = api_module._build_url_list_collection_preview(source)

        self.assertEqual(preview["provider"], "xiaoetong")
        self.assertEqual(preview["source_type"], "xiaoet_video_list")
        self.assertEqual(preview["title"], "小鹅通课程合集（2 节）")
        self.assertEqual(preview["total_items"], 2)
        self.assertTrue(all(item["provider"] == "xiaoetong" for item in preview["items"]))

    def test_xiaoet_course_page_is_not_silently_submitted_as_a_video(self):
        source = "https://appexpqpqic7617.h5.xiaoeknow.com/p/course/column/p_course"

        with self.assertRaises(HTTPException) as context:
            api_module._build_url_list_collection_preview(source)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("课程或专栏主页", str(context.exception.detail))
        self.assertIn("具体视频课时链接", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
