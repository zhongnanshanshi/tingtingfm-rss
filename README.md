# 听听FM 节目 → Podcast RSS

把 [听听FM](https://mobile.tingtingfm.com) 的节目页转成标准 Podcast RSS 2.0 订阅源，
可以直接粘进 Apple Podcasts / Overcast / Pocket Casts / 小宇宙 等播客客户端的「通过 URL 添加」。

当前订阅的节目：[《照亮新闻深处》- 北京新闻广播](https://mobile.tingtingfm.com/v3/program/VkZorENdE7)

## 订阅地址

```
https://<你的用户名>.github.io/<仓库名>/feed.xml
```

## 工作方式

- `scripts/tingtingfm_rss.py` 调用 `api-v3.tingtingfm.com` 抓节目信息和全部剧集
  （接口请求需要 `api_sign = md5(排序后的 query + "_" + secret)`，secret 硬编码在
  `mobile.tingtingfm.com/main.bundle.js` 里）。
- GitHub Actions 每 8 小时跑一次，重新生成 `feed.xml` 并提交，Pages 自动发布。
- 为什么要反复刷新：音频 CDN 链接带 `auth_key` 签名，只有 10 天有效期。
  定时重跑保证订阅源里始终是新鲜链接。

## 换一个节目

1. 打开节目页 `https://mobile.tingtingfm.com/v3/program/<PROGRAM_ID>`，记下 ID。
2. 仓库 Settings → Secrets and variables → Actions → Variables 新建 `PROGRAM_ID`。
3. 手动跑一次 workflow。

## 本地调试

```bash
# 一次性生成
python3 scripts/tingtingfm_rss.py VkZorENdE7 --out feed.xml --limit 500

# 本机起服务（同一 Wi-Fi 下手机可直接订阅）
python3 serve.py VkZorENdE7
```

## 免责声明

本项目只做格式转换与索引，音频版权归北京广播电视台 / 听听FM 所有。
内容仅供个人订阅收听，请勿再分发。
