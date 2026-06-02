#!/bin/bash
# Claude 工作空间自动同步脚本
# 由 Claude Code Stop hook 触发

REPO_DIR="$HOME/claude-sync-workspace"
cd "$REPO_DIR" || exit 0

# 检查是否在 git 仓库内
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# 检查是否有变更（包括未跟踪文件）
git add -A
if git diff --cached --quiet; then
    exit 0
fi

# 提交并推送
git commit -m "sync: $(date '+%Y-%m-%d %H:%M:%S')" --no-verify
git push origin main
