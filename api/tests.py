import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from .models import Chapter, MediaAsset, Sentence, Word


def _make_test_image(name="test.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color="red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(
    ALLOWED_HOSTS=["testserver", "satoori-api.protfolio.store"],
)
class MediaAssetApiTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.temp_media_root = tempfile.mkdtemp(prefix="satoori-media-test-")
        self.override = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.override.enable()
        self.user, _ = get_user_model().objects.get_or_create(
            username="master",
            defaults={
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.chapter = Chapter.objects.create(
            owner=self.user,
            title="테스트 챕터",
            difficulty="beginner",
            context_tag="daily",
        )
        self.word = Word.objects.create(
            chapter=self.chapter,
            korean_word="사과",
            north_korean_word="능금",
        )
        self.sentence = Sentence.objects.create(
            chapter=self.chapter,
            korean_sentence="안녕하세요",
            north_korean_sentence="안녕하십니까",
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_media_root, ignore_errors=True)
        super().tearDown()

    def test_media_asset_upload_uses_public_https_origin(self):
        image = _make_test_image()
        response = self.client.post(
            "/api/media-assets/",
            {
                "category": "general",
                "label": "테스트 이미지",
                "key_text": "테스트",
                "image": image,
            },
            format="multipart",
            HTTP_HOST="satoori-api.protfolio.store",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            response.data["image_url"].startswith(
                "https://satoori-api.protfolio.store/api/media-assets/"
            )
        )

        file_response = self.client.get(
            response.data["image_url"].replace("https://satoori-api.protfolio.store", ""),
            HTTP_HOST="satoori-api.protfolio.store",
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response["Content-Type"], "image/png")

    def test_chapter_word_endpoint_includes_image_url(self):
        MediaAsset.objects.create(
            owner=self.user,
            category=MediaAsset.CATEGORY_WORD,
            label="단어 이미지",
            key_text=self.word.korean_word,
            word=self.word,
            chapter=self.chapter,
            image=_make_test_image("word.png"),
        )

        response = self.client.get(
            f"/api/chapters/{self.chapter.id}/words/",
            HTTP_HOST="satoori-api.protfolio.store",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]["image_url"].startswith("https://"))

    def test_chapter_sentence_endpoint_includes_image_url(self):
        MediaAsset.objects.create(
            owner=self.user,
            category=MediaAsset.CATEGORY_SENTENCE,
            label="문장 이미지",
            key_text=self.sentence.korean_sentence,
            sentence=self.sentence,
            chapter=self.chapter,
            image=_make_test_image("sentence.png"),
        )

        response = self.client.get(
            f"/api/chapters/{self.chapter.id}/sentences/",
            HTTP_HOST="satoori-api.protfolio.store",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]["image_url"].startswith("https://"))
