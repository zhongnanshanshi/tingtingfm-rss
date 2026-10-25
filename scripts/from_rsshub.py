#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从公共 RSSHub 实例拉取听听FM 节目，重新生成本仓库的 feed.xml。

为什么走这条路：api-v3.tingtingfm.com 对海外 IP（含 GitHub Actions 的
Azure runner）一律返回 405，Actions 无法直连。而部分 RSSHub 公共实例位于
香港等地，出口可正常访问 tingtingfm，于是用它当中转。

用法:
    python3 scripts/from_rsshub.py VkZorENdE7 --out feed.xml
"""

import argparse
import os
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tingtingfm_rss import build_rss  # noqa: E402

CST = timezone(timedelta(hours=8))
NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
}

# 公共 RSSHub 实例，按可用性依次尝试
INSTANCES = [
    "https://rsshub.umzzz.com",
    "https://rsshub.email-once.com",
    "https://rsshub.rssforever.com",
    "https://rsshub.cups.moe",
    "https://rsshub.isrss.com",
    "https://rsshub.app",
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch(program_id, tries_per_instance=2):
    """用 curl 下载：比 urllib 稳（chunked 传输 + 代理环境下 urllib 常被截断）。"""
    path = f"/tingtingfm/program/{program_id}"
    errors = []
    tmp = "/tmp/.rsshub_feed.xml"
    for base in INSTANCES:
        for attempt in range(tries_per_instance):
            try:
                r = subprocess.run(
                    [
                        "curl", "-sSL", "--compressed", "--fail",
                        "--retry", "2", "--retry-delay", "3",
                        "--max-time", "120",
                        "-A", UA,
                        "-o", tmp,
                        base + path,
                    ],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    raise RuntimeError(f"curl exit {r.returncode}: {(r.stderr or '').strip()[:160]}")
                raw = open(tmp, "rb").read()
                if b"<item>" not in raw:
                    raise RuntimeError(f"返回内容不是 feed（{len(raw)} 字节）")
                print(f"  成功：{base}（{len(raw)} 字节）", file=sys.stderr)
                return raw
            except Exception as e:
                errors.append(f"{base} -> {e}")
                print(f"  {base} 第 {attempt + 1} 次失败: {e}", file=sys.stderr)
                time.sleep(3)
    raise RuntimeError("所有 RSSHub 实例都失败:\n" + "\n".join(errors))


def hms_to_seconds(s):
    if not s:
        return 0
    parts = [int(x) for x in str(s).split(":") if x.isdigit() or x == "0"]
    while len(parts) < 3:
        parts.insert(0, 0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def parse(raw, program_id):
    root = ET.fromstring(raw)
    ch = root.find("channel")
    img = ch.find("itunes:image", NS)
    cover = img.get("href") if img is not None else ""
    title = (ch.findtext("title") or "").strip()

    program = {
        "h_program_id": program_id,
        "title": title.split(" - ")[0] or title,
        "belong_radio": title.split(" - ")[1] if " - " in title else "",
        "description": re.sub(r"\s*-\s*Powered by RSSHub\s*$", "", (ch.findtext("description") or "").strip()),
        "cover": cover,
        "anchor": [],
        "audio_num": 0,
    }

    episodes = []
    for it in ch.findall("item"):
        link = (it.findtext("link") or "").strip()
        audio_id = link.rstrip("/").split("/")[-1] if link else ""
        enc = it.find("enclosure")
        url = enc.get("url") if enc is not None else ""
        if not (audio_id and url):
            continue
        pub = it.findtext("pubDate") or ""
        ts = 0
        if pub:
            try:
                from email.utils import parsedate_to_datetime

                ts = int(parsedate_to_datetime(pub).timestamp())
            except Exception:
                ts = 0
        episodes.append(
            {
                "h_audio_id": audio_id,
                "title": (it.findtext("title") or "").strip(),
                "duration": hms_to_seconds(it.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration") or ""),
                "add_time": str(ts),
                "play_url": url,
            }
        )
    return program, episodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("program_id")
    ap.add_argument("-o", "--out", default="feed.xml")
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    raw = fetch(args.program_id)
    program, episodes = parse(raw, args.program_id)
    print(f"解析到 {len(episodes)} 期，节目：《{program['title']}》", file=sys.stderr)
    if len(episodes) < 5:
        raise SystemExit(f"剧集太少（{len(episodes)}），判定为异常，保留旧 feed")

    xml = build_rss(program, episodes, "", args.limit)
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(xml)
    os.replace(tmp, args.out)
    print(f"已生成 {args.out}（{len(xml)} 字节）", file=sys.stderr)


if __name__ == "__main__":
    main()
