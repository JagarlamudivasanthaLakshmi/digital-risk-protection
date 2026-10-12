from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from services.groq_service import (
    GroqServiceError,
    create_chat_completion,
)


class GroqServiceTests(SimpleTestCase):
    @override_settings(GROQ_API_KEY="test-key", GROQ_MODEL="test-model")
    @patch("services.groq_service.requests.post")
    def test_create_chat_completion_sends_request_and_returns_content(self, post):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": '{"summary":"ok"}'}}]}
        post.return_value = response

        result = create_chat_completion([{"role": "user", "content": "evidence"}])

        self.assertEqual(result, '{"summary":"ok"}')
        response.raise_for_status.assert_called_once_with()
        self.assertEqual(post.call_args.kwargs["json"]["model"], "test-model")
        self.assertEqual(post.call_args.kwargs["json"]["messages"][0]["content"], "evidence")
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-key",
        )

    @override_settings(GROQ_API_KEY="")
    def test_create_chat_completion_requires_api_key(self):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY"):
            create_chat_completion([])

    @override_settings(GROQ_API_KEY="test-key")
    @patch("services.groq_service.requests.post")
    def test_create_chat_completion_rejects_missing_message(self, post):
        response = Mock()
        response.json.return_value = {"choices": []}
        post.return_value = response

        with self.assertRaisesRegex(GroqServiceError, "unexpected format"):
            create_chat_completion([])
