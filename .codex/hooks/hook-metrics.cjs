const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MAX_METRICS_BYTES = 1024 * 1024;
const MAX_ROTATED_METRICS_FILES = 3;
const DEFAULT_HOOK_OBSERVABILITY = {
  enabled: true,
  sampleRate: 1,
  metrics: true,
  decisions: true
};
const policyCache = new Map();

function recordHookMetric(event) {
  try {
    const cwd = event.cwd || process.cwd();
    const root = findHarnessRoot(cwd);
    if (!root) {
      return;
    }
    if (!shouldRecordHookObservation(root, 'metrics')) {
      return;
    }

    const metricsDir = path.join(root, '.xian-harness', 'runtime');
    fs.mkdirSync(metricsDir, { recursive: true });
    const metricsPath = path.join(metricsDir, 'hook-metrics.jsonl');
    rotateIfNeeded(metricsPath);

    const line = JSON.stringify({
      schema_version: 2,
      timestamp: new Date().toISOString(),
      hook: String(event.hook || 'unknown'),
      hook_event_name: stringOrNull(event.hookEventName) || String(event.hook || 'unknown'),
      session_id: stringOrNull(event.sessionId),
      turn_id: stringOrNull(event.turnId),
      tool_use_id: stringOrNull(event.toolUseId),
      prompt_digest: promptDigest(event.prompt),
      duration_ms: Math.max(0, Date.now() - Number(event.startTime || Date.now())),
      output_bytes: Math.max(0, Number(event.outputBytes || 0)),
      output_lines: outputLineCount(event),
      mode: event.mode || null,
      selected_skills: stringArray(event.selectedSkills),
      context_injected: booleanOrNull(event.contextInjected),
      tool_name: stringOrNull(event.toolName),
      tool_category: stringOrNull(event.toolCategory),
      permission_decision: stringOrNull(event.permissionDecision),
      skill_read_signal: stringOrNull(event.skillReadSignal),
      context_digest: normalizeContextDigest(event.contextDigest),
      cwd_depth: cwdDepth(root, cwd)
    });
    fs.appendFileSync(metricsPath, `${line}\n`, 'utf8');
  } catch {
    // Metrics must never block hook execution.
  }
}

function recordHookDecision(event) {
  try {
    const cwd = event.cwd || process.cwd();
    const root = findHarnessRoot(cwd);
    if (!root) {
      return;
    }
    if (!shouldRecordHookObservation(root, 'decisions')) {
      return;
    }

    const metricsDir = path.join(root, '.xian-harness', 'runtime');
    fs.mkdirSync(metricsDir, { recursive: true });
    const decisionsPath = path.join(metricsDir, 'hook-decisions.jsonl');
    rotateIfNeeded(decisionsPath);

    const line = JSON.stringify({
      schema_version: 2,
      timestamp: new Date().toISOString(),
      hook: String(event.hook || 'unknown'),
      hook_event_name: stringOrNull(event.hookEventName) || String(event.hook || 'unknown'),
      session_id: stringOrNull(event.sessionId),
      turn_id: stringOrNull(event.turnId),
      tool_use_id: stringOrNull(event.toolUseId),
      prompt_digest: promptDigest(event.prompt),
      duration_ms: Math.max(0, Date.now() - Number(event.startTime || Date.now())),
      output_bytes: Math.max(0, Number(event.outputBytes || 0)),
      output_lines: outputLineCount(event),
      mode: event.mode || null,
      reason_codes: stringArray(event.reasonCodes),
      matched_terms: normalizeMatchedTerms(event.matchedTerms),
      traits: normalizeTraits(event.traits),
      selected_skills: stringArray(event.selectedSkills),
      required_skills: stringArray(event.requiredSkills),
      context_injected: booleanOrNull(event.contextInjected),
      context_digest: normalizeContextDigest(event.contextDigest),
      cwd_depth: cwdDepth(root, cwd)
    });
    fs.appendFileSync(decisionsPath, `${line}\n`, 'utf8');
  } catch {
    // Decision logs must never block hook execution.
  }
}

function findHarnessRoot(startDir) {
  let current = path.resolve(startDir || process.cwd());
  while (true) {
    if (exists(path.join(current, '.xian-harness'))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

function cwdDepth(root, cwd) {
  const relative = path.relative(root, path.resolve(cwd || root));
  if (!relative || relative === '.') {
    return 0;
  }
  return relative.split(path.sep).filter(Boolean).length;
}

function rotateIfNeeded(filePath) {
  try {
    const stats = fs.statSync(filePath);
    if (stats.size > MAX_METRICS_BYTES) {
      rotateExistingFiles(filePath);
      fs.renameSync(filePath, rotatedPath(filePath, 1));
    }
  } catch {
    // Missing or unrotatable metrics files are fine.
  }
}

function rotateExistingFiles(filePath) {
  for (let index = MAX_ROTATED_METRICS_FILES; index >= 1; index -= 1) {
    const current = rotatedPath(filePath, index);
    const next = rotatedPath(filePath, index + 1);
    try {
      if (index === MAX_ROTATED_METRICS_FILES) {
        fs.rmSync(current, { force: true });
      } else if (fs.existsSync(current)) {
        fs.renameSync(current, next);
      }
    } catch {
      // Rotation is best effort; metrics must never block hook execution.
    }
  }
}

function rotatedPath(filePath, index) {
  return `${filePath}.${index}`;
}

function exists(filePath) {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function shouldRecordHookObservation(root, kind) {
  const policy = readHookObservabilityPolicy(root);
  if (!policy.enabled) {
    return false;
  }
  if (kind === 'metrics' && !policy.metrics) {
    return false;
  }
  if (kind === 'decisions' && !policy.decisions) {
    return false;
  }
  if (policy.sampleRate <= 0) {
    return false;
  }
  if (policy.sampleRate >= 1) {
    return true;
  }
  return Math.random() < policy.sampleRate;
}

function readHookObservabilityPolicy(root) {
  const cacheKey = path.resolve(root);
  const cached = policyCache.get(cacheKey);
  if (cached) {
    return cached;
  }
  const policy = { ...DEFAULT_HOOK_OBSERVABILITY };
  try {
    const policyPath = path.join(root, '.xian-harness', 'interaction-policy.json');
    const parsed = JSON.parse(fs.readFileSync(policyPath, 'utf8'));
    const value = parsed && typeof parsed === 'object' ? parsed.hookObservability : null;
    if (value && typeof value === 'object') {
      if (typeof value.enabled === 'boolean') {
        policy.enabled = value.enabled;
      }
      if (typeof value.metrics === 'boolean') {
        policy.metrics = value.metrics;
      }
      if (typeof value.decisions === 'boolean') {
        policy.decisions = value.decisions;
      }
      policy.sampleRate = normalizeSampleRate(value.sampleRate, policy.sampleRate);
    }
  } catch {
    // Missing or malformed policy falls back to current always-on behavior.
  }

  const envEnabled = String(process.env.XIAN_HOOK_OBSERVABILITY || '').trim().toLowerCase();
  if (['0', 'false', 'off', 'disabled', 'no'].includes(envEnabled)) {
    policy.enabled = false;
  } else if (['1', 'true', 'on', 'enabled', 'yes'].includes(envEnabled)) {
    policy.enabled = true;
  }
  policy.sampleRate = normalizeSampleRate(process.env.XIAN_HOOK_OBSERVABILITY_SAMPLE_RATE, policy.sampleRate);

  policyCache.set(cacheKey, policy);
  return policy;
}

function normalizeSampleRate(value, fallback) {
  const number = typeof value === 'number' ? value : Number.parseFloat(String(value));
  if (!Number.isFinite(number)) {
    return fallback;
  }
  return Math.max(0, Math.min(1, number));
}

function stringArray(value) {
  return Array.isArray(value)
    ? value.filter((item) => typeof item === 'string' && item.length > 0)
    : [];
}

function stringOrNull(value) {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function booleanOrNull(value) {
  return typeof value === 'boolean' ? value : null;
}

function promptDigest(value) {
  if (typeof value !== 'string' || value.length === 0) {
    return null;
  }
  return crypto.createHash('sha256').update(value).digest('hex');
}

function outputLineCount(event) {
  if (Number.isFinite(event.outputLines)) {
    return Math.max(0, Number(event.outputLines));
  }
  if (typeof event.outputText !== 'string' || event.outputText.length === 0) {
    return 0;
  }
  return event.outputText.split(/\r?\n/).filter((line) => line.length > 0).length;
}

function normalizeMatchedTerms(value) {
  if (!value || typeof value !== 'object') {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value)
      .filter(([, terms]) => Array.isArray(terms))
      .map(([key, terms]) => [key, stringArray(terms).slice(0, 12)])
  );
}

function normalizeTraits(value) {
  if (!value || typeof value !== 'object') {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value)
      .filter(([, trait]) => typeof trait === 'boolean')
      .map(([key, trait]) => [key, trait])
  );
}

function normalizeContextDigest(value) {
  if (!value || typeof value !== 'object') {
    return null;
  }
  return {
    version: Number(value.version) || 1,
    injection_level: typeof value.injectionLevel === 'string' ? value.injectionLevel : null,
    delta_from_previous: Boolean(value.deltaFromPrevious),
    policy_hash_changed: Boolean(value.policyHashChanged),
    skill_registry_hash_changed: Boolean(value.skillRegistryHashChanged),
    required_skills_changed: Boolean(value.requiredSkillsChanged),
    forbidden_policy_hash_changed: Boolean(value.forbiddenPolicyHashChanged),
    scope_changed: Boolean(value.scopeChanged),
    receipt_expired: Boolean(value.receiptExpired),
    delta_policy: typeof value.deltaPolicy === 'string' ? value.deltaPolicy : null,
    receipt_age_minutes: typeof value.receiptAgeMinutes === 'number' ? value.receiptAgeMinutes : null,
    profile: typeof value.profile === 'string' ? value.profile : null,
    agent_runtime: typeof value.agentRuntime === 'string' ? value.agentRuntime : null,
    full_facts_available: Boolean(value.fullFactsAvailable),
    reason: typeof value.reason === 'string' ? value.reason : null
  };
}

module.exports = {
  recordHookDecision,
  recordHookMetric
};
