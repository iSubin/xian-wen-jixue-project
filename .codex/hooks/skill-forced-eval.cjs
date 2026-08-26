#!/usr/bin/env node
// Codex UserPromptSubmit Hook - registry-driven skill activation.

const fs = require('fs');
const path = require('path');
const { recordHookDecision, recordHookMetric } = require('./hook-metrics.cjs');
const {
  classifyInteractionMode,
  classifyPromptMatches,
  createRoutingDecision,
  hasXianContextTokens,
  skipPatterns,
  traitsFromMatches
} = require('./hook-routing.cjs');
const {
  matchedRegistryTermsForSkills,
  maxSelectedSkills,
  selectFallbackSkills,
  selectRegistrySkills
} = require('./hook-skill-selection.cjs');
const {
  DEFAULT_INTERACTION_POLICY,
  appendSkillSections,
  buildInteractionOutputContract,
  formatSkillReadInstruction,
  limitHookOutput,
  mergeInteractionPolicy,
  requiredSkillsForMode,
  visibilityForMode
} = require('./hook-output.cjs');

const hookStartTime = Date.now();
let selectedMetricSkills = [];
let requiredMetricSkills = [];
let routingDecision = null;
let interactionMode = null;

let input = {};
try {
  const raw = fs.readFileSync(0, 'utf8');
  input = raw ? JSON.parse(raw) : {};
} catch {
  process.exit(0);
}

const prompt = String(input.prompt || '').trim();
const cwd = input.cwd || process.cwd();
if (!prompt) {
  finish('');
}

const promptLower = prompt.toLowerCase();
const promptForMatching = prompt.replace(/xian-agent-harness/gi, 'xian harness');
const promptMatches = classifyPromptMatches(prompt);
const promptTraits = traitsFromMatches(promptMatches);

if (skipPatterns.some((item) => promptLower.includes(item.toLowerCase()))) {
  finish('', { mode: 'skipped' });
}

interactionMode = classifyInteractionMode(prompt, promptTraits);
routingDecision = createRoutingDecision(interactionMode, prompt, promptTraits, promptMatches);
if (interactionMode === 'chat') {
  finish('', { mode: interactionMode });
}

const explicitXianPrompt = /xian|harness|agent|change|gate|workbench|验收|门禁|看板|需求|计划|验证/.test(promptLower);
const reservedAssetPath = isPathInside(cwd, 'xian-agent-harness/harness-pack');

if (reservedAssetPath && !explicitXianPrompt) {
  finish('', { mode: interactionMode });
}

const firstToken = prompt.split(/\s/)[0] || '';
if (/^\/[^/\s]+$/.test(firstToken)) {
  finish('', { mode: interactionMode });
}

const projectRoot = findProjectRoot(cwd) || cwd;
const interactionPolicy = readInteractionPolicy(projectRoot);

if (interactionPolicy.enabled === false) {
  finish('', { mode: 'disabled' });
}

const installedSkillNames = listSkillNames(projectRoot);
const installedSkills = new Set(installedSkillNames);
const registry = readRegistry(projectRoot);
const registryEntryByName = new Map(
  registry.entries
    .filter((entry) => entry && typeof entry.name === 'string')
    .map((entry) => [entry.name, entry])
);
const maxSkills = maxSelectedSkills(interactionMode, process.env.XIAN_SKILL_HOOK_MAX);
const selected = registry.entries.length > 0
  ? selectRegistrySkills(registry.entries, installedSkills, {
    explicitXianPrompt,
    prompt: promptForMatching,
    contextHasXianTokens: hasXianContextTokens(promptLower),
    maxSkills
  })
  : selectFallbackSkills(installedSkillNames, {
    explicitXianPrompt,
    reservedAssetPath,
    prompt: promptForMatching,
    maxSkills
  });

selectedMetricSkills = selected;
if (selected.length > 0) {
  addRoutingReason('registry-match');
  routingDecision.matchedTerms.registry = matchedRegistryTermsForSkills(selected, registryEntryByName, promptForMatching);
} else if (interactionMode !== 'chat') {
  addRoutingReason('no-skill-selection');
}

const shouldInject = selected.length > 0 && (!reservedAssetPath || explicitXianPrompt);

if (!shouldInject) {
  finish('', { mode: interactionMode, selectedSkills: selectedMetricSkills });
}

const visibleSkillNames = selected;
const requiredSkillNames = requiredSkillsForMode(interactionMode, visibleSkillNames);
requiredMetricSkills = Array.from(requiredSkillNames);
const visibilityOverride = process.env.XIAN_VISIBILITY;
const visibility = visibilityForMode(interactionMode, visibilityOverride);
const outputContract = buildInteractionOutputContract({
  mode: interactionMode,
  policy: interactionPolicy,
  projectRoot,
  traits: promptTraits,
  selectedSkillNames: visibleSkillNames,
  requiredSkillNames: requiredMetricSkills,
  overrideVisibility: visibilityOverride
});
const sections = [];

if (visibilityOverride === 'full') {
  sections.push('展示级别：full（用户显式要求完整显性化）');
}

appendSkillSections(sections, interactionMode, 'Xian', visibleSkillNames, requiredSkillNames, registryEntryByName, projectRoot);

const skillReadInstruction = formatSkillReadInstruction(interactionMode);
if (skillReadInstruction) {
  sections.push(skillReadInstruction);
}

writeAdditionalContext(limitHookOutput(sections.join('\n'), interactionPolicy));

function readRegistry(root) {
  const registryPath = path.join(root, '.xian-harness', 'skill-registry.json');
  try {
    const value = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
    return {
      profile: typeof value.profile === 'string' ? value.profile : 'unknown',
      entries: Array.isArray(value.entries) ? value.entries : []
    };
  } catch {
    return {
      profile: 'missing',
      entries: []
    };
  }
}

function readInteractionPolicy(root) {
  const policyPath = path.join(root, '.xian-harness', 'interaction-policy.json');
  try {
    return mergeInteractionPolicy(JSON.parse(fs.readFileSync(policyPath, 'utf8')));
  } catch {
    return DEFAULT_INTERACTION_POLICY;
  }
}

function findProjectRoot(startDir) {
  let current = path.resolve(startDir || process.cwd());

  while (true) {
    if (
      exists(path.join(current, 'pom.xml'))
      || exists(path.join(current, '.xian-harness'))
      || exists(path.join(current, '.git'))
    ) {
      return current;
    }

    const parent = path.dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

function listSkillNames(root) {
  const skillsRoot = path.join(root, '.codex', 'skills');
  try {
    return fs.readdirSync(skillsRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .filter((entry) => exists(path.join(skillsRoot, entry.name, 'SKILL.md')))
      .map((entry) => entry.name)
      .sort();
  } catch {
    return [];
  }
}

function exists(filePath) {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function isPathInside(filePath, pathPart) {
  const normalized = path.resolve(filePath).split(path.sep).join('/');
  return normalized.includes(`/${pathPart}/`) || normalized.endsWith(`/${pathPart}`);
}

function addRoutingReason(code) {
  if (routingDecision && !routingDecision.reasonCodes.includes(code)) {
    routingDecision.reasonCodes.push(code);
  }
}

function writeAdditionalContext(additionalContext) {
  const output = JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext
    }
  });
  finish(output, { mode: interactionMode, selectedSkills: selectedMetricSkills });
}

function finish(output, metric = {}) {
  const text = output || '';
  const outputBytes = Buffer.byteLength(text, 'utf8');
  recordHookMetric({
    hook: 'UserPromptSubmit',
    hookEventName: 'UserPromptSubmit',
    startTime: hookStartTime,
    cwd,
    sessionId: input.session_id,
    turnId: input.turn_id,
    prompt,
    outputBytes,
    outputText: text,
    mode: metric.mode || null,
    selectedSkills: metric.selectedSkills || [],
    contextInjected: text.length > 0
  });
  if (routingDecision) {
    recordHookDecision({
      hook: 'UserPromptSubmit',
      hookEventName: 'UserPromptSubmit',
      startTime: hookStartTime,
      cwd,
      sessionId: input.session_id,
      turnId: input.turn_id,
      prompt,
      outputBytes,
      outputText: text,
      mode: metric.mode || routingDecision.mode || null,
      reasonCodes: routingDecision.reasonCodes,
      matchedTerms: routingDecision.matchedTerms,
      traits: routingDecision.traits,
      selectedSkills: metric.selectedSkills || selectedMetricSkills,
      requiredSkills: metric.requiredSkills || requiredMetricSkills,
      contextInjected: text.length > 0
    });
  }
  if (text) {
    process.stdout.write(text);
  }
  process.exit(0);
}
