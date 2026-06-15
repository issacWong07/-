#!/bin/bash
# 手动清理脚本：停止跟踪已上传文件并删除本地副本
# 用法：bash cleanup.sh

cd "$HOME/工作" || exit 1

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "错误：不是 git 仓库"
    exit 1
fi

# 关键基础设施文件（永不删除）
CRITICAL="^(\.gitignore|auto-sync\.sh|README\.md|cleanup\.sh|sync-to-mcp\.py)$"

# 获取所有已跟踪的非关键文件
TRACKED_FILES=$(git ls-files | grep -v -E "$CRITICAL")

if [ -z "$TRACKED_FILES" ]; then
    echo "✅ 没有需要清理的文件"
    exit 0
fi

echo "以下文件将被停止跟踪并删除本地副本："
echo "$TRACKED_FILES" | sed 's/^/  - /'
echo ""
read -p "确认清理？(y/N) " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # 使用 process substitution 避免子 shell 问题
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            git rm --cached "$file" > /dev/null 2>&1
            rm -f "$file"
            echo "  ✓ 已清理: $file"
        fi
    done <<< "$TRACKED_FILES"

    # 更新 .gitignore
    while IFS= read -r file; do
        if ! grep -qxF "$file" .gitignore 2>/dev/null; then
            echo "$file" >> .gitignore
        fi
    done <<< "$TRACKED_FILES"

    # 暂存所有变更（包括 git rm --cached 产生的删除）
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "chore: manual cleanup uploaded files" --no-verify
        git push origin main
    fi

    find . -type d -not -path './.git/*' -empty -delete 2>/dev/null
    echo ""
    echo "✅ 清理完成，GitHub 仍保留文件历史版本"
else
    echo "已取消"
fi
