#!/bin/bash
# Claude 工作空间自动同步脚本（单次 push + MCP 精细化清理）
# 模式说明：
#   默认模式：仅同步，不删除本地文件
#   清理模式：同步后停止跟踪并删除本地用户文件（保留仓库基础设施）

REPO_DIR="$HOME/工作"
cd "$REPO_DIR" || exit 0

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# 关键基础设施文件（永不删除）
CRITICAL_FILES=(".gitignore" "auto-sync.sh" "README.md" "cleanup.sh" "sync-to-mcp.py")

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

# ---------- 2. 提交主变更（暂不 push） ----------
git commit -m "sync: $(date '+%Y-%m-%d %H:%M:%S')" --no-verify
echo "[auto-sync] 已提交主变更"

# ---------- 3. 同步 待归档 到 evolving-knowledge-mcp 并精细化清理 ----------
ARCHIVE_DIR="待归档"
SYNC_SCRIPT="$REPO_DIR/sync-to-mcp.py"
if [ -f "$SYNC_SCRIPT" ] && [ -d "$ARCHIVE_DIR" ]; then
    echo "[auto-sync] 同步待归档文件到 evolving-knowledge-mcp..."
    if python3 "$SYNC_SCRIPT" --cleanup "$ARCHIVE_DIR"; then
        echo "[auto-sync] MCP 索引与精细化清理完成"
    else
        echo "[auto-sync] ⚠️ MCP 索引失败，已提交的主变更未 push，待归档文件保留本地供重试"
        exit 0
    fi
fi

# ---------- 4. 提交清理变更（如有） ----------
git add -A
if ! git diff --cached --quiet; then
    git commit -m "chore: auto cleanup 待归档 files after sync" --no-verify
    echo "[auto-sync] 已提交清理变更"
fi

# ---------- 5. 统一 push 到 GitHub ----------
git push origin main
echo "[auto-sync] 已推送到 GitHub"
