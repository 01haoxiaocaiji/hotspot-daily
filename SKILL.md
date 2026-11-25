---
name: daily-hotspot-brief
description: 生成每日热点简报（微博/百度/今日头条热榜），可渲染邮件 HTML 并定时推送。当用户说"今日热点""热点简报""整理热搜""每天的热点"时使用。
license: MIT
---

# 每日热点简报

把一个"攒热点"的动作标准化：固定数据源、固定版式、固定发送方式，避免每次口径不一。

## 触发场景

- 用户要求「今日热点」「今天的新闻」「热点简报」「整理热搜」
- 用户要求把热点定时推送到邮箱
- 用户要求把热点做成日报/周报文档

## 数据源（均已验证可用）

| 平台 | 接口 | 关键字段 |
|---|---|---|
| 微博热搜 | `https://weibo.com/ajax/side/hotSearch` | `data.realtime[].word` / `.num`，需过滤 `is_ad` |
| 百度热搜 | `https://top.baidu.com/api/board?platform=wise&tab=realtime` | `data.cards[0].content[0].content[].word` |
| 今日头条 | `https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc` | `data[].Title` / `.HotValue` |

知乎 `/api/v3/feed/topstory/hot-lists/total` 返回 401（需登录态），不要使用。
请求需带桌面版 User-Agent 和对应 Referer；只接受 gzip，避免 brotli 解压不了。

## 执行方式

**方式一（本地/服务器）**
```bash
python hotspot.py --send --out-dir out
```

**方式二（对话内）**
抓取后用下面的结构直接输出，不要堆砌无关八卦：

1. 一句话总览（今天最大的 1 件事）
2. 🚀 头条 / 时政
3. 💻 科技与产业
4. 📈 市场财经
5. 🌡 社会民生
6. 🌍 国际
7. 🎬 文娱体育（压到一句话）

**输出纪律**
- 必须标注时间口径（哪一天的热点、抓取时刻）
- 明确说明「热榜是平台算法结果，重大事项以官方发布为准」
- 不把热搜标题当事实陈述；敏感事件注明来源与"待官方确认"
- 不编造未在数据源出现的条目

## 定时推送

GitHub Actions，见 `.github/workflows/daily.yml`，cron 用 UTC。
凭据全部走仓库 Secrets：`SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASS` `MAIL_TO`。
