const { unique } = require('./hook-routing.cjs');

const fallbackSkillTerms = {
  'xian-open': ['open', 'intake', '需求', '接入', '澄清', '开一个', '开新'],
  'xian-next': ['next', 'next-action', 'continue', '继续', '下一步', '推进', 'go'],
  'xian-spec': ['spec', 'proposal', '规格', '方案', '需求'],
  'xian-design': ['design', 'architecture', '设计', '架构', '方案'],
  'xian-plan': ['plan', 'task', '规划', '计划', '任务', '普通 typescript'],
  'xian-build': ['build', 'implement', '开发', '实现', '修复'],
  'xian-diagnose': ['bug', 'error', '报错', '失败', '性能', '慢'],
  'xian-project-startup': ['project startup', 'xian-project-startup', '接手项目', '初始化项目', '项目基线', '项目骨架'],
  'xian-verify': ['verify', 'test', '验证', '测试', '自测'],
  'xian-review': ['review', '审查', '复核', '评审', '反馈', 'issue'],
  'xian-gate': ['gate', 'quality', '门禁', '质量'],
  'xian-workbench': ['workbench', 'handoff', '看板', '交接'],
  'xian-archive': ['archive', 'release', '归档', '发布']
};

const defaultModeSkillLimits = {
  chat: 0,
  change: 3
};

function selectRegistrySkills(entries, installedSkills, context) {
  const candidates = [];
  entries.forEach((entry, index) => {
    if (!entry || typeof entry.name !== 'string' || !installedSkills.has(entry.name)) {
      return;
    }

    const baseScore = scoreRegistryEntry(entry, context.prompt);
    const score = baseScore + (baseScore > 0 && context.contextHasXianTokens ? 1 : 0);

    if (score > 0) {
      candidates.push({ name: entry.name, score, index });
    }
  });

  if (candidates.length === 0 && context.explicitXianPrompt && installedSkills.has('xian-open')) {
    candidates.push({ name: 'xian-open', score: 0, index: Number.MAX_SAFE_INTEGER });
  }

  return uniqueRanked(candidates)
    .sort((left, right) => right.score - left.score || left.index - right.index || left.name.localeCompare(right.name))
    .slice(0, context.maxSkills)
    .map((candidate) => candidate.name);
}

function selectFallbackSkills(skillNames, context) {
  const xianSkills = skillNames.filter((name) => name.startsWith('xian-'));
  const selected = [];

  if (xianSkills.length > 0 && (!context.reservedAssetPath || context.explicitXianPrompt)) {
    selected.push(...rankFallbackSkills(xianSkills, context.prompt).slice(0, context.maxSkills));
    if (selected.length === 0 && context.explicitXianPrompt && xianSkills.includes('xian-open')) {
      selected.push('xian-open');
    }
  }

  return unique(selected);
}

function rankFallbackSkills(names, prompt) {
  return names
    .map((name, index) => ({ name, index, score: scoreFallbackSkill(name, prompt) }))
    .filter((candidate) => candidate.score > 0)
    .sort((left, right) => right.score - left.score || left.index - right.index || left.name.localeCompare(right.name))
    .map((candidate) => candidate.name);
}

function scoreRegistryEntry(entry, prompt) {
  return matchScore(entry.activation && entry.activation.promptPatterns, prompt, 2)
    + matchScore(entry.keywords, prompt, 1);
}

function matchScore(patterns, prompt, weight) {
  if (!Array.isArray(patterns) || patterns.length === 0) {
    return 0;
  }

  const lower = prompt.toLowerCase();
  return patterns.reduce((score, pattern) => {
    if (typeof pattern !== 'string' || pattern.length === 0) {
      return score;
    }
    return matchesRegistryTerm(pattern, prompt, lower) ? score + weight : score;
  }, 0);
}

function matchesRegistryTerm(pattern, prompt, lowerPrompt) {
  const normalized = pattern.trim();
  if (/^[A-Za-z0-9_]+$/.test(normalized)) {
    return new RegExp(`(^|[^A-Za-z0-9_])${escapeRegExp(normalized)}([^A-Za-z0-9_]|$)`, 'i').test(prompt);
  }
  if (/^[\p{L}\p{N}_ -]+$/u.test(normalized)) {
    return lowerPrompt.includes(normalized.toLowerCase());
  }
  try {
    return new RegExp(normalized, 'i').test(prompt);
  } catch {
    return lowerPrompt.includes(normalized.toLowerCase());
  }
}

function matchedRegistryTermsForSkills(names, registryEntryByName, value) {
  const lower = value.toLowerCase();
  const terms = [];
  names.forEach((name) => {
    const entry = registryEntryByName.get(name);
    if (!entry) {
      return;
    }
    [
      ...(Array.isArray(entry.activation && entry.activation.promptPatterns) ? entry.activation.promptPatterns : []),
      ...(Array.isArray(entry.keywords) ? entry.keywords : [])
    ].forEach((term) => {
      if (typeof term === 'string' && term.length > 0 && matchesRegistryTerm(term, value, lower)) {
        terms.push(term);
      }
    });
  });
  return unique(terms).slice(0, 24);
}

function scoreFallbackSkill(name, prompt) {
  const lower = prompt.toLowerCase();
  const normalizedName = name.toLowerCase().replace(/^xian-/, '').replace(/-/g, ' ');
  const terms = unique([
    name.toLowerCase(),
    normalizedName,
    ...(fallbackSkillTerms[name] || [])
  ]).map((term) => term.toLowerCase());

  return terms.reduce((score, term) => lower.includes(term) ? score + 1 : score, 0);
}

function maxSelectedSkills(mode, envValue) {
  const fallback = defaultModeSkillLimits[mode] ?? 2;
  const value = Number(envValue || String(fallback));
  return Number.isFinite(value) && value > 0 ? Math.min(Math.floor(value), 8) : fallback;
}

function uniqueRanked(values) {
  const byName = new Map();
  for (const value of values) {
    const existing = byName.get(value.name);
    if (!existing || value.score > existing.score) {
      byName.set(value.name, value);
    }
  }
  return [...byName.values()];
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

module.exports = {
  matchedRegistryTermsForSkills,
  matchesRegistryTerm,
  maxSelectedSkills,
  selectFallbackSkills,
  selectRegistrySkills
};
