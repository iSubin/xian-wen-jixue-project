const skipPatterns = [
  'continued from a previous conversation',
  'ran out of context',
  'No code restore',
  'Conversation compacted',
  'commands restored',
  'context window',
  'session is being continued'
];

const leadingLightweightQuestionTerms = [
  '接下来呢',
  '然后呢',
  '看看',
  '看一下',
  '确认一下',
  '评估一下'
];

const lightweightQuestionTerms = [
  '怎么看',
  '为什么',
  '什么意思',
  '如何理解',
  '是否',
  '是不是',
  '能否',
  '可以吗',
  '讲一下',
  '聊一下',
  '评价一下',
  '有哪些'
];

const explicitLightweightTerms = [
  '轻量回答',
  '不要读文件',
  '不用读文件',
  '不要跑命令',
  '不用跑命令',
  '只讨论方案',
  '只聊方案',
  '不要改代码',
  '不用改代码',
  '先不要改',
  '先不改',
  '只看方案',
  'only discuss',
  'no file reads',
  'do not read files',
  'do not edit',
  'no code changes'
];

const snapshotTerms = [
  '当前项目状态',
  '项目状态',
  '当前状态',
  '项目进展',
  '现在到哪',
  '到哪了',
  '进展怎么样'
];

const productWideTerms = [
  '整个产品',
  '整体产品',
  '整个工程',
  '整个项目',
  '整体架构',
  '全局状态',
  '完整结论',
  '完整评价',
  '完整评估',
  '全面评估',
  '评价整个',
  '评估整个',
  '全面 review',
  '全面review',
  '整体评价',
  '产品级评估',
  'product review',
  'whole product',
  'global status'
];

const inspectLiteTerms = [
  '检查',
  '看看',
  '看一下',
  '确认',
  '评估',
  '状态',
  '反馈',
  'review',
  '审查',
  '复核',
  '评审',
  '有哪些',
  '有没有'
];

const reviewOnlyTerms = [
  'review',
  '审查',
  '复核',
  '评审',
  '评价',
  '评估'
];

const explicitChangeActionTerms = [
  '修复',
  '修改',
  '改一下',
  '改一改',
  '帮我改',
  '执行',
  '提交',
  '合并',
  '验证',
  '继续',
  '推进',
  '下一步',
  '开一个',
  '开新',
  '新 change',
  '跑测试',
  '补测试',
  '补充测试',
  '补验证',
  '补必要验证',
  '开始实现',
  '去实现',
  '请实现',
  '实现一下',
  '继续实现',
  '写成',
  '调整一下',
  '帮我调整',
  '改善一下',
  '落地',
  '删除',
  '清理',
  'fix',
  'commit',
  'push',
  'merge',
  'run test',
  'write tests',
  'add tests'
];

const strongQuestionActionTerms = [
  '帮我改',
  '请改',
  '请修改',
  '请修复',
  '修复一下',
  '直接改',
  '跑测试',
  '补测试',
  '补充测试',
  '补验证',
  '补必要验证',
  '开始实现',
  '去实现',
  '请实现',
  '实现一下',
  '继续实现',
  '开一个',
  '开新',
  '新 change',
  'fix',
  'run test',
  'write tests',
  'add tests'
];

const changeTerms = [
  '开发',
  '修复',
  '实现',
  '执行',
  '创建',
  '规划',
  '提交',
  'push',
  '合并',
  '验证',
  '继续',
  '推进',
  '下一步',
  '开一个',
  '开新',
  '新 change',
  '跑',
  '测试',
  '生成',
  '更新',
  '优化',
  '加强',
  '处理',
  '落地',
  '归档',
  '修改',
  '改一下',
  '改一改',
  '帮我改',
  '写成',
  '调整一下',
  '帮我调整',
  '改善一下',
  '补验证',
  '补必要验证',
  '删除',
  '清理',
  'fix',
  'change',
  'implement',
  'develop',
  'run',
  'create',
  'plan',
  'commit',
  'push',
  'merge',
  'test',
  'generate',
  'update',
  'optimize'
];

const deepAuditTerms = [
  '深度 review',
  '深度review',
  '深度评审',
  '深度复核',
  '深度审查',
  '进入 change',
  '创建 change',
  '开一个 change',
  '完整 change',
  '完整流程',
  '全面审计',
  '深扫',
  '完整验收',
  '系统性验收',
  '跑验收',
  '跑 gate',
  '质量门禁',
  'archive',
  'release',
  '归档',
  '发布验收',
  'change-full',
  'deep-audit',
  'deep audit'
];

const bareHandoffContinuationTerms = [
  '继续',
  '下一步',
  'go',
  'continue'
];

const evidenceReviewTerms = [
  'gate/archive',
  'gate archive',
  'archive/gate',
  'gate 产物',
  'archive 产物',
  '归档产物',
  '门禁产物',
  '质量门禁产物',
  'workbench 产物',
  '看板产物',
  '证据产物',
  '状态变更'
];

function classifyPromptTraits(value) {
  return traitsFromMatches(classifyPromptMatches(value));
}

function classifyPromptMatches(value) {
  return {
    explicitLightweight: matchedTerms(value, explicitLightweightTerms),
    evidenceReview: matchedTerms(value, evidenceReviewTerms),
    wholeProjectEvaluation: matchedTerms(value, productWideTerms),
    deepAudit: matchedTerms(value, deepAuditTerms),
    change: matchedTerms(value, changeTerms),
    snapshot: matchedTerms(value, snapshotTerms),
    reviewOnly: matchedTerms(value, reviewOnlyTerms),
    inspectLite: matchedTerms(value, inspectLiteTerms),
    lightweightQuestion: matchedLightweightQuestionTerms(value)
  };
}

function traitsFromMatches(matches) {
  return {
    explicitLightweight: matches.explicitLightweight.length > 0,
    evidenceReview: matches.evidenceReview.length > 0,
    wholeProjectEvaluation: matches.wholeProjectEvaluation.length > 0
  };
}

function createRoutingDecision(mode, value, traits, matches) {
  return {
    mode,
    reasonCodes: routingReasonCodesFor(mode, value, traits, matches),
    matchedTerms: matches,
    traits
  };
}

function routingReasonCodesFor(mode, value, traits, matches) {
  const codes = [];
  if (traits.evidenceReview) {
    codes.push('evidence-review');
  }
  if (matches.deepAudit.length > 0 && isDeepAuditPrompt(value)) {
    codes.push('deep-audit-term');
  }
  if (traits.explicitLightweight) {
    codes.push('explicit-lightweight');
  }
  if (traits.wholeProjectEvaluation) {
    codes.push('whole-project-evaluation');
  }
  if (matches.reviewOnly.length > 0 && isReviewOnlyPrompt(value)) {
    codes.push('review-only');
  }
  if (matches.change.length > 0 && isChangePrompt(value)) {
    codes.push('change-term');
  }
  if (matches.snapshot.length > 0 && isSnapshotPrompt(value)) {
    codes.push('snapshot-term');
  }
  if (isLightweightQuestion(value)) {
    codes.push('lightweight-question');
  }
  if (matches.inspectLite.length > 0 && isInspectLitePrompt(value)) {
    codes.push('inspect-lite-term');
  }
  if (codes.length === 0) {
    codes.push(`default-${mode}`);
  }
  return unique(codes);
}

function classifyInteractionMode(value, traits = classifyPromptTraits(value)) {
  if (isChangePrompt(value)) {
    return 'change';
  }
  return 'chat';
}

function isLightweightQuestion(value) {
  if (isChangePrompt(value) || isDeepAuditPrompt(value) || isSnapshotPrompt(value)) {
    return false;
  }

  const normalized = value.trim();
  if (normalized.length <= 120 && /[?？]$/.test(normalized)) {
    return true;
  }

  return leadingLightweightQuestionTerms.some((term) => normalized.startsWith(term))
    || includesAnyTerm(normalized, lightweightQuestionTerms);
}

function isInspectLitePrompt(value) {
  return includesAnyTerm(value.toLowerCase(), inspectLiteTerms);
}

function isReviewOnlyPrompt(value) {
  const lower = value.toLowerCase();
  return includesAnyTerm(lower, reviewOnlyTerms) && !includesAnyTerm(lower, explicitChangeActionTerms);
}

function isSnapshotPrompt(value) {
  return includesAnyTerm(value.toLowerCase(), snapshotTerms);
}

function isChangePrompt(value) {
  if (isBareHandoffContinuation(value)) {
    return false;
  }
  if (isLightweightActionQuestion(value)) {
    return false;
  }
  return includesAnyTerm(value.toLowerCase(), changeTerms);
}

function isBareHandoffContinuation(value) {
  const normalized = value.trim().toLowerCase();
  return bareHandoffContinuationTerms.includes(normalized);
}

function isLightweightActionQuestion(value) {
  const normalized = value.trim();
  if (!/[?？]$/.test(normalized)) {
    return false;
  }
  if (hasExplicitQuestionAction(normalized)) {
    return false;
  }
  return /^(能否|是否|你觉得|这个方案是否|这段说明能不能)/.test(normalized)
    || includesAnyTerm(normalized, ['能不能', '是否要', '怎么改善', '需要哪些', '是否正确', '是否正常', '有哪些前置', '要不要']);
}

function hasExplicitQuestionAction(value) {
  const lower = value.toLowerCase();
  return includesAnyTerm(lower, strongQuestionActionTerms)
    || /(?:帮我|请|直接|顺手|麻烦|可以|能否|能不能).{0,8}(改一下|改一改|修改|修复|调整一下|补测试|补验证|提交|执行|删除|清理|实现一下)/.test(value);
}

function isDeepAuditPrompt(value) {
  return includesAnyTerm(value.toLowerCase(), deepAuditTerms);
}

function matchedTerms(value, terms) {
  const lower = value.toLowerCase();
  return unique(
    terms.filter((term) => typeof term === 'string' && term.length > 0 && lower.includes(term.toLowerCase()))
  );
}

function matchedLightweightQuestionTerms(value) {
  const normalized = value.trim();
  const matches = [];
  leadingLightweightQuestionTerms.forEach((term) => {
    if (normalized.startsWith(term)) {
      matches.push(term);
    }
  });
  matches.push(...matchedTerms(value, lightweightQuestionTerms));
  if (normalized.length <= 120 && /[?？]$/.test(normalized)) {
    matches.push('question-mark');
  }
  return unique(matches);
}

function hasXianContextTokens(value) {
  return /\b(xian|harness|agent)\b/i.test(value)
    || includesAnyTerm(value, ['验收', '门禁', '看板']);
}

function unique(values) {
  return [...new Set(values)];
}

function includesAnyTerm(value, terms) {
  return terms.some((term) => value.includes(term));
}

module.exports = {
  classifyInteractionMode,
  classifyPromptMatches,
  classifyPromptTraits,
  createRoutingDecision,
  hasXianContextTokens,
  includesAnyTerm,
  isBareHandoffContinuation,
  matchedTerms,
  skipPatterns,
  traitsFromMatches,
  unique
};
