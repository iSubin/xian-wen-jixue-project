const path = require('node:path');

const PRE_TOOL_USE_HOOK_VERSION = '1';
const PRE_TOOL_USE_POLICY_ID = 'xian-pre-tool-use-generic-safety-v1';

function evaluatePreToolUse(input, options = {}) {
  const toolName = String(input.tool_name || input.tool || '');
  const toolInput = input.tool_input || input;

  if (/^(Bash|Shell|shell)$/i.test(toolName)) {
    const command = commandFrom(toolInput);
    const blocked = firstBlockedCommand(command);
    if (blocked) {
      return withHookDiagnostics({
        action: 'block',
        reason: `xian Harness pre-tool guard blocked a destructive or cross-session risky command: ${blocked.reason}`,
        command
      }, input, toolInput, options);
    }
    const managedPushProbe = inspectManagedPushCommand(command, process.cwd());
    let managedPush = managedPushProbe;
    if (managedPushProbe.detected) {
      const workdir = resolveManagedPushWorkdir(input, toolInput, options);
      if (!workdir.ok) {
        return withHookDiagnostics({
          action: 'block',
          reason: `xian Harness pre-tool guard blocked a managed push whose tool workdir is not statically safe: ${workdir.reason}`,
          command
        }, input, toolInput, options);
      }
      managedPush = inspectManagedPushCommand(command, workdir.path);
    }
    if (managedPush.detected) {
      if (!managedPush.target) {
        return withHookDiagnostics({
          action: 'block',
          reason: `xian Harness pre-tool guard blocked a managed push whose local Git identity is not statically safe: ${managedPush.reason}`,
          command
        }, input, toolInput, options);
      }
    }
    const warning = firstWarningCommand(command);
    if (warning) {
      return withHookDiagnostics({
        action: 'warn',
        message: warning.message,
        command
      }, input, toolInput, options, managedPush.target);
    }
  }

  if (/^(Write|Edit|MultiEdit|apply_patch)$/i.test(toolName)) {
    const payload = writeTargetText(toolName, toolInput);
    const hits = sensitiveFileHits(payload);
    if (hits.length > 0) {
      return withHookDiagnostics({
        action: 'warn',
        message: `敏感文件写入：${hits.join(', ')}。请确保不要把密钥、Token 或生产配置提交到 Git。`
      }, input, toolInput, options);
    }
  }

  return { action: 'allow' };
}

function resolveManagedPushWorkdir(input, toolInput, options) {
  const candidates = [
    {
      name: 'tool_input.workdir',
      present: Object.prototype.hasOwnProperty.call(toolInput, 'workdir'),
      value: toolInput.workdir
    },
    {
      name: 'options.cwd',
      present: Object.prototype.hasOwnProperty.call(options, 'cwd'),
      value: options.cwd
    },
    {
      name: 'input.cwd',
      present: Object.prototype.hasOwnProperty.call(input, 'cwd'),
      value: input.cwd
    },
    {
      name: 'process.cwd()',
      present: true,
      value: process.cwd()
    }
  ];
  const selected = candidates.find((candidate) => candidate.present);
  if (!selected || typeof selected.value !== 'string') {
    return {
      ok: false,
      path: null,
      reason: `${selected?.name || 'workdir'} must be an absolute string.`
    };
  }
  if (selected.value.trim().length === 0 || selected.value.includes('\0')) {
    return {
      ok: false,
      path: null,
      reason: `${selected.name} must be non-empty and NUL-free.`
    };
  }
  if (!path.isAbsolute(selected.value)) {
    return {
      ok: false,
      path: null,
      reason: `${selected.name} must be an absolute path.`
    };
  }
  try {
    return { ok: true, path: path.resolve(selected.value), reason: null };
  } catch (error) {
    return {
      ok: false,
      path: null,
      reason: `${selected.name} could not be resolved: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

function formatPreToolUseOutput(decision, runtime) {
  if (decision.action === 'allow') {
    return '{}';
  }

  if (decision.action === 'warn') {
    if (runtime === 'codex') {
      return JSON.stringify({
        systemMessage: decision.message
      });
    }
    return JSON.stringify({
      systemMessage: decision.message,
      xianHarnessHook: decision.diagnostics
    });
  }

  if (runtime === 'codex') {
    return JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: decision.reason
      }
    });
  }

  return JSON.stringify({
    decision: 'block',
    reason: decision.reason,
    xianHarnessHook: decision.diagnostics
  });
}

function withHookDiagnostics(decision, input, toolInput, options, resolvedTarget) {
  return {
    ...decision,
    diagnostics: {
      hookSource: absoluteDiagnosticPath(options.hookSource) || __filename,
      hookVersion: PRE_TOOL_USE_HOOK_VERSION,
      taskRoot: absoluteDiagnosticPath(options.taskRoot)
        || absoluteDiagnosticPath(options.cwd)
        || absoluteDiagnosticPath(input.cwd)
        || process.cwd(),
      resolvedTarget: absoluteDiagnosticPath(resolvedTarget)
        || diagnosticTarget(input, toolInput, options),
      policyId: PRE_TOOL_USE_POLICY_ID
    }
  };
}

function diagnosticTarget(input, toolInput, options) {
  const values = [
    toolInput.workdir,
    options.cwd,
    input.cwd,
    options.taskRoot,
    process.cwd()
  ];
  for (const value of values) {
    const resolved = absoluteDiagnosticPath(value);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}

function absoluteDiagnosticPath(value) {
  if (typeof value !== 'string' || value.trim().length === 0 || value.includes('\0')) {
    return null;
  }
  try {
    return path.resolve(value);
  } catch {
    return null;
  }
}

function commandFrom(inputValue) {
  if (typeof inputValue.command === 'string') {
    return inputValue.command;
  }
  if (typeof inputValue.cmd === 'string') {
    return inputValue.cmd;
  }
  if (Array.isArray(inputValue.argv)) {
    return inputValue.argv.join(' ');
  }
  return '';
}

function firstBlockedCommand(command) {
  if (!command) {
    return null;
  }

  const blockedGitMutation = firstBlockedGitMutation(command);
  if (blockedGitMutation) {
    return blockedGitMutation;
  }

  const blocked = [
    { pattern: /[12]?\s*>\s*nul\b/i, reason: 'Windows nul redirection can create a real file named nul; use /dev/null or remove the redirect.' },
    { pattern: /git\s+reset\s+--hard/, reason: 'git reset --hard may discard user or cross-session changes.' },
    { pattern: /git\s+clean\s+-fd/, reason: 'git clean -fd may delete untracked user files.' },
    { pattern: /git\s+stash(\s|$)/, reason: 'git stash may hide user or cross-session changes.' },
    { pattern: /git\s+checkout\s+--\s+/, reason: 'git checkout -- may revert files outside the active task.' },
    { pattern: /rm\s+-rf\s+\/(?!\w)/, reason: 'rm -rf / is destructive.' },
    { pattern: /rm\s+-rf\s+(--\s+)?(\.\/)?\*/, reason: 'rm -rf wildcard deletion is destructive.' },
    { pattern: /rm\s+-rf\s+(?:--\s+)?(?:["']\.\/?["']|\.\/?)(?=\s|$|[;&|])/, reason: 'rm -rf . may delete the current project.' },
    { pattern: /rm\s+-rf\s+["']?[A-Za-z]:[\/\\][^"'\s]*["']?\s*\*?/i, reason: 'rm -rf against a Windows absolute path is destructive.' },
    { pattern: /rm\s+-rf\s+(?:--\s+)?["']?\/(home|usr|etc|var|opt|root|tmp|private\/tmp|bin|sbin|lib)\b/i, reason: 'rm -rf against a system directory is destructive.' },
    { pattern: /drop\s+database/i, reason: 'database deletion is destructive.' },
    { pattern: /truncate\s+table/i, reason: 'table truncation is destructive.' },
    { pattern: />\s*\/dev\/sd[a-z]/, reason: 'direct writes to disk devices are destructive.' },
    { pattern: /mkfs\./, reason: 'filesystem formatting is destructive.' },
    { pattern: /:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:/, reason: 'fork bomb commands can exhaust system resources.' },
    { pattern: /kill\s+-9/, reason: 'kill -9 may terminate unrelated developer processes.' },
    { pattern: /npx\s+kill-port/, reason: 'npx kill-port should be run explicitly by the user when needed.' },
    { pattern: /taskkill\s+(\/F\s+)?\/IM\s+node\.exe/i, reason: 'taskkill /IM node.exe may terminate the agent runtime.' },
    { pattern: /Stop-Process\b[^|;\n]*-Name\s+["']?node\*?["']?(\b|\s)/i, reason: 'Stop-Process -Name node may terminate the agent runtime.' },
    { pattern: /Get-Process\b[^|;\n]*\bnode\b[^|;\n]*\|\s*Stop-Process/i, reason: 'piped Stop-Process for node may terminate the agent runtime.' },
    { pattern: /\b(powershell|pwsh)(\.exe)?\s+[-\/]+(enc|encodedcommand|e\b)/i, reason: 'PowerShell EncodedCommand hides command content from static review.' },
    { pattern: /\bFormat-Volume\b/i, reason: 'PowerShell Format-Volume is destructive.' },
    { pattern: /\bClear-Disk\b[^|;\n]*-RemoveData/i, reason: 'PowerShell Clear-Disk removes disk data.' },
    { pattern: /\b(Remove-Partition|Remove-Volume)\b[^|;\n]*-(Confirm|Force)/i, reason: 'PowerShell partition or volume removal is destructive.' },
    { pattern: /\b(Stop-Computer|Restart-Computer)\b[^|;\n]*-Force/i, reason: 'forced computer stop or restart is unsafe for agent sessions.' },
    { pattern: /\bshutdown\b[^|;\n]*\/[rspf]\b/i, reason: 'shutdown can stop or restart the machine.' },
    { pattern: /\b(Invoke-RestMethod|Invoke-WebRequest|irm|iwr)\b[^|;\n]*\|\s*(iex|Invoke-Expression)\b/i, reason: 'remote download piped to execution cannot be statically audited.' }
  ];

  const direct = blocked.find((item) => item.pattern.test(command));
  if (direct) {
    return direct;
  }

  if (!/[A-Za-z]:[\\/][^"'\s|;<>]+/.test(command)) {
    return null;
  }

  const windowsDeletes = [
    { pattern: /Remove-Item\b/i, reason: 'PowerShell Remove-Item deletes a Windows absolute path.' },
    { pattern: /\b(rm|ri|erase|del)\b\s+[^|;\n]*[A-Za-z]:[\\/]/i, reason: 'Shell alias deletes a Windows absolute path.' },
    { pattern: /\b(rd|rmdir)\b[^|;\n]*\/[sS]\b/i, reason: 'cmd recursively deletes a Windows absolute path.' },
    { pattern: /\bdel\b[^|;\n]*\/[sSfF]\b/i, reason: 'cmd force deletes a Windows absolute path.' },
    { pattern: /\[\s*(System\.)?IO\.File\s*\]\s*::\s*Delete/i, reason: '.NET File API deletes a Windows absolute path.' },
    { pattern: /\[\s*(System\.)?IO\.Directory\s*\]\s*::\s*Delete/i, reason: '.NET Directory API deletes a Windows absolute path.' },
    { pattern: /\bNew-Object\s+(System\.)?IO\.(FileInfo|DirectoryInfo)\b/i, reason: '.NET FileInfo or DirectoryInfo can delete a Windows absolute path.' },
    { pattern: /Microsoft\.VisualBasic\.FileIO\.FileSystem.*Delete(File|Directory)/i, reason: 'VisualBasic FileSystem deletes a Windows absolute path.' },
    { pattern: /\b(Invoke-Expression|iex)\b/i, reason: 'Indirect execution with a Windows absolute path cannot be statically audited.' },
    { pattern: /\brobocopy\b[^|;\n]*\/(mir|purge)\b/i, reason: 'robocopy MIR or PURGE can delete a Windows absolute path.' },
    { pattern: /\bClear-Content\b/i, reason: 'PowerShell Clear-Content empties a Windows absolute path file.' }
  ];
  return windowsDeletes.find((item) => item.pattern.test(command)) ?? null;
}

function firstBlockedGitMutation(command) {
  const invocations = findLiteralGitInvocations(command);
  for (const invocation of invocations) {
    if (invocation.subcommand === 'add') {
      if (invocation.args.some((argument) => (
        argument === '--all'
        || isCombinedShortOption(argument, 'A')
      ))) {
        return {
          reason: 'git add -A/--all broadly stages repository changes; stage explicit pathspecs instead.'
        };
      }
      if (invocation.args.some(isRepositoryRootPathspec)) {
        return {
          reason: 'git add . or ./ broadly stages the current tree; stage explicit pathspecs instead.'
        };
      }
    }
    if (invocation.subcommand === 'commit' && invocation.args.some((argument) => (
      argument === '--no-verify'
      || isCombinedShortOption(argument, 'n')
    ))) {
      return {
        reason: 'git commit --no-verify/-n bypasses repository verification hooks.'
      };
    }
    if (invocation.subcommand === 'push' && invocation.args.some(isForcePushArgument)) {
      return {
        reason: 'force push arguments may overwrite shared history and are not allowed for Agent-managed Git mutation.'
      };
    }
  }
  return null;
}

function inspectManagedPushCommand(command, cwd) {
  const loosePushes = findLiteralGitInvocations(command)
    .filter((invocation) => invocation.subcommand === 'push');
  if (loosePushes.length === 0 && !containsStandalonePushToken(command)) {
    return { detected: false, target: null, reason: null };
  }

  const parsed = parseStrictLiteralWords(command);
  if (!parsed.ok) {
    return { detected: true, target: null, reason: parsed.reason };
  }
  if (parsed.words.length === 0 || !isGitExecutable(parsed.words[0])) {
    return {
      detected: true,
      target: null,
      reason: 'managed push must start directly with the literal git executable; wrappers and assignments are not allowed.'
    };
  }
  const invocation = parseGitInvocation(parsed.words, 0);
  if (!invocation || invocation.subcommand !== 'push' || invocation.endIndex !== parsed.words.length) {
    return {
      detected: true,
      target: null,
      reason: 'managed push must contain exactly one standalone literal git push invocation.'
    };
  }
  if (invocation.ambiguousGlobalOption) {
    return {
      detected: true,
      target: null,
      reason: `managed push does not allow Git global identity/config override ${invocation.ambiguousGlobalOption}.`
    };
  }
  if (invocation.args.some(isForcePushArgument)) {
    return {
      detected: true,
      target: null,
      reason: 'force push arguments are not allowed.'
    };
  }

  let target = path.resolve(cwd);
  for (const gitCwd of invocation.gitCwds) {
    if (!isLiteralGitCwd(gitCwd)) {
      return {
        detected: true,
        target: null,
        reason: 'git -C must use a non-empty literal path without shell expansion.'
      };
    }
    target = path.resolve(target, gitCwd);
  }
  return { detected: true, target, reason: null };
}

function containsStandalonePushToken(command) {
  const words = tokenizeShellLoosely(command);
  const executable = String(words[0] || '');
  if (words[1] === 'push') {
    return true;
  }
  if (!/(?:^|[\\/])(ba|z|fi|da)?sh(?:\.exe)?$/iu.test(executable)) {
    return false;
  }
  const commandOptionIndex = words.indexOf('-c');
  return commandOptionIndex >= 0
    && /\bgit\s+push\b/iu.test(String(words[commandOptionIndex + 1] || ''));
}

function findLiteralGitInvocations(command) {
  const tokens = tokenizeShellLoosely(command);
  const invocations = [];
  for (let index = 0; index < tokens.length; index += 1) {
    if (!isGitExecutable(tokens[index])) {
      continue;
    }
    const invocation = parseGitInvocation(tokens, index);
    if (invocation) {
      invocations.push(invocation);
      index = Math.max(index, invocation.endIndex - 1);
    }
  }
  return invocations;
}

function parseGitInvocation(words, gitIndex) {
  const gitCwds = [];
  let ambiguousGlobalOption = null;
  let index = gitIndex + 1;
  while (index < words.length) {
    const word = words[index];
    if (isShellBoundaryToken(word)) {
      return null;
    }
    if (word === '-C') {
      const value = words[index + 1];
      if (!value || isShellBoundaryToken(value)) {
        return null;
      }
      gitCwds.push(value);
      index += 2;
      continue;
    }
    if (word.startsWith('-C') && word.length > 2) {
      gitCwds.push(word.slice(2));
      index += 1;
      continue;
    }
    if (word === '--no-pager') {
      index += 1;
      continue;
    }
    if (word.startsWith('-')) {
      ambiguousGlobalOption = ambiguousGlobalOption || word;
      if (gitGlobalOptionConsumesValue(word)) {
        index += 2;
      } else {
        index += 1;
      }
      continue;
    }
    const endIndex = nextShellBoundaryIndex(words, index + 1);
    return {
      subcommand: word,
      args: words.slice(index + 1, endIndex),
      gitCwds,
      ambiguousGlobalOption,
      endIndex
    };
  }
  return null;
}

function tokenizeShellLoosely(command) {
  const tokens = [];
  let current = '';
  let quote = null;
  let escaped = false;
  const flush = () => {
    if (current) {
      tokens.push(current);
      current = '';
    }
  };
  for (let index = 0; index < command.length; index += 1) {
    const character = command[index];
    if (escaped) {
      current += character;
      escaped = false;
      continue;
    }
    if (character === '\\' && quote !== "'") {
      escaped = true;
      continue;
    }
    if (quote) {
      if (character === quote) {
        quote = null;
      } else {
        current += character;
      }
      continue;
    }
    if (character === "'" || character === '"') {
      quote = character;
      continue;
    }
    if (/\s/u.test(character)) {
      flush();
      if (character === '\n' || character === '\r') {
        tokens.push('\n');
      }
      continue;
    }
    if (';&|()<>'.includes(character)) {
      flush();
      const paired = command[index + 1] === character ? character + character : character;
      tokens.push(paired);
      if (paired.length === 2) {
        index += 1;
      }
      continue;
    }
    current += character;
  }
  flush();
  return tokens;
}

function parseStrictLiteralWords(command) {
  const words = [];
  let current = '';
  let quote = null;
  let escaped = false;
  const flush = () => {
    if (current) {
      words.push(current);
      current = '';
    }
  };
  for (let index = 0; index < command.length; index += 1) {
    const character = command[index];
    if (escaped) {
      if (character === '\n' || character === '\r') {
        return { ok: false, words: [], reason: 'managed push does not allow escaped newlines.' };
      }
      current += character;
      escaped = false;
      continue;
    }
    if (quote === "'") {
      if (character === "'") {
        quote = null;
      } else if (character === '\n' || character === '\r') {
        return { ok: false, words: [], reason: 'managed push does not allow newlines.' };
      } else {
        current += character;
      }
      continue;
    }
    if (quote === '"') {
      if (character === '"') {
        quote = null;
      } else if (character === '\\') {
        const nextCharacter = command[index + 1];
        if (nextCharacter === '\n' || nextCharacter === '\r') {
          return { ok: false, words: [], reason: 'managed push does not allow escaped newlines.' };
        }
        if (['$', '`', '"', '\\'].includes(nextCharacter)) {
          current += nextCharacter;
          index += 1;
        } else {
          current += '\\';
        }
      } else if (character === '$' || character === '`') {
        return { ok: false, words: [], reason: 'managed push does not allow shell expansion.' };
      } else if (character === '\n' || character === '\r') {
        return { ok: false, words: [], reason: 'managed push does not allow newlines.' };
      } else {
        current += character;
      }
      continue;
    }
    if (character === '\\') {
      escaped = true;
      continue;
    }
    if (character === "'" || character === '"') {
      quote = character;
      continue;
    }
    if (character === '\n' || character === '\r') {
      return { ok: false, words: [], reason: 'managed push does not allow newlines or compound commands.' };
    }
    if (/\s/u.test(character)) {
      flush();
      continue;
    }
    if (';&|<>()`$#*?[]{}~'.includes(character)) {
      return {
        ok: false,
        words: [],
        reason: `managed push does not allow shell operator, redirection, substitution, comment, or expansion token ${character}.`
      };
    }
    current += character;
  }
  if (escaped || quote) {
    return { ok: false, words: [], reason: 'managed push contains an unterminated escape or quote.' };
  }
  flush();
  return { ok: true, words, reason: null };
}

function gitGlobalOptionConsumesValue(option) {
  return [
    '-c',
    '--config-env',
    '--exec-path',
    '--git-dir',
    '--work-tree',
    '--namespace',
    '--super-prefix'
  ].includes(option);
}

function isGitExecutable(word) {
  return /(?:^|[\\/])git(?:\.exe)?$/iu.test(String(word || ''));
}

function isShellBoundaryToken(word) {
  return ['&&', '||', ';', '|', '&', '(', ')', '<', '>', '<<', '>>', '\n'].includes(word);
}

function nextShellBoundaryIndex(words, startIndex) {
  for (let index = startIndex; index < words.length; index += 1) {
    if (isShellBoundaryToken(words[index])) {
      return index;
    }
  }
  return words.length;
}

function isCombinedShortOption(argument, flag) {
  return /^-[^-]+$/u.test(argument) && argument.slice(1).includes(flag);
}

function isRepositoryRootPathspec(argument) {
  return /^\.\/?$/u.test(argument);
}

function isForcePushArgument(argument) {
  return argument === '--force'
    || argument.startsWith('--force-with-lease')
    || argument === '--force-if-includes'
    || isCombinedShortOption(argument, 'f')
    || argument.startsWith('+');
}

function isLiteralGitCwd(value) {
  return typeof value === 'string'
    && value.length > 0
    && !/[\0$`*?[\]{}~]/u.test(value);
}

function firstWarningCommand(command) {
  const warnings = [
    { pattern: /git\s+push\s+--force/, message: 'Force push 可能覆盖他人代码' },
    { pattern: /npm\s+publish/, message: '即将发布到 npm' },
    { pattern: /docker\s+system\s+prune/, message: '将清理所有未使用的 Docker 资源' }
  ];
  return warnings.find((item) => item.pattern.test(command)) ?? null;
}

function writeTargetText(name, inputValue) {
  if (/^apply_patch$/i.test(name)) {
    return extractPatchTargetPaths(inputValue.input || inputValue.patch || '').join('\n');
  }
  return [
    inputValue.file_path,
    inputValue.path
  ].filter(Boolean).join('\n');
}

function extractPatchTargetPaths(patchText) {
  if (typeof patchText !== 'string' || patchText.length === 0) {
    return [];
  }
  return patchText
    .split(/\r?\n/)
    .map((line) => line.match(/^\*\*\* (?:Add|Update|Delete) File: (.+)$/))
    .filter(Boolean)
    .map((match) => match[1].trim());
}

function sensitiveFileHits(payload) {
  const sensitive = [
    '.env.production',
    'application-prod.yml',
    'application-prod.yaml',
    'credentials.json',
    'secrets.json',
    '.gitee_token'
  ];
  return sensitive.filter((item) => payload.includes(item));
}

module.exports = {
  PRE_TOOL_USE_HOOK_VERSION,
  PRE_TOOL_USE_POLICY_ID,
  evaluatePreToolUse,
  formatPreToolUseOutput,
  commandFrom,
  firstBlockedCommand,
  inspectManagedPushCommand,
  sensitiveFileHits
};
