"""Batch processing script: iterate all operator .md files and call the upload API."""

import argparse
import sys
import time
from pathlib import Path

import requests

# ─── 配置 ──────────────────────────────────────────────────────
DEFAULT_OPERATORS_DIR = "operators/nn"
DEFAULT_API_BASE = "http://127.0.0.1:8000"
UPLOAD_ENDPOINT = "/api/v1/upload"


# ────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="批量调用算子文档解析接口")
    p.add_argument(
        "-d", "--dir",
        default=DEFAULT_OPERATORS_DIR,
        help=f"算子文件目录 (默认: {DEFAULT_OPERATORS_DIR})",
    )
    p.add_argument(
        "-u", "--url",
        default=DEFAULT_API_BASE,
        help=f"API 地址 (默认: {DEFAULT_API_BASE})",
    )
    p.add_argument(
        "-s", "--search",
        default="",
        help="按文件名过滤 (模糊匹配)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只列出文件，不实际调用 API",
    )
    return p.parse_args()


def collect_files(ops_dir: Path, search: str) -> list[Path]:
    """递归扫描目录下所有 .md 文件，可选按名称过滤。"""
    files = sorted(ops_dir.rglob("*.md"))
    if search:
        keyword = search.lower()
        files = [f for f in files if keyword in f.stem.lower()]
    return files


def upload_one(api_url: str, file_path: Path) -> dict:
    """上传单个文件到解析接口，返回响应 JSON。"""
    url = f"{api_url}{UPLOAD_ENDPOINT}"
    with open(file_path, "rb") as fh:
        files = {"file": (file_path.name, fh, "text/markdown")}
        resp = requests.post(url, files=files, timeout=600)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    args = parse_args()
    ops_dir = Path(args.dir)

    if not ops_dir.exists():
        print(f"❌ 目录不存在: {ops_dir}")
        sys.exit(1)

    files = collect_files(ops_dir, args.search)
    total = len(files)
    print(f"📂 目录: {ops_dir}")
    print(f"📄 共扫描到 {total} 个 .md 文件")
    if args.search:
        print(f"🔍 过滤关键字: {args.search}")
    print()

    if total == 0:
        print("没有匹配的文件，退出。")
        return

    if args.dry_run:
        for i, f in enumerate(files, 1):
            rel = f.relative_to(ops_dir.parent)
            print(f"  {i:>4}. {rel}")
        print(f"\n--dry-run 模式，不实际调用 API。")
        return

    # ─── 批量调用 ──────────────────────────────────────────────
    success_count = 0
    unchanged_count = 0
    fail_count = 0
    failed_list: list[tuple[Path, str]] = []
    start_time = time.time()

    for i, f in enumerate(files, 1):
        rel = f.relative_to(ops_dir.parent)
        print(f"[{i:>4}/{total}] {rel} ... ", end="", flush=True)

        t0 = time.time()
        try:
            data = upload_one(args.url, f)
            elapsed = time.time() - t0

            if data.get("success"):
                status = data.get("status", "new")
                op_name = data.get("operator_name", "?")
                ver = data.get("version", "-")
                if status == "unchanged":
                    unchanged_count += 1
                    print(f"⏭  unchanged ({op_name}, {elapsed:.1f}s)")
                else:
                    success_count += 1
                    print(f"✅ {status} ({op_name} v{ver}, {elapsed:.1f}s)")
            else:
                fail_count += 1
                err = data.get("error", "未知错误")
                failed_list.append((rel, err))
                print(f"❌ {err} ({elapsed:.1f}s)")

        except requests.exceptions.ConnectionError:
            fail_count += 1
            failed_list.append((rel, "连接失败，请确认服务已启动"))
            print(f"❌ 连接失败")
            # 后续大概率也会失败，提前退出
            print("\n⚠️  服务连接失败，停止后续请求。请先启动服务：")
            print(f"   uvicorn agent.main:create_app --factory --reload")
            break
        except Exception as e:
            fail_count += 1
            failed_list.append((rel, str(e)))
            print(f"❌ {e}")

    # ─── 汇总 ──────────────────────────────────────────────────
    total_time = time.time() - start_time
    print()
    print("=" * 60)
    print(f"📊 执行完毕  耗时: {total_time:.1f}s")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ⏭  未变: {unchanged_count}")
    print(f"   ❌ 失败: {fail_count}")
    print(f"   总计: {total}")

    if failed_list:
        print(f"\n❌ 失败详情:")
        for path, err in failed_list:
            print(f"   {path}: {err}")


if __name__ == "__main__":
    main()
