const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const DEFAULT_INTERACTION_POLICY = {
  version: 1,
  defaultMode: 'chat',
  staleThresholdMinutes: 60,
  maxHookOutputChars: 1200,
  forbiddenSummary: '重型项目状态、workbench、quality-gate、archive evidence、pack state',
  outputBudgetSummary: 'diff/文件名优先；失败只给摘要+尾部；大输出进 evidence',
  verificationSummary: '默认定向验证；全量仅用于 gate/release 或用户明确要求',
  modes: {
    chat: { maxSkills: 0, evidenceRequired: false, disclosure: '轻量回答，不访问仓库' },
    change: { maxSkills: 3, evidenceRequired: false, disclosure: '定向变更流程' }
  }
};

function mergeInteractionPolicy(value) {
  return {
    ...DEFAULT_INTERACTION_POLICY,
    ...value,
    modes: {
      ...DEFAULT_INTERACTION_POLICY.modes,
      ...(value && typeof value.modes === 'object' ? value.modes : {})
    }
  };
}

function formatBudgetContext() {
  return [];
}

function budgetForMode(mode, policy) {
  const modes = policy && policy.modes ? policy.modes : DEFAULT_INTERACTION_POLICY.modes;
  return modes[mode] || modes[policy.defaultMode] || DEFAULT_INTERACTION_POLICY.modes.chat;
}

function numberOrZero(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : 0;
}

function requiredSkillsForMode(mode, names) {
  if (mode === 'chat') {
    return new Set();
  }
  return new Set(names.slice(0, 1));
}

const VISIBILITY_BY_MODE = {
  chat: 'silent',
  change: 'essential'
};

const VALID_VISIBILITIES = new Set(['silent', 'brief', 'essential', 'full']);
function visibilityForMode(mode, overrideVisibility) {
  if (VALID_VISIBILITIES.has(overrideVisibility)) {
    return overrideVisibility;
  }
  return VISIBILITY_BY_MODE[mode] || VISIBILITY_BY_MODE[DEFAULT_INTERACTION_POLICY.defaultMode] || 'silent';
}

function buildInteractionOutputContract(options = {}) {
  const mode = typeof options.mode === 'string' ? options.mode : DEFAULT_INTERACTION_POLICY.defaultMode;
  const policy = mergeInteractionPolicy(options.policy || {});
  const projectRoot = options.projectRoot || process.cwd();
  const traits = options.traits && typeof options.traits === 'object' ? options.traits : {};
  const visibility = visibilityForMode(mode, options.overrideVisibility);
  const selectedSkillNames = Array.isArray(options.selectedSkillNames) ? options.selectedSkillNames : [];
  const explicitRequired = Array.isArray(options.requiredSkillNames)
    ? new Set(options.requiredSkillNames)
    : requiredSkillsForMode(mode, selectedSkillNames);
  const requiredSkills = selectedSkillNames.filter((name) => explicitRequired.has(name));
  const candidateSkills = selectedSkillNames.filter((name) => !explicitRequired.has(name));
  const facts = {
    budget: [],
    access: [],
    verification: [],
    requiredSkills,
    candidateSkills,
    readInstruction: formatSkillReadInstruction(mode)
  };

  return {
    mode,
    visibility,
    contextClasses: contextClassesForVisibility(visibility),
    facts,
    internal: internalFactsForVisibility(visibility, facts),
    public: publicFactsForVisibility(visibility, mode)
  };
}

function contextClassesForVisibility(visibility) {
  if (visibility === 'silent') {
    return ['reference-only'];
  }
  if (visibility === 'brief') {
    return ['must-inline', 'summary-inline', 'reference-only'];
  }
  if (visibility === 'essential') {
    return ['must-inline', 'summary-inline', 'reference-only'];
  }
  return ['must-inline', 'summary-inline', 'reference-only', 'on-demand'];
}

function internalFactsForVisibility(visibility, facts) {
  if (visibility === 'silent') {
    return {};
  }
  if (visibility === 'brief') {
    return {
      budget: facts.budget,
      verification: facts.verification.slice(0, 1),
      candidateSkills: facts.candidateSkills
    };
  }
  if (visibility === 'essential') {
    return {
      budget: facts.budget,
      access: facts.access,
      verification: facts.verification,
      requiredSkills: facts.requiredSkills,
      readInstruction: facts.readInstruction
    };
  }
  return {
    budget: facts.budget,
    access: facts.access,
    verification: facts.verification,
    requiredSkills: facts.requiredSkills,
    candidateSkills: facts.candidateSkills,
    readInstruction: facts.readInstruction
  };
}

function publicFactsForVisibility(visibility, mode) {
  if (visibility === 'silent') {
    return {};
  }
  return {
    summary: [`展示级别：${visibility}`, `模式：${mode}`]
  };
}

function renderInteractionOutputContract(contract) {
  if (!contract || contract.visibility === 'silent') {
    return '';
  }
  const internal = contract.internal || {};
  const lines = [];
  if (contract.visibility === 'full') {
    lines.push(`展示级别：${contract.visibility}`);
  }
  appendArray(lines, internal.budget);
  appendArray(lines, internal.access);
  appendArray(lines, internal.verification);
  appendSkillNames(lines, '必需 skill', internal.requiredSkills);
  appendSkillNames(lines, '候选 skill', internal.candidateSkills);
  if (typeof internal.readInstruction === 'string' && internal.readInstruction.length > 0) {
    lines.push(internal.readInstruction);
  }
  return lines.join('\n');
}

function appendArray(lines, value) {
  if (Array.isArray(value)) {
    lines.push(...value.filter((item) => typeof item === 'string' && item.length > 0));
  }
}

function appendSkillNames(lines, label, value) {
  if (Array.isArray(value) && value.length > 0) {
    lines.push(`${label}：${value.join('、')}`);
  }
}

function appendSkillSections(sections, mode, label, names, requiredSkillNames, registryEntryByName, projectRoot) {
  const required = names.filter((name) => requiredSkillNames.has(name));
  const candidates = names.filter((name) => !requiredSkillNames.has(name));

  if (required.length > 0) {
    sections.push(
      `必需 ${label} skill：`,
      formatSkillList(required, registryEntryByName, projectRoot),
      ''
    );
  }

  if (candidates.length > 0) {
    sections.push(
      `候选 ${label} skill：`,
      formatSkillList(candidates, registryEntryByName, projectRoot),
      ''
    );
  }
}

function formatSkillReadInstruction(mode) {
  if (mode === 'change') {
    return '工具前读取必需 skill；已读且未变可复用。候选仅在必需不足时读。';
  }
  return '';
}

function formatSkillList(names, registryEntryByName, projectRoot) {
  return names.slice(0, 24).map((name) => {
    const contractPath = skillContractPath(projectRoot, name);
    return `- ${name}（读 ${contractPath}）`;
  }).join('\n');
}

function skillContractPath(projectRoot, name) {
  return path.join('.codex', 'skills', name, 'SKILL.md');
}

function compactText(value, maxLength) {
  if (typeof value !== 'string') {
    return '';
  }
  const compact = value.replace(/\s+/g, ' ').trim();
  return compact.length <= maxLength ? compact : `${compact.slice(0, maxLength - 1)}…`;
}

function limitHookOutput(value, policy) {
  const maxLength = Number(policy.maxHookOutputChars || DEFAULT_INTERACTION_POLICY.maxHookOutputChars);
  if (!Number.isFinite(maxLength) || maxLength <= 0 || value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 32)}\n[hook 输出已截断]`;
}

module.exports = {

  DEFAULT_INTERACTION_POLICY,
  appendSkillSections,
  buildInteractionOutputContract,

  budgetForMode,
  contextClassesForVisibility,
  formatBudgetContext,
  formatSkillReadInstruction,
  limitHookOutput,
  mergeInteractionPolicy,

  renderInteractionOutputContract,

  requiredSkillsForMode,
  visibilityForMode
};
