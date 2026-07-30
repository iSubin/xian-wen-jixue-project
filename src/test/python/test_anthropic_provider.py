import os
import sys
import unittest


path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, path)

from src.main.python.xianwen.config.settings import _BUILTIN_PROVIDER_DEFAULTS
from src.main.python.xianwen.llm.llm import LLMConfig
from src.main.python.xianwen.llm.litellm_client import LiteLLMClient
from src.main.python.xianwen.llm.provider_manager import LLMProviderManager


class TestAnthropicProvider(unittest.TestCase):
    def test_provider_defaults_include_anthropic(self):
        self.assertIn("anthropic", _BUILTIN_PROVIDER_DEFAULTS)
        self.assertEqual(_BUILTIN_PROVIDER_DEFAULTS["anthropic"]["base_url"], "https://api.anthropic.com")

    def test_provider_manager_lists_anthropic(self):
        manager = LLMProviderManager(
            LLMConfig(
                provider="openai_compatible",
                base_url="https://api.openai.com/v1",
                api_key="",
                model_id="gpt-4o-mini",
            )
        )

        provider_ids = {provider["id"] for provider in manager.list_providers()}

        self.assertIn("anthropic", provider_ids)

    def test_litellm_client_routes_anthropic_provider(self):
        client = LiteLLMClient(
            LLMConfig(
                provider="anthropic",
                base_url="http://example.test",
                api_key="test-key",
                model_id="claude-opus-4-7",
            )
        )

        self.assertEqual(client._custom_llm_provider(), "anthropic")
        self.assertEqual(client._model_candidates(), ["claude-opus-4-7"])


if __name__ == "__main__":
    unittest.main()
