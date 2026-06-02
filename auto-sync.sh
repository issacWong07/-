#!/bin/bash
# Claude 工作空间自动同步脚本（支持上传后自动清理）
# 模式说明：
#   默认模式：仅同步，不删除本地文件
#   清理模式：同步后停止跟踪并删除本地用户文件（保留仓库基础设施）

REPO_DIR="$HOME/claude-sync-workspace"
cd "$REPO_DIR" || exit 0

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# 获取环境变量控制是否清理（CLaude 调用时默认不清理，手动调用可设置 CLEANUP=1）
CLEANUP_MODE="${CLEANUP:-0}"

# 关键基础设施文件（永不删除）
CRITICAL_FILES=(".gitignore" "auto-sync.sh" "README.md" "cleanup.sh")

is_critical() {
    local target="$1"
    for f in "${CRITICAL_FILES[@]}"; do
        if [ "$target" = "$f" ]; then
            return 0
        fi
    done
    return 1
}

# ---------- 1. 暂存所有变更 ----------
git add -A
if git diff --cached --quiet; then
    echo "[auto-sync] 没有变更，跳过"
    exit 0
fi

# 获取被暂存的文件列表
STAGED_FILES=$(git diff --cached --name-only)

# ---------- 2. 提交并推送 ----------
git commit -m "sync: $(date '+%Y-%m-%d %H:%M:%S')" --no-verify
git push origin main
echo "[auto-sync] 已推送到 GitHub"

# ---------- 3. 清理模式：停止跟踪 + 删除本地文件 ----------
if [ "$CLEANUP_MODE" = "1" ]; then
    echo "[auto-sync] 清理模式：上传后删除本地文件..."

    UPLOADED_FILES=""
    echo "$STAGED_FILES" | while read -r file; do
        [ -z "$file" ] && continue
        is_critical "$file" && continue

        if [ -f "$file" ]; then
            # 停止 git 跟踪（保留历史版本在 GitHub）
            git rm --cached "$file" > /dev/null 2>&1
            # 删除本地文件
            rm -f "$file"
            UPLOADED_FILES="$UPLOADED_FILES$file\n"
            echo "  ✓ 已清理: $file"
        fi
    done

    # 把清理的文件加入 .gitignore，防止下次同步时冲突
    echo "$STAGED_FILES" | while read -r file; do
        [ -z "$file" ] && continue
        is_critical "$file" && continue
        if ! grep -qxF "$file" .gitignore 2>/dev/null; then
            echo "$file" >> .gitignore
        fi
    done

    # 提交 .gitignore 更新（让 git 永久忽略这些文件路径）
    git add .gitignore
    if ! git diff --cached --quiet; then
        git commit -m "chore: cleanup uploaded files and update .gitignore" --no-verify
        git push origin main
        echo "[auto-sync] 清理完成，GitHub 保留历史版本"
    fi

    # 删除空目录
    find . -type d -not -path './.git/*' -empty -delete 2>/dev/null
fi
