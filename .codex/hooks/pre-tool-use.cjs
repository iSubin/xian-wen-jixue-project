#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { recordHookMetric } = require('./hook-metrics.cjs');
const {
  commandFrom,
  evaluatePreToolUse,
  formatPreToolUseOutput
} = require('../../hooks/pre-tool-use-core.cjs');

const hookStartTime = Date.now();

let input = {};
try {
  const raw = fs.readFileSync(0, 'utf8');
  input = raw ? JSON.parse(raw) : {};
} catch {
  process.stdout.write('{}');
  process.exit(0);
}

const toolName = input.tool_name || '';
const toolInput = input.tool_input || {};
const cwd = input.cwd || process.cwd();
let observedToolCategory = classifyToolCategory(toolName);
let observedSkillReadSignal = null;

if (/^(Bash|Shell|shell)$/i.test(toolName)) {
  const command = commandFrom(toolInput);
  if (isSkillReadCommand(command)) {
    observedToolCategory = 'skill-read';
    observedSkillReadSignal = 'skill-md-read';
  }
}

const decision = evaluatePreToolUse(input, {
  runtime: 'codex',
  hookSource: __filename,
  taskRoot: path.resolve(__dirname, '../..')
});
const output = formatPreToolUseOutput(decision, 'codex');
finish(output, decision.action === 'block' ? 'deny' : decision.action);

function finish(output, mode) {
  recordHookMetric({
    hook: 'PreToolUse',
    hookEventName: 'PreToolUse',
    startTime: hookStartTime,
    cwd,
    sessionId: input.session_id,
    turnId: input.turn_id,
    toolUseId: input.tool_use_id,
    outputBytes: Buffer.byteLength(output || '', 'utf8'),
    outputText: output || '',
    mode,
    selectedSkills: [],
    toolName,
    toolCategory: observedToolCategory,
    permissionDecision: mode,
    skillReadSignal: observedSkillReadSignal
  });
  process.stdout.write(output);
  process.exit(0);
}

function classifyToolCategory(name) {
  if (/^(apply_patch|Edit|Write|MultiEdit)$/i.test(name)) {
    return 'mutation';
  }
  if (/^(Bash|Shell|shell)$/i.test(name)) {
    return 'shell';
  }
  return 'other';
}

function isSkillReadCommand(command) {
  if (typeof command !== 'string' || !/SKILL\.md/.test(command)) {
    return false;
  }
  if (!/(^|\s)(cat|sed|nl|awk|head|tail|less|more|rg|grep)\b/.test(command)) {
    return false;
  }
  return /(?:^|[\s"'`])(?:\.\/)?(?:\.codex|\.claude)\/skills\/[^ \n"'`]+\/SKILL\.md/.test(command)
    || /\/(?:\.codex|\.claude)\/skills\/[^ \n"'`]+\/SKILL\.md/.test(command)
    || /\/skills\/[^ \n"'`]+\/SKILL\.md/.test(command);
}
