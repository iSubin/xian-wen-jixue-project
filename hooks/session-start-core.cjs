const fs = require('fs');
const path = require('path');

function runSessionStartHook(options = {}) {
  const runtime = options.runtime === 'claude' ? 'claude' : 'codex';
  const recordHookMetric = typeof options.recordHookMetric === 'function'
    ? options.recordHookMetric
    : () => {};
  const hookStartTime = Date.now();
  let input = {};

  try {
    const raw = fs.readFileSync(0, 'utf8');
    input = raw ? JSON.parse(raw) : {};
  } catch {
    process.stdout.write('{}');
    process.exit(0);
  }

  const source = input.source || '';
  const cwd = input.cwd || process.cwd();
  const finish = (output, mode) => {
    recordHookMetric({
      hook: 'SessionStart',
      startTime: hookStartTime,
      cwd,
      outputBytes: Buffer.byteLength(output || '', 'utf8'),
      mode,
      selectedSkills: []
    });
    process.stdout.write(output);
    process.exit(0);
  };

  if (source && source !== 'startup') {
    finish('{}', 'skipped');
  }

  const projectRoot = findProjectRoot(cwd) || cwd;
  const manifest = readBootstrapManifest(projectRoot);
  const maxBytes = Number.isInteger(manifest.maxBytes) && manifest.maxBytes > 0 ? manifest.maxBytes : 8192;
  const sourceConfigs = Array.isArray(manifest.sources) ? manifest.sources : [];
  const sourceBudget = perSourceContentBudget(maxBytes, sourceConfigs.length);
  const sections = [];

  for (const sourceConfig of sourceConfigs) {
    const sourceSection = loadSource(projectRoot, sourceConfig, sourceBudget);
    if (sourceSection) {
      sections.push(sourceSection);
    }
  }

  if (sections.length === 0) {
    finish('{}', 'empty');
  }

  const wrapped = [
    `## xian Harness Bootstrap Context (${manifest.profile || 'unknown'})`,
    '',
    '> The following context is loaded from `.xian-harness/bootstrap-context.json`.',
    '> Hooks read the manifest; profiles own the source list.',
    '',
    ...sections
  ].join('\n');
  const boundedContext = truncateUtf8(wrapped, maxBytes, '\n\n...(truncated; read the source files for full context)');

  finish(formatSessionStartOutput(runtime, boundedContext), 'startup');
}

function readBootstrapManifest(projectRoot) {
  const contextPath = path.join(projectRoot, '.xian-harness', 'bootstrap-context.json');
  return readJson(contextPath) || {
    version: 1,
    profile: 'fallback',
    maxBytes: 8192,
    sources: [
      { label: 'Xian Harness Project Context', path: 'AGENTS.md', kind: 'markdown', required: false },
      { label: 'Xian Harness State', path: '.xian-harness/state.yaml', kind: 'text', required: false }
    ]
  };
}

function formatSessionStartOutput(runtime, boundedContext) {
  if (runtime === 'claude') {
    return JSON.stringify({ additionalContext: boundedContext });
  }
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: boundedContext
    }
  });
}

function loadSource(root, sourceConfig, maxBytes) {
  if (!sourceConfig || typeof sourceConfig !== 'object') {
    return null;
  }

  const label = String(sourceConfig.label || sourceConfig.path || 'Bootstrap Source');
  const relativePath = String(sourceConfig.path || '');
  if (!relativePath || path.isAbsolute(relativePath)) {
    return null;
  }

  const kind = String(sourceConfig.kind || 'text');
  const absolutePath = path.join(root, relativePath);
  let filePath = absolutePath;

  if (kind === 'state-summary') {
    return loadStateSummary(root, label);
  }

  if (kind === 'latest-exp-summary') {
    filePath = findLatestExperienceSummary(absolutePath);
    if (!filePath) {
      return null;
    }
  }

  if (!exists(filePath)) {
    return null;
  }

  let content = '';
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch {
    return null;
  }

  content = truncateUtf8(content, maxBytes, '\n\n...(truncated; read the source file for full context)');

  const sourcePath = path.relative(root, filePath).replace(/\\/g, '/');
  return [`### ${label}`, '', `Source: \`${sourcePath}\``, '', content, ''].join('\n');
}

function loadStateSummary(root, label) {
  const stateYamlPath = path.join(root, '.xian-harness', 'state.yaml');
  if (!exists(stateYamlPath)) {
    return null;
  }

  let stateContent = '';
  try {
    stateContent = fs.readFileSync(stateYamlPath, 'utf8');
  } catch {
    return null;
  }

  const activeChangeMatch = stateContent.match(/^activeChange:\s*(\S+)\s*$/m);
  const activeChange = activeChangeMatch ? activeChangeMatch[1] : null;
  if (
    !activeChange
    || activeChange === 'null'
    || !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(activeChange)
  ) {
    return null;
  }

  const changeDir = path.join(root, '.xian-harness', 'changes', activeChange);
  const changeStatePath = path.join(changeDir, '.change-state.json');
  const changeState = readJson(changeStatePath);
  const phase = changeState && typeof changeState.phase === 'string'
    ? changeState.phase
    : null;
  if (!phase || !new Set(['open', 'spec', 'plan', 'build', 'verify', 'archived']).has(phase)) {
    return null;
  }

  const lines = [
    `### ${label}`,
    '',
    `当前 Change：${activeChange}`,
    `当前阶段：${phase}`,
    '',
    '方向：`xian-harness continue` 是唯一的下一步方向来源。'
  ];
  lines.push('');

  return lines.join('\n');
}

function perSourceContentBudget(maxBytes, sourceCount) {
  if (sourceCount <= 0) {
    return maxBytes;
  }
  return Math.max(Math.floor(maxBytes / sourceCount) - 320, 96);
}

function truncateUtf8(value, maxBytes, suffix = '') {
  const limit = Math.max(Math.floor(Number(maxBytes)), 0);
  if (Buffer.byteLength(value, 'utf8') <= limit) {
    return value;
  }
  if (limit === 0) {
    return '';
  }

  const suffixBytes = Buffer.byteLength(suffix, 'utf8');
  if (suffixBytes >= limit) {
    return sliceUtf8(suffix, limit);
  }

  return `${sliceUtf8(value, limit - suffixBytes)}${suffix}`;
}

function sliceUtf8(value, maxBytes) {
  let low = 0;
  let high = value.length;
  while (low < high) {
    const mid = Math.ceil((low + high) / 2);
    if (Buffer.byteLength(value.slice(0, mid), 'utf8') <= maxBytes) {
      low = mid;
    } else {
      high = mid - 1;
    }
  }
  return value.slice(0, low).replace(/[\uD800-\uDBFF]$/, '');
}

function findLatestExperienceSummary(expDir) {
  try {
    const dateDirs = fs.readdirSync(expDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort()
      .reverse();

    for (const dirName of dateDirs) {
      const dir = path.join(expDir, dirName);
      const files = fs.readdirSync(dir)
        .filter((file) => file.endsWith('-exp-summary.md'))
        .sort()
        .reverse();
      if (files.length > 0) {
        return path.join(dir, files[0]);
      }
    }
  } catch {
    return null;
  }

  return null;
}

function findProjectRoot(startDir) {
  let current = path.resolve(startDir || process.cwd());
  while (true) {
    if (exists(path.join(current, '.xian-harness')) || exists(path.join(current, '.git'))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function exists(filePath) {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

module.exports = {
  runSessionStartHook,
  formatSessionStartOutput,
  loadSource,
  loadStateSummary,
  truncateUtf8
};
