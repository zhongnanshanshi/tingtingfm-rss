# 听听FM 节目 → Podcast RSS

把 [听听FM](https://mobile.tingtingfm.com) 的节目页转成标准 Podcast RSS 2.0 订阅源，
可以直接粘进 Apple Podcasts / Overcast / Pocket Casts / 小宇宙 等播客客户端的「通过 URL 添加」。

当前节目：[《照亮新闻深处》- 北京新闻广播](https://mobile.tingtingfm.com/v3/program/VkZorENdE7)

## 订阅地址

```
https://zhongnanshanshi.github.io/tingtingfm-rss/feed.xml
```

## 架构

```
本机 Mac                         GitHub
┌──────────────────────┐         ┌──────────────────┐
│ launchd 每 6 小时     │  push   │ 仓库 + Pages      │
│ python 调 tingtingfm │ ──────▶ │ feed.xml 静态托管 │ ──▶ 播客客户端
│ 生成 feed.xml        │         └──────────────────┘
└──────────────────────┘
```

**为什么抓取放在本机而不是 GitHub Actions**：`api-v3.tingtingfm.com` 对海外出口 IP
返回 `405 Not Allowed`（WAF 拦截），GitHub 的 runner 全在海外，抓不到数据。
本机在国内网络环境下正常，GitHub 只承担静态托管。

**为什么要反复刷新**：音频 CDN 链接带 `auth_key` 签名，有效期约 10 天。
`refresh.sh` 每 6 小时重跑一次，保证订阅源里的链接始终新鲜。
即使 Mac 关机几天，只要 10 天内更新过一次，所有链接就有效。

## 文件

| 文件 | 作用 |
|---|---|
| `scripts/tingtingfm_rss.py` | 抓取 + 生成 RSS |
| `refresh.sh` | 刷新并推送到 GitHub（launchd 调用） |
| `com.luck.tingtingfm-rss.plist` | launchd 定时任务定义 |
| `serve.py` | 本机 HTTP 服务（同一 Wi-Fi 下手机可直接订阅，调试用） |
| `feed.xml` | 生成的订阅源（由脚本覆盖，勿手改） |
| `index.html` | Pages 首页，显示订阅地址 |

## 常用命令

```bash
# 手动刷新一次
cd ~/Desktop/tingtingfm-rss && ./refresh.sh && tail -5 refresh.log

# 重新安装定时任务
launchctl unload ~/Library/LaunchAgents/com.luck.tingtingfm-rss.plist 2>/dev/null
cp com.luck.tingtingfm-rss.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.luck.tingtingfm-rss.plist
launchctl list | grep tingtingfm

# 单独生成一份
python3 scripts/tingtingfm_rss.py VkZorENdE7 --out feed.xml --limit 500

# 本机起服务
LIMIT=300 python3 serve.py VkZorENdE7
```

## 换一个节目

1. 打开节目页 `https://mobile.tingtingfm.com/v3/program/<PROGRAM_ID>`，记下末段 ID。
2. 改 `refresh.sh` 里的 `PROGRAM_ID`（或设环境变量）。
3. `./refresh.sh`。

## 技术细节

接口请求需要 `api_sign = md5(排序后的 query + "_" + secret)`。
secret 硬编码在前端 `mobile.tingtingfm.com/main.bundle.js` 里
（当前值见 `tingtingfm_rss.py` 的 `SECRET`）。
如果哪天接口开始报「请求参数sign错误」，重新从 bundle 里提取 secret 即可。

剧集列表接口 `/albumaudio/play_audio` 以 `audio_id` 为中心返回前后共 100 条，
脚本用滑动窗口翻页，可抓全 4000+ 期历史。

## 免责声明

本项目只做格式转换与索引，音频版权归北京广播电视台 / 听听FM 所有。
内容仅供个人订阅收听，请勿再分发。
