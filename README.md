# 听听FM 节目 → Podcast RSS

把 [听听FM](https://mobile.tingtingfm.com) 的节目转成标准 Podcast RSS 2.0，
可以直接粘进 Apple Podcasts / Overcast / Pocket Casts / 小宇宙 的「通过 URL 添加」。

当前收录 14 个节目。

## 订阅地址

**北京交通广播 FM103.9**

| 节目 | 订阅源 | 更新 |
|---|---|---|
| 一路畅通·早高峰 | https://zhongnanshanshi.github.io/tingtingfm-rss/yiluchangtong-zao.xml | 日更 |
| 一路畅通·晚高峰 | https://zhongnanshanshi.github.io/tingtingfm-rss/yiluchangtong.xml | 日更 |
| 新闻要知道 | https://zhongnanshanshi.github.io/tingtingfm-rss/xinwenyaozhidao.xml | 日更 |
| 1039服务热线 | https://zhongnanshanshi.github.io/tingtingfm-rss/fuwurexian1039.xml | 日更 |
| 行走天下（原联e会） | https://zhongnanshanshi.github.io/tingtingfm-rss/xingzoutianxia.xml | 日更 |

**北京新闻广播 FM94.5**

| 节目 | 订阅源 | 更新 |
|---|---|---|
| 科技新视点 | https://zhongnanshanshi.github.io/tingtingfm-rss/kejixinshidian.xml | 日更 |
| 财经对对碰 | https://zhongnanshanshi.github.io/tingtingfm-rss/caijingduiduipeng.xml | 日更 |
| 照亮新闻深处 | https://zhongnanshanshi.github.io/tingtingfm-rss/feed.xml | 周更 |

**北京文艺广播 FM87.6**

| 节目 | 订阅源 | 更新 |
|---|---|---|
| 打开文化之门 | https://zhongnanshanshi.github.io/tingtingfm-rss/wenhuazhimen.xml | 日更 |
| 文化经纬线 | https://zhongnanshanshi.github.io/tingtingfm-rss/wenhuajingweixian.xml | 日更 |
| 悦读时光 | https://zhongnanshanshi.github.io/tingtingfm-rss/yuedushiguang.xml | 日更 |
| 环球旅行家 | https://zhongnanshanshi.github.io/tingtingfm-rss/huanqiulvxingjia.xml | 日更 |

**北京音乐广播 FM97.4**

| 节目 | 订阅源 | 更新 |
|---|---|---|
| 复刻唱片行 | https://zhongnanshanshi.github.io/tingtingfm-rss/fukechangpianxing.xml | 周更 |

**北京城市广播副中心之声 FM102.5 / AM1026**

| 节目 | 订阅源 | 更新 |
|---|---|---|
| 教育面对面 | https://zhongnanshanshi.github.io/tingtingfm-rss/jiaoyumiduimian.xml | 日更 |

首页（带复制按钮）：<https://zhongnanshanshi.github.io/tingtingfm-rss/>

节目 ID 依次为 `2QKo6pJ1Nl`、`p1WdY8NJgz`、`VWXaN2aM2j`、`rkgoD0o1qm`、`4ZdKyGea0r`、
`OjdkYXRaBm`、`eLoAny1aGm`、`VkZorENdE7`、`POjdkZgJBm`、`xGo4ebna0L`、`1WdY5rMdgz`、
`D9VdpOZJeR`、`V2WoqkOJ9g`、`p2Zdjwpozy`，在 `update-feed.yml` 的 `FEEDS`
环境变量里维护，一行一项，格式 `<节目ID>=<输出文件>`。

## 架构

```
GitHub Actions (每天 2 次)
   │
   ├─ curl ──▶ 公共 RSSHub 实例（香港等地出口）
   │              └─ 抓 api-v3.tingtingfm.com
   │
   ├─ scripts/from_rsshub.py 解析并重建标准 feed
   └─ commit feed.xml ──▶ GitHub Pages ──▶ 播客客户端
```

**为什么不直连 tingtingfm**：`api-v3.tingtingfm.com` 与 `mobile.tingtingfm.com`
的阿里云 WAF 对所有海外 IP 返回 `405 Not Allowed`（实测 GitHub runner 位于
Azure 美国，连首页都拿不到）。而 [RSSHub](https://github.com/DIYgod/RSSHub)
自带 `tingtingfm` 路由，部分公共实例出口在香港，可以正常访问，于是用它做中转。

**为什么每天刷新**：音频 CDN 链接带 `auth_key` 签名，有效期约 10 天。
定时重建保证订阅源里的链接始终新鲜。

## 文件

| 文件 | 作用 |
|---|---|
| `.github/workflows/update-feed.yml` | 每天两次：抓取 → 校验 → 提交 |
| `scripts/from_rsshub.py` | 经 RSSHub 抓取并重建 feed（多实例自动 fallback） |
| `scripts/tingtingfm_rss.py` | 直连官方 API 的实现（含签名算法）；国内网络下可抓全 4000+ 期历史 |
| `feed.xml` | 生成的订阅源，勿手改 |
| `index.html` | Pages 首页 |

## 为什么只有 100 期

RSSHub 的 `tingtingfm` 路由只输出最近 100 期（约两年）。
想要完整历史可在国内网络下直连官方 API：

```bash
python3 scripts/tingtingfm_rss.py VkZorENdE7 --out feed.xml   # 全量 4000+ 期
```

## 换一个节目

1. 打开 `https://mobile.tingtingfm.com/v3/program/<PROGRAM_ID>`，记下 ID。
2. 仓库 Settings → Secrets and variables → Actions → Variables，
   新建 `PROGRAM_ID`，值填节目 ID。
3. Actions 页面手动跑一次 `Update feed`。

## 技术细节

官方 API 需要 `api_sign = md5(排序后的 query + "_" + secret)`，
secret 硬编码在前端 `mobile.tingtingfm.com/main.bundle.js` 里
（见 `scripts/tingtingfm_rss.py` 的 `SECRET`）。如果哪天报「请求参数sign错误」，
重新从 bundle 提取即可。

## 免责声明

本项目只做格式转换与索引，音频版权归北京广播电视台 / 听听FM 所有。
内容仅供个人订阅收听，请勿再分发。
