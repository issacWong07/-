#!/usr/bin/env python3
"""
工作空间 → evolving-knowledge-mcp 同步脚本

将 工作/待归档/ 目录下的文件索引到 evolving-knowledge-mcp 知识库。

用法：
    python3 sync-to-mcp.py [待归档目录路径] [--cleanup]

参数：
    --cleanup       同步后清理已成功索引/重复/不支持的本地文件
    --repo-dir      工作空间仓库根目录（默认 ~/工作）

返回 JSON 到 stdout：
    {
        "scanned": 扫描文件数,
        "indexed": 成功索引数,
        "duplicates": 重复跳过数,
        "unsupported": 不支持文件数,
        "errors": 错误数,
        "details": [...],
        "cleaned": [已清理文件路径列表]
    }
"""

import argparse
import json
import os
import sys
from pathlib import Path

# evolving-knowledge-mcp 项目根目录
MCP_ROOT = Path.home() / "evolving-knowledge-mcp"
MCP_VENV_PYTHON = MCP_ROOT / "venv" / "bin" / "python"

# 将 MCP 项目加入 Python 路径
sys.path.insert(0, str(MCP_ROOT))

# 支持的文件扩展名（与 evolving-knowledge-mcp parser 保持一致）
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json",
    ".csv", ".yaml", ".yml", ".pdf", ".docx", ".doc",
    ".xlsx", ".xls", ".pptx", ".ppt", ".html", ".htm",
}

# 默认标签
DEFAULT_TAGS = "workspace,待归档"


def log(message: str) -> None:
    """打印同步日志到 stderr，避免污染 stdout JSON 输出"""
    print(f"[sync-to-mcp] {message}", file=sys.stderr)


def ensure_mcp_environment() -> None:
    """校验 MCP 环境是否就绪，并在必要时用 MCP 虚拟环境重新执行"""
    if not MCP_ROOT.exists():
        raise FileNotFoundError(f"MCP 项目目录不存在: {MCP_ROOT}")
    if not MCP_VENV_PYTHON.exists():
        raise FileNotFoundError(f"MCP 虚拟环境 Python 不存在: {MCP_VENV_PYTHON}")

    # 如果当前不是 MCP 虚拟环境 Python，则重新执行
    # 注意：venv 的 python 通常是系统 python 的符号链接，所以不能用 realpath/resolve 比较目标文件
    current_python = Path(sys.executable)
    expected_python = MCP_VENV_PYTHON
    if current_python != expected_python:
        log(f"切换到 MCP 虚拟环境 Python: {expected_python}")
        os.execv(str(expected_python), [str(expected_python), str(__file__)] + sys.argv[1:])


def scan_archive_files(archive_dir: Path) -> list[Path]:
    """扫描待归档目录下的所有支持文件（不包含 .git 等隐藏目录）"""
    files = []
    if not archive_dir.exists():
        return files

    for item in archive_dir.rglob("*"):
        if not item.is_file():
            continue
        # 跳过隐藏文件和目录
        if any(part.startswith(".") for part in item.relative_to(archive_dir).parts):
            continue
        files.append(item)

    # 按路径排序，保证输出稳定
    files.sort()
    return files


def cleanup_files(archive_dir: Path, details: list[dict], repo_dir: Path = None) -> list[str]:
    """清理已成功索引、重复或不支持索引的文件，返回已清理文件列表

    只清理状态为 indexed/duplicate/unsupported 的文件，error 状态文件保留供重试。
    """
    if repo_dir is None:
        repo_dir = Path.home() / "工作"

    gitignore_path = repo_dir / ".gitignore"
    cleaned = []

    for detail in details:
        status = detail.get("status")
        file_str = detail.get("file")
        if not file_str:
            continue
        if status not in ("indexed", "duplicate", "unsupported"):
            log(f"保留未成功文件: {file_str}")
            continue

        file_path = Path(file_str)
        if not file_path.is_absolute():
            file_path = repo_dir / file_path

        if not file_path.exists():
            continue

        try:
            file_path.unlink()
            cleaned.append(str(file_path))
            log(f"已清理本地文件: {file_path}")

            # 计算相对于仓库根目录的路径，用于 .gitignore
            try:
                rel_path = file_path.relative_to(repo_dir)
                rel_path_str = str(rel_path)
                if gitignore_path.exists():
                    existing = gitignore_path.read_text(encoding="utf-8").splitlines()
                    if rel_path_str not in existing:
                        with open(gitignore_path, "a", encoding="utf-8") as f:
                            f.write(f"{rel_path_str}\n")
                        log(f"已加入 .gitignore: {rel_path_str}")
                else:
                    gitignore_path.write_text(f"{rel_path_str}\n", encoding="utf-8")
            except ValueError:
                log(f"文件不在仓库内，跳过 .gitignore: {file_path}")
        except Exception as e:
            log(f"清理失败: {file_path} - {e}")

    # 删除空目录
    if archive_dir.exists():
        for subdir in sorted(archive_dir.rglob("*"), reverse=True):
            if subdir.is_dir() and not any(subdir.iterdir()):
                try:
                    subdir.rmdir()
                    log(f"已删除空目录: {subdir}")
                except Exception:
                    pass
        try:
            archive_dir.rmdir()
        except Exception:
            pass

    return cleaned


def index_file(file_path: Path) -> dict:
    """索引单个文件到 evolving-knowledge-mcp 知识库"""
    from knowledge_base.store import 添加文档

    result = 添加文档(str(file_path), 标签=DEFAULT_TAGS)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="同步工作空间归档文件到 evolving-knowledge-mcp")
    parser.add_argument("archive_dir", nargs="?", default=str(Path.home() / "工作" / "待归档"), help="待归档目录路径")
    parser.add_argument("--cleanup", action="store_true", help="同步后清理已成功索引/重复/不支持的本地文件")
    parser.add_argument("--repo-dir", default=str(Path.home() / "工作"), help="工作空间仓库根目录")
    args = parser.parse_args()

    archive_dir = Path(args.archive_dir)
    repo_dir = Path(args.repo_dir)

    report = {
        "archive_dir": str(archive_dir),
        "scanned": 0,
        "indexed": 0,
        "duplicates": 0,
        "unsupported": 0,
        "errors": 0,
        "details": [],
        "cleaned": [],
    }

    try:
        ensure_mcp_environment()
        files = scan_archive_files(archive_dir)
        report["scanned"] = len(files)

        if not files:
            log("待归档目录为空或没有支持的文件")
            print(json.dumps(report, ensure_ascii=False))
            return 0

        for file_path in files:
            detail = {
                "file": str(file_path),
                "status": "pending",
                "result": None,
            }

            # 检查文件类型
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                detail["status"] = "unsupported"
                detail["result"] = {"message": f"不支持的文件类型: {file_path.suffix}"}
                report["unsupported"] += 1
                log(f"跳过不支持的文件类型: {file_path}")
                report["details"].append(detail)
                continue

            try:
                result = index_file(file_path)
                detail["result"] = result

                if result.get("success"):
                    detail["status"] = "indexed"
                    report["indexed"] += 1
                    log(f"已索引: {file_path} (doc_id={result.get('doc_id')}, chunks={result.get('chunks')})")
                elif "已存在" in result.get("error", ""):
                    detail["status"] = "duplicate"
                    report["duplicates"] += 1
                    log(f"重复跳过: {file_path}")
                else:
                    detail["status"] = "error"
                    report["errors"] += 1
                    log(f"索引失败: {file_path} - {result.get('error')}")
            except Exception as e:
                detail["status"] = "error"
                detail["result"] = {"error": str(e)}
                report["errors"] += 1
                log(f"索引异常: {file_path} - {e}")

            report["details"].append(detail)

        if args.cleanup:
            report["cleaned"] = cleanup_files(archive_dir, report["details"], repo_dir)

    except Exception as e:
        report["errors"] += 1
        report["details"].append({
            "file": None,
            "status": "fatal_error",
            "result": {"error": str(e)},
        })
        log(f"致命错误: {e}")
        print(json.dumps(report, ensure_ascii=False))
        return 1

    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
