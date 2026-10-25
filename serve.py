#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
听听FM 节目 -> 本地 Podcast RSS 服务

启动:
    python3 serve.py VkZorENdE7

然后播客客户端订阅:
    http://<本机局域网IP>:8787/feed.xml

特性:
  - 后台线程每 N 小时重新抓一次，刷新 enclosure 里 10 天有效的 auth_key
  - /feed.xml   返回 RSS
  - /data.json  返回原始剧集数据
  - /           显示订阅地址与状态
"""

import json
import os
import socketserver
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tingtingfm_rss as tt  # noqa: E402

PORT = int(os.environ.get("PORT", "8787"))
REFRESH_HOURS = float(os.environ.get("REFRESH_HOURS", "6"))
LIMIT = int(os.environ.get("LIMIT", "500"))  # feed 里保留最近 N 期，太大客户端会慢

_state = {"program_id": None, "xml": b"", "count": 0, "built": None, "error": None}
_lock = threading.Lock()


def regen(program_id):
    try:
        prog = tt.program_info(program_id)
        prog["h_program_id"] = program_id
        eps = tt.fetch_episodes(program_id)
        xml = tt.build_rss(prog, eps, "", LIMIT)
        with _lock:
            _state.update(xml=xml.encode("utf-8"), count=len(eps), program_id=program_id,
                          built=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), error=None)
        print(f"[{datetime.now():%H:%M:%S}] feed 已刷新: {len(eps)} 期 (输出最近 {LIMIT} 期, {len(xml)} 字节)", flush=True)
    except Exception as e:
        with _lock:
            _state["error"] = str(e)
        print(f"[{datetime.now():%H:%M:%S}] 刷新失败: {e}", flush=True)


def loop(program_id):
    while True:
        regen(program_id)
        time.sleep(REFRESH_HOURS * 3600)


class Handler(BaseHTTPRequestHandler):
    server_version = "tingtingfm-rss/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        with _lock:
            xml, count, built, err, pid = (_state["xml"], _state["count"], _state["built"], _state["error"], _state["program_id"])

        if path in ("/feed.xml", "/rss", "/podcast.xml"):
            if not xml:
                return self._send(503, ("generating… %s" % (err or "")).encode(), "text/plain; charset=utf-8")
            return self._send(200, xml, "application/rss+xml; charset=utf-8")

        if path == "/data.json":
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
            if os.path.exists(p):
                return self._send(200, open(p, "rb").read(), "application/json")
            return self._send(404, b"{}", "application/json")

        host = self.headers.get("Host", f"127.0.0.1:{PORT}")
        page = f"""<!doctype html><meta charset=utf-8>
<title>听听FM RSS</title>
<style>body{{font:15px/1.7 -apple-system,sans-serif;max-width:640px;margin:40px auto;padding:0 18px;color:#222}}
code{{background:#f4f4f5;padding:2px 6px;border-radius:4px}}.ok{{color:#0a0}}.bad{{color:#c00}}</style>
<h1>听听FM → Podcast RSS</h1>
<p>订阅地址（同一 Wi-Fi 下可用）：</p>
<p><code>http://{host}/feed.xml</code></p>
<ul>
<li>节目 ID：{pid}</li>
<li>已入库：{count} 期</li>
<li>feed 内输出：最近 {LIMIT} 期</li>
<li>上次刷新：{built}</li>
<li>状态：<span class="{'ok' if not err else 'bad'}">{err or '正常'}</span></li>
<li>自动刷新：每 {REFRESH_HOURS:g} 小时</li>
</ul>
<p>把上面的地址粘进 Apple Podcasts / Overcast / 小宇宙 / Pocket Casts 的「通过 URL 添加」即可。</p>
"""
        return self._send(200, page.encode(), "text/html; charset=utf-8")


def main():
    pid = sys.argv[1] if len(sys.argv) > 1 else "VkZorENdE7"
    threading.Thread(target=loop, args=(pid,), daemon=True).start()
    socketserver.TCPServer.allow_reuse_address = True
    srv = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"服务已启动: http://127.0.0.1:{PORT}/feed.xml  (Ctrl-C 停止)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
