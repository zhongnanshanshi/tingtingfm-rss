#!/bin/bash
# 抓取听听FM 节目 -> 生成 feed.xml -> 推送到 GitHub Pages
# 由 launchd (com.luck.tingtingfm-rss.plist) 每 6 小时调用一次

set -uo pipefail

REPO_DIR="$HOME/tingtingfm-rss"
PROGRAM_ID="${PROGRAM_ID:-VkZorENdE7}"
LIMIT="${LIMIT:-500}"
export PATH="$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
LOG="$REPO_DIR/refresh.log"

cd "$REPO_DIR" || exit 1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 开始刷新 ===" >> "$LOG"

# 1) 生成（最多重试一次）
if ! python3 scripts/tingtingfm_rss.py "$PROGRAM_ID" --out feed.xml.tmp --limit "$LIMIT" >> "$LOG" 2>&1; then
  echo "$(date '+%H:%M:%S') 第一次生成失败，重试一次" >> "$LOG"
  sleep 20
  if ! python3 scripts/tingtingfm_rss.py "$PROGRAM_ID" --out feed.xml.tmp --limit "$LIMIT" >> "$LOG" 2>&1; then
    echo "$(date '+%H:%M:%S') 生成失败，保留旧 feed" >> "$LOG"
    rm -f feed.xml.tmp
    exit 1
  fi
fi

# 2) 校验
if ! python3 -c "import xml.etree.ElementTree as E,sys; t=E.parse('feed.xml.tmp'); n=len(t.getroot().findall('./channel/item')); sys.exit(0 if n>10 else 1)"; then
  echo "$(date '+%H:%M:%S') 新 feed 校验不通过，保留旧 feed" >> "$LOG"
  rm -f feed.xml.tmp
  exit 1
fi

mv feed.xml.tmp feed.xml

# 3) 推送
git add feed.xml
if git diff --cached --quiet; then
  echo "$(date '+%H:%M:%S') 内容无变化，跳过推送" >> "$LOG"
  exit 0
fi
git -c user.name="zhongnanshanshi" -c user.email="zhongnanshanshi@users.noreply.github.com" \
    commit -q -m "chore: refresh feed $(date -u '+%Y-%m-%dT%H:%MZ')" >> "$LOG" 2>&1
if git push -q origin main >> "$LOG" 2>&1; then
  echo "$(date '+%H:%M:%S') 已推送，GitHub Pages 约 1 分钟后生效" >> "$LOG"
else
  echo "$(date '+%H:%M:%S') 推送失败（网络？），本地 feed 已更新" >> "$LOG"
  exit 1
fi
