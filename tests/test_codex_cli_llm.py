from __future__ import annotations

import asyncio
import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from src.main.python.xianwen.llm.codex_cli_client import CodexCliClient
from src.main.python.xianwen.llm.llm import (
    LLMConfig,
    LLMConnectionError,
    LLMMessage,
    LLMResponseError,
    get_llm,
)
from src.main.python.xianwen.llm.litellm_client import LiteLLMClient
from src.main.python.xianwen.llm.provider_manager import LLMProviderManager
from src.main.python.xianwen.config.settings import JSONConfigManager


class CodexCliClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="xianwen-codex-test-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_cli(self, actual_body: str, *, login_exit: int = 0) -> Path:
        path = self.root / f"fake-codex-{len(list(self.root.glob('fake-codex-*')))}"
        body = f"""#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import time

args = sys.argv[1:]
if args == ['--help']:
    print('--sandbox')
    raise SystemExit(0)
if args == ['exec', '--help']:
    print('--ignore-user-config --ignore-rules --ephemeral --json --output-last-message --skip-git-repo-check')
    raise SystemExit(0)
if args == ['login', 'status']:
    print('Logged in using ChatGPT')
    raise SystemExit({login_exit})
{textwrap.dedent(actual_body)}
"""
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        return path

    async def test_response_uses_bounded_read_only_ephemeral_invocation(self):
        cli = self._make_cli(
            """
            prompt = sys.stdin.read()
            result_path = pathlib.Path(args[args.index('--output-last-message') + 1])
            result_path.write_text('# 已整理\\n\\n内容', encoding='utf-8')
            print(json.dumps({'type': 'thread.started', 'thread_id': 'thread-test'}))
            print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 5}}))
            """
        )
        config = LLMConfig(
            provider="codex_cli",
            cli_path=str(cli),
            model_id="gpt-test",
            reasoning_effort="high",
            cli_timeout_sec=10,
        )
        client = CodexCliClient(config)
        args = client._build_args(str(cli), self.root / "result.md")

        self.assertEqual(args[:4], [str(cli), "--sandbox", "read-only", "exec"])
        self.assertIn("--ignore-user-config", args)
        self.assertIn("--ignore-rules", args)
        self.assertIn("--ephemeral", args)
        self.assertIn("--skip-git-repo-check", args)
        self.assertIn("--json", args)
        self.assertIn("--output-last-message", args)
        self.assertIn("gpt-test", args)
        self.assertIn('model_reasoning_effort="high"', args)
        self.assertEqual(args[-1], "-")

        results: list[object] = []
        await client.response(
            [LLMMessage(role="system", content="整理内容"), LLMMessage(role="user", content="原始逐字稿")],
            results.append,
            stream=True,
        )
        self.assertEqual(results, ["# 已整理\n\n内容"])

    async def test_preflight_reports_missing_executable(self):
        client = CodexCliClient(
            LLMConfig(provider="codex_cli", cli_path=str(self.root / "missing-codex"))
        )
        with self.assertRaisesRegex(LLMConnectionError, "不可执行"):
            await client.preflight()

    async def test_preflight_reports_login_required_without_model_call(self):
        cli = self._make_cli("raise AssertionError('model call must not run')", login_exit=1)
        client = CodexCliClient(LLMConfig(provider="codex_cli", cli_path=str(cli)))
        with self.assertRaisesRegex(LLMConnectionError, "codex login"):
            await client.preflight(force=True)

    async def test_nonzero_exit_is_reported_as_response_error(self):
        cli = self._make_cli(
            """
            print(json.dumps({'type': 'turn.failed'}))
            print('simulated failure', file=sys.stderr)
            raise SystemExit(7)
            """
        )
        client = CodexCliClient(
            LLMConfig(provider="codex_cli", cli_path=str(cli), cli_timeout_sec=10)
        )
        results: list[object] = []
        await client.response([LLMMessage(role="user", content="内容")], results.append)

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], LLMResponseError)
        self.assertIn("exit 7", str(results[0]))
        self.assertIn("simulated failure", str(results[0]))

    async def test_output_limit_terminates_process(self):
        cli = self._make_cli("print('x' * 8192)")
        client = CodexCliClient(
            LLMConfig(provider="codex_cli", cli_path=str(cli)),
            output_limit_bytes=2048,
            terminate_grace_sec=0.1,
        )
        with self.assertRaisesRegex(LLMResponseError, "输出超过"):
            await client._execute([str(cli)], "input", self.root, timeout=2)

    async def test_timeout_terminates_process_group(self):
        pid_path = self.root / "timeout.pid"
        cli = self._make_cli(
            f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8')\n"
            "time.sleep(30)"
        )
        client = CodexCliClient(
            LLMConfig(provider="codex_cli", cli_path=str(cli)),
            terminate_grace_sec=0.1,
        )
        with self.assertRaisesRegex(LLMResponseError, "分析超时"):
            await client._execute([str(cli)], "input", self.root, timeout=2)
        pid = int(pid_path.read_text(encoding="utf-8"))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    async def test_cancellation_terminates_process_group(self):
        pid_path = self.root / "cancel.pid"
        cli = self._make_cli(
            f"""
            pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8')
            time.sleep(30)
            """
        )
        client = CodexCliClient(
            LLMConfig(provider="codex_cli", cli_path=str(cli)),
            terminate_grace_sec=0.1,
        )
        task = asyncio.create_task(client._execute([str(cli)], "input", self.root, timeout=30))
        for _ in range(100):
            if pid_path.exists():
                break
            await asyncio.sleep(0.01)
        self.assertTrue(pid_path.exists())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        pid = int(pid_path.read_text(encoding="utf-8"))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_environment_does_not_forward_application_secrets(self):
        with patch.dict(
            os.environ,
            {"XIANWEN_SECRET": "do-not-forward", "OPENAI_API_KEY": "do-not-forward", "PATH": "/bin"},
            clear=True,
        ):
            env = CodexCliClient._sanitized_environment()
        self.assertEqual(env["PATH"], "/bin")
        self.assertNotIn("XIANWEN_SECRET", env)
        self.assertNotIn("OPENAI_API_KEY", env)


class CodexCliProviderManagerTest(unittest.TestCase):
    def test_factory_and_profile_switch_replace_client_type(self):
        lite_config = LLMConfig(
            provider="deepseek",
            base_url="https://api.deepseek.com",
            api_key="secret",
            model_id="deepseek-chat",
        )
        self.assertIsInstance(get_llm(lite_config), LiteLLMClient)
        self.assertIsInstance(get_llm(LLMConfig(provider="codex_cli")), CodexCliClient)

        manager = LLMProviderManager(lite_config, initial_provider_id="deepseek")

        class Worker:
            def __init__(self):
                self._llm_client = None

            def update_llm_client(self, client):
                self._llm_client = client

        worker = Worker()
        manager.bind_llm_worker(worker)
        self.assertIsInstance(worker._llm_client, LiteLLMClient)

        settings = manager.add_profile(
            name="本机 Codex",
            provider="codex_cli",
            cli_path="/opt/homebrew/bin/codex",
            reasoning_effort="high",
            cli_timeout_sec=600,
        )
        self.assertIsInstance(worker._llm_client, CodexCliClient)
        profile = next(item for item in settings["profiles"] if item["provider"] == "codex_cli")
        self.assertFalse(profile["has_api_key"])
        self.assertEqual(profile["cli_path"], "/opt/homebrew/bin/codex")
        self.assertEqual(profile["reasoning_effort"], "high")
        self.assertEqual(profile["cli_timeout_sec"], 600)

    def test_codex_profile_fields_round_trip_through_json_settings(self):
        with tempfile.TemporaryDirectory(prefix="xianwen-settings-test-") as temp_dir:
            config_path = Path(temp_dir) / "settings.json"
            manager = JSONConfigManager(str(config_path))
            profile_id = manager.add_profile(
                "本机 Codex",
                "codex_cli",
                {
                    "cli_path": "/opt/homebrew/bin/codex",
                    "reasoning_effort": "xhigh",
                    "cli_timeout_sec": 1200,
                },
            )
            reloaded = JSONConfigManager(str(config_path)).get_llm_profiles_config()
            profile = next(item for item in reloaded.profiles if item.id == profile_id)

        self.assertEqual(profile.provider, "codex_cli")
        self.assertEqual(profile.base_url, "")
        self.assertEqual(profile.api_key, "")
        self.assertEqual(profile.cli_path, "/opt/homebrew/bin/codex")
        self.assertEqual(profile.reasoning_effort, "xhigh")
        self.assertEqual(profile.cli_timeout_sec, 1200)


if __name__ == "__main__":
    unittest.main()
