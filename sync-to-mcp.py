#!/usr/bin/env python3
"""
工作空间 → evolving-knowledge-mcp 同步脚本

将 工作/待归档/ 目录下的文件索引到 evolving-knowledge-mcp 知识库。

用法：
    python3 sync-to-mcp.py [待归档目录路径]

返回 JSON 到 stdout：
    {
        "scanned": 扫描文件数,
        "indexed": 成功索引数,
        "duplicates": 重复跳过数,
        "errors": 错误数,
        "details": [...]
    }
"""

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
        if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
            log(f"跳过不支持的文件类型: {item}")
            continue
        files.append(item)

    # 按路径排序，保证输出稳定
    files.sort()
    return files


def index_file(file_path: Path) -> dict:
    """索引单个文件到 evolving-knowledge-mcp 知识库"""
    from knowledge_base.store import 添加文档

    result = 添加文档(str(file_path), 标签=DEFAULT_TAGS)
    return result


def main() -> int:
    archive_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "工作" / "待归档"

    report = {
        "archive_dir": str(archive_dir),
        "scanned": 0,
        "indexed": 0,
        "duplicates": 0,
        "errors": 0,
        "details": [],
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
