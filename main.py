"""CLI 入口：argparse 子命令"""

import os
import sys
import argparse
from collections import defaultdict
from tqdm import tqdm

from config import DEFAULT_PLAYLIST_NAME, REPORT_FILE, DOWNLOADS_DIR
from auth import ensure_login, qrcode_login, check_login
from excel_handler import generate_template, read_song_list, generate_report
from search import batch_search
from downloader import download_song
from playlist_manager import batch_create_playlists
from progress_tracker import ProgressTracker


def cmd_template(args):
    """生成 Excel 模板"""
    output = args.output if args.output else None
    path = generate_template(output)
    print(f"模板已生成: {os.path.abspath(path)}")


def cmd_login(args):
    """登录"""
    if qrcode_login():
        print("登录成功，会话已缓存")
    else:
        print("登录失败")
        sys.exit(1)


def cmd_report(args):
    """查看进度报告"""
    tracker = ProgressTracker(args.task_id if hasattr(args, 'task_id') and args.task_id else "default")
    s = tracker.summary()
    print(f"进度报告 (任务: {tracker.task_id})")
    print(f"  总歌曲数:   {s['total']}")
    print(f"  已搜索:     {s['searched']}")
    print(f"  搜索到:     {s['found']}")
    print(f"  未找到:     {s['not_found']}")
    print(f"  已下载:     {s['downloaded']}")
    print(f"  已建歌单:   {s['playlists_created']}")


def cmd_run(args):
    """完整流程：搜索 + 下载 + 建歌单"""
    input_file = args.input
    no_download = args.no_download
    no_playlist = args.no_playlist
    resume = args.resume
    bitrate = args.bitrate

    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"文件不存在: {input_file}")
        sys.exit(1)

    # 登录
    print("=" * 50)
    print("步骤 1: 登录")
    print("=" * 50)
    if not ensure_login():
        print("登录失败，请重试")
        sys.exit(1)

    # 读取歌曲列表
    print("\n" + "=" * 50)
    print("步骤 2: 读取歌曲列表")
    print("=" * 50)
    songs = read_song_list(input_file)
    print(f"读取到 {len(songs)} 首歌曲")
    if not songs:
        print("歌曲列表为空")
        sys.exit(1)

    # 初始化进度跟踪
    task_id = os.path.splitext(os.path.basename(input_file))[0]
    tracker = ProgressTracker(task_id)
    if not resume:
        tracker.clear()
    tracker.set_total(len(songs))

    # 搜索歌曲
    print("\n" + "=" * 50)
    print("步骤 3: 搜索歌曲")
    print("=" * 50)

    pbar = tqdm(total=len(songs), desc="搜索进度", unit="首")
    found_count = 0
    not_found_count = 0

    def on_search_progress(idx, total, result):
        nonlocal found_count, not_found_count
        pbar.update(1)
        if result:
            found_count += 1
        else:
            not_found_count += 1

    search_results = batch_search(songs, tracker=tracker, on_progress=on_search_progress)
    pbar.close()

    print(f"\n搜索完成: 找到 {found_count} 首, 未找到 {not_found_count} 首")

    # 未找到的歌曲列表
    not_found_songs = [r for r in search_results if r["result"] is None]
    if not_found_songs:
        print("\n未找到的歌曲:")
        for r in not_found_songs[:20]:
            inp = r["input"]
            print(f"  - {inp['name']}" + (f" ({inp['artist']})" if inp.get('artist') else ""))
        if len(not_found_songs) > 20:
            print(f"  ... 还有 {len(not_found_songs) - 20} 首")

    # 下载歌曲
    if not no_download:
        print("\n" + "=" * 50)
        print("步骤 4: 下载歌曲")
        print("=" * 50)

        to_download = [r for r in search_results if r["result"] is not None]
        pbar = tqdm(total=len(to_download), desc="下载进度", unit="首")
        download_success = 0
        download_fail = 0

        for r in to_download:
            song_id = r["result"]["song_id"]
            category = r["input"].get("category", "")

            # 断点续下
            if tracker.is_downloaded(song_id):
                pbar.update(1)
                download_success += 1
                continue

            try:
                file_path = download_song(song_id, category=category, bitrate=bitrate)
                if file_path:
                    tracker.mark_downloaded(song_id, file_path)
                    download_success += 1
                else:
                    download_fail += 1
            except Exception as e:
                tqdm.write(f"  下载失败 [{r['result']['name']}]: {e}")
                download_fail += 1

            pbar.update(1)

        pbar.close()
        print(f"\n下载完成: 成功 {download_success} 首, 失败 {download_fail} 首")

    # 创建歌单
    if not no_playlist:
        print("\n" + "=" * 50)
        print("步骤 5: 创建歌单")
        print("=" * 50)

        # 按分类分组
        songs_by_category = defaultdict(list)
        for r in search_results:
            if r["result"] is None:
                continue
            category = r["input"].get("category", "") or DEFAULT_PLAYLIST_NAME
            songs_by_category[category].append(r["result"]["song_id"])

        if songs_by_category:
            created = batch_create_playlists(songs_by_category, tracker=tracker)
            print(f"\n歌单创建完成: 共 {len(created)} 个歌单")
        else:
            print("没有可添加到歌单的歌曲")

    # 生成报告
    print("\n" + "=" * 50)
    print("步骤 6: 生成报告")
    print("=" * 50)

    report_data = []
    for r in search_results:
        inp = r["input"]
        res = r["result"]
        entry = {
            "input_name": inp["name"],
            "input_artist": inp.get("artist", ""),
            "category": inp.get("category", ""),
        }
        if res:
            entry["matched_name"] = res.get("name", "")
            entry["matched_artist"] = res.get("artist", "")
            entry["matched_album"] = res.get("album", "")
            song_id = res["song_id"]
            if tracker.is_downloaded(song_id):
                entry["status"] = "下载成功"
                entry["file_path"] = tracker.get_download_path(song_id) or ""
            elif no_download:
                entry["status"] = "已匹配(未下载)"
            else:
                entry["status"] = "下载失败"
            entry["note"] = f"匹配度: {res.get('score', 0)}"
        else:
            entry["matched_name"] = ""
            entry["matched_artist"] = ""
            entry["matched_album"] = ""
            entry["status"] = "未找到"
            entry["file_path"] = ""
            entry["note"] = inp.get("note", "")

        report_data.append(entry)

    report_path = generate_report(report_data, REPORT_FILE)
    print(f"报告已生成: {os.path.abspath(report_path)}")

    # 最终汇总
    s = tracker.summary()
    print("\n" + "=" * 50)
    print("任务完成!")
    print(f"  总歌曲: {s['total']} | 找到: {s['found']} | 未找到: {s['not_found']}")
    print(f"  已下载: {s['downloaded']} | 歌单: {s['playlists_created']}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="网易云音乐批量下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py template                     生成 Excel 模板
  python main.py login                        登录并保存会话
  python main.py run songs.xlsx               完整流程
  python main.py run songs.xlsx --no-download  仅搜索+建歌单
  python main.py run songs.xlsx --no-playlist  仅搜索+下载
  python main.py run songs.xlsx --resume       断点续传
  python main.py report                        查看进度
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # template
    p_template = subparsers.add_parser("template", help="生成 Excel 模板")
    p_template.add_argument("-o", "--output", help="输出路径")
    p_template.set_defaults(func=cmd_template)

    # login
    p_login = subparsers.add_parser("login", help="登录网易云音乐")
    p_login.set_defaults(func=cmd_login)

    # run
    p_run = subparsers.add_parser("run", help="执行批量搜索/下载/建歌单")
    p_run.add_argument("input", help="输入文件路径 (xlsx/csv)")
    p_run.add_argument("--no-download", action="store_true", help="不下载，仅搜索+建歌单")
    p_run.add_argument("--no-playlist", action="store_true", help="不建歌单，仅搜索+下载")
    p_run.add_argument("--resume", action="store_true", help="断点续传")
    p_run.add_argument("--bitrate", type=int, default=320000,
                       choices=[128000, 192000, 320000, 999000],
                       help="音质: 128000(标准) 192000(高品) 320000(极高) 999000(无损), 默认320000")
    p_run.set_defaults(func=cmd_run)

    # report
    p_report = subparsers.add_parser("report", help="查看进度报告")
    p_report.add_argument("--task-id", default="default", help="任务 ID")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
