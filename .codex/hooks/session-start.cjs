#!/usr/bin/env node
// Codex SessionStart Hook adapter. Shared logic lives in ../../hooks/session-start-core.cjs.

const { recordHookMetric } = require('./hook-metrics.cjs');
const { runSessionStartHook } = require('../../hooks/session-start-core.cjs');

runSessionStartHook({
  runtime: 'codex',
  recordHookMetric
});
