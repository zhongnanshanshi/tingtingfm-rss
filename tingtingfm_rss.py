#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
听听FM 节目 -> Podcast RSS 生成器

用法:
    python3 tingtingfm_rss.py VkZorENdE7                 # 生成 feed.xml + data.json
    python3 tingtingfm_rss.py VkZorENdE7 --full          # 抓取全部历史剧集(默认也是全量)
    python3 tingtingfm_rss.py VkZorENdE7 --limit 100     # 只保留最近 100 期

原理:
    api-v3.tingtingfm.com 的请求需要一个 api_sign = md5(排序后的query + "_" + secret)。
    secret 硬编码在 mobile.tingtingfm.com/main.bundle.js 里，可随前端版本变化；
    如果某天接口开始报 "请求参数sign错误"，重新从 bundle 里提取 secret 即可(见 SECRET 注释)。
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from typing import List, Optional
from xml.sax.saxutils import escape

API = "https://api-v3.tingtingfm.com"
VERSION = "h5_6.6.3.4"
CLIENT = "h5_YIidkdCDk4PMSHyqmTM4GYoALLUQCY"
SECRET = "1Ftjv0bfpVmqbE38"
CST = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"


# ---------- 签名 ----------
def _sign(params: dict) -> str:
    parts = [f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items()]
    raw = "&".join(sorted(parts)) + "_" + SECRET
    return hashlib.md5(raw.encode()).hexdigest()


def call(path: str, extra: dict, tries: int = 3) -> dict:
    last = None
    for i in range(tries):
        p = {"version": VERSION, "client": CLIENT}
        p.update(extra)
        p["api_sign"] = _sign(p)
        url = API + path + "?" + urllib.parse.urlencode(p)
        req = urllib.request.Request(url, data=b"", headers={"User-Agent": UA})
        try:
            body = json.loads(urllib.request.urlopen(req, timeout=25).read())
            if body.get("errno") != 0:
                raise RuntimeError(f"接口错误 {body.get('errno')}: {body.get('error')}")
            return body["data"]
        except Exception as e:  # 有界重试
            last = e
            time.sleep(1 + i)
    raise RuntimeError(f"{path} 请求失败: {last}")


# ---------- 抓取 ----------
def program_info(program_id: str) -> dict:
    return call("/broadcast/get_program_v3_8", {"h_program_id": program_id})["info"]


def first_audio_id(program_id: str) -> str:
    return call("/broadcast/get_program_audio_list", {"h_program_id": program_id})[0]["h_audio_id"]


def fetch_episodes(program_id: str, max_pages: int = 60) -> list:
    """以 audio_id 为滑动窗口锚点，每次前移 50 条，抓取该节目全部剧集。"""
    anchor = first_audio_id(program_id)
    seen = {}
    order = []
    window = 100
    for page in range(max_pages):
        data = call("/albumaudio/play_audio", {"type": 2, "sort": -1, "audio_id": anchor})
        lst = data.get("list") or []
        new = 0
        for it in lst:
            aid = it["h_audio_id"]
            if aid not in seen:
                seen[aid] = it
                order.append(aid)
                new += 1
        print(f"  第 {page + 1} 页: 返回 {len(lst)} 条, 新增 {new} 条, 累计 {len(seen)} 期", file=sys.stderr)
        if new == 0 or len(lst) < window:
            break
        anchor = lst[-1]["h_audio_id"]
    return [seen[i] for i in order]


# ---------- RSS ----------
def build_rss(program: dict, episodes: list, feed_url: str, limit: Optional[int]) -> str:
    eps = sorted(episodes, key=lambda x: int(x.get("add_time") or 0), reverse=True)
    if limit:
        eps = eps[:limit]

    title = program["title"]
    desc = program.get("description") or ""
    cover = program.get("cover") or ""
    radio = program.get("belong_radio") or ""
    anchor = "、".join(program.get("anchor") or [])
    page_url = f"https://mobile.tingtingfm.com/v3/program/{program['h_program_id']}"

    items = []
    for e in eps:
        ts = int(e.get("add_time") or 0)
        dt = datetime.fromtimestamp(ts, CST)
        dur = int(e.get("duration") or 0)
        items.append(
            """    <item>
      <title>{title}</title>
      <description>{title}</description>
      <guid isPermaLink="false">ttfm-{guid}</guid>
      <pubDate>{pub}</pubDate>
      <enclosure url="{url}" type="audio/mp4" length="0"/>
      <itunes:duration>{dur_hms}</itunes:duration>
      <link>{link}</link>
    </item>""".format(
                title=escape(e["title"]),
                guid=e["h_audio_id"],
                pub=format_datetime(dt),
                url=escape(e.get("play_url") or "", {'"': "&quot;"}),
                dur_hms=f"{dur // 3600:02d}:{dur % 3600 // 60:02d}:{dur % 60:02d}",
                link=f"https://mobile.tingtingfm.com/v3/vod/2/{e['h_audio_id']}",
            )
        )

    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{title}</title>
    <link>{page_url}</link>
    <language>zh-cn</language>
    <description>{desc}</description>
    <itunes:author>{anchor}</itunes:author>
    <itunes:summary>{desc}</itunes:summary>
    <itunes:image href="{cover}"/>
    <itunes:category text="News"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:owner><itunes:name>{anchor}</itunes:name></itunes:owner>
    <lastBuildDate>{build}</lastBuildDate>
    <generator>tingtingfm-rss</generator>
{items}
  </channel>
</rss>
""".format(
        title=escape(f"{title} - {radio}" if radio else title),
        page_url=page_url,
        desc=escape(desc),
        anchor=escape(anchor or radio),
        cover=escape(cover, {'"': "&quot;"}),
        build=format_datetime(datetime.now(CST)),
        items="\n".join(items),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("program_id", help="节目 ID，例如 VkZorENdE7")
    ap.add_argument("-o", "--out", default="feed.xml")
    ap.add_argument("--json", default="data.json")
    ap.add_argument("--limit", type=int, default=None, help="只输出最近 N 期")
    ap.add_argument("--feed-url", default="", help="RSS 自身的公网地址(可选)")
    args = ap.parse_args()

    print("拉取节目信息…", file=sys.stderr)
    prog = program_info(args.program_id)
    prog["h_program_id"] = args.program_id
    print(f"  {prog['title']} / {prog.get('belong_radio')} / 共 {prog.get('audio_num')} 期", file=sys.stderr)

    print("抓取剧集列表…", file=sys.stderr)
    eps = fetch_episodes(args.program_id)
    print(f"共抓到 {len(eps)} 期", file=sys.stderr)

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump({"program": prog, "episodes": eps, "fetched_at": int(time.time())}, f, ensure_ascii=False, indent=1)

    xml = build_rss(prog, eps, args.feed_url, args.limit)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"已生成 {args.out} ({len(xml)} 字节, {len(eps) if not args.limit else min(len(eps), args.limit)} 期)", file=sys.stderr)


if __name__ == "__main__":
    main()
