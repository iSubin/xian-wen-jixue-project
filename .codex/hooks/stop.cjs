#!/usr/bin/env node
/**
 * Codex Stop Hook - 单 turn 结束时触发
 *
 * 功能：防御 stop_hook_active re-entry，避免连锁触发。
 *
 * Codex stdin schema：
 *   { session_id, turn_id, stop_hook_active, last_assistant_message, cwd, ... }
 *
 * Codex 输出：
 *   - 必须返回 JSON
 *   - {} → 正常结束
 *   - {decision:"block", reason} → 自动续 turn（不要乱用，会陷入死循环）
 *   - {continue:false} → 强制停止后续处理
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
let recordHookMetric = () => {};
try {
  ({ recordHookMetric } = require('./hook-metrics.cjs'));
} catch {
  // Hook metrics are optional. Stop must remain fail-open during partial uninstall.
}
let isStopReentry = (value) => Boolean(value && value.stop_hook_active);
try {
  ({ isStopReentry } = require('../../hooks/stop-core.cjs'));
} catch {
  // Shared hook helpers are optional. Stop must remain fail-open during partial uninstall.
}
const hookStartTime = Date.now();

let input = {};
try {
  const raw = fs.readFileSync(0, 'utf8');
  if (raw) input = JSON.parse(raw);
} catch {
  // 输入异常时也要正常退出，不能阻塞 Codex
}

// 防御：stop_hook_active 表示已是 hook 触发的 re-entry，直接退出，避免连锁触发
if (isStopReentry(input)) {
  safeRecordStopMetric('reentry');
  process.stdout.write('{}');
  process.exit(0);
}

// Codex 要求 Stop hook 返回 JSON
let stopMode = 'projection-error';
try {
  stopMode = inspectProjectionOnStop(input.cwd || process.cwd());
} catch {
  stopMode = 'projection-error';
}
safeRecordStopMetric(stopMode);
process.stdout.write('{}');
process.exit(0);

function inspectProjectionOnStop(cwd) {
  const projectRoot = findProjectRoot(cwd);
  if (!projectRoot) {
    return 'projection-skip';
  }

  const cli = resolveHarnessCli(projectRoot);
  if (!cli) {
    return 'projection-skip';
  }

  const status = runHarnessCli(cli, ['change', 'projection', 'status', '--target', projectRoot, '--json'], 8000);
  if (status.errorCode === 'ENOENT') {
    return 'projection-skip';
  }
  if (status.code !== 0) {
    return 'projection-error';
  }

  let parsed = null;
  try {
    parsed = JSON.parse(status.stdout || '{}');
  } catch {
    return 'projection-error';
  }

  if (!parsed || projectSurfacePendingCount(parsed) <= 0) {
    return 'projection-idle';
  }

  if (!shouldDrainProjectionOnStop()) {
    return 'projection-pending';
  }

  const drain = runHarnessCli(cli, ['change', 'projection', 'drain', '--target', projectRoot, '--json'], 25000);
  if (drain.errorCode === 'ENOENT') {
    return 'projection-skip';
  }
  return drain.code === 0 ? 'projection-drained' : 'projection-error';
}

function shouldDrainProjectionOnStop() {
  return /^(1|true|yes)$/i.test(process.env.XIAN_STOP_HOOK_DRAIN_PROJECTION || '');
}

function projectSurfacePendingCount(status) {
  const surfaces = Array.isArray(status.surfaces) ? status.surfaces : [];
  return surfaces
    .filter((surface) => surface && surface.surface !== 'manifest-only')
    .reduce((total, surface) => total + Number(surface.pendingEventCount || 0), 0);
}

function findProjectRoot(start) {
  let current = path.resolve(start || process.cwd());
  while (current !== path.dirname(current)) {
    if (fs.existsSync(path.join(current, '.xian-harness'))) {
      return current;
    }
    current = path.dirname(current);
  }
  return null;
}

function resolveHarnessCli(projectRoot) {
  const override = process.env.XIAN_HARNESS_CLI;
  if (override) {
    return { command: process.execPath, baseArgs: [override] };
  }

  const localCli = path.join(projectRoot, 'xian-agent-harness', 'bin', 'xian-harness');
  if (fs.existsSync(localCli)) {
    return { command: process.execPath, baseArgs: [localCli] };
  }

  return null;
}

function runHarnessCli(cli, args, timeout) {
  const result = spawnSync(cli.command, [...cli.baseArgs, ...args], {
    cwd: process.cwd(),
    encoding: 'utf8',
    timeout,
    maxBuffer: 1024 * 1024
  });
  return {
    code: result.status,
    stdout: result.stdout || '',
    errorCode: result.error && result.error.code ? result.error.code : null
  };
}

function recordStopMetric(mode) {
  recordHookMetric({
    hook: 'Stop',
    hookEventName: 'Stop',
    startTime: hookStartTime,
    cwd: input.cwd || process.cwd(),
    sessionId: input.session_id,
    turnId: input.turn_id,
    outputBytes: 2,
    outputText: '{}',
    mode,
    selectedSkills: [],
    toolCategory: 'turn-complete'
  });
}

function safeRecordStopMetric(mode) {
  try {
    recordStopMetric(mode);
  } catch {
    // Stop hooks must not block the agent session because observability failed.
  }
}
