const stopChecklistMessage = `## xian Stop Checklist

结束前确认：

- 当前 change 的 tasks 是否更新。
- 验证 evidence 是否落盘。
- open issues 是否记录。
- 需要用户决策的事项是否明确写出。
- 不要用对话历史替代 .xian-harness/ 或 .xian-harness/ 的事实源。`;

function formatClaudeStopOutput() {
  return JSON.stringify({ additionalContext: stopChecklistMessage });
}

function isStopReentry(input) {
  return Boolean(input && input.stop_hook_active);
}

module.exports = {
  stopChecklistMessage,
  formatClaudeStopOutput,
  isStopReentry
};
