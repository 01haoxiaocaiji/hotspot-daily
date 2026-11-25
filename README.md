# 每日热点 · 邮件自动推送

不依赖你自己的电脑或手机常开：把仓库放到 GitHub，让它每天定时替你跑一次，
抓微博 / 百度 / 今日头条热榜，生成排版好的 HTML 日报，直接发到你邮箱。

## 它能做什么

- 每天定时（默认北京时间 08:00）抓三个平台的公开热榜，各取前 15 条
- 生成移动端友好的 HTML 邮件 + 同内容 Markdown
- 任一数据源挂掉不影响其他源，脚本继续发信
- 零第三方依赖（纯标准库），Actions 里不用装包，跑一次约 20 秒

## 部署步骤（约 5 分钟，一次性）

### 1. 建仓库
在 GitHub 新建一个仓库（Public / Private 都行，Private 每月 2000 分钟免费额度也绰绰有余），
把本项目所有文件传上去，注意保持目录结构：

```
hotspot.py
.github/workflows/daily.yml
```

### 2. 打开 Actions
仓库页面 → **Settings → Actions → General** → 选择 “Allow all actions”，保存。

### 3. 配置 5 个 Secret
**Settings → Secrets and variables → Actions → New repository secret**，逐个添加：

| 名称 | 说明 | 示例 |
|---|---|---|
| `SMTP_HOST` | 邮箱 SMTP 服务器 | `smtp.qq.com` |
| `SMTP_PORT` | 端口，465 走 SSL，587 走 STARTTLS | `465` |
| `SMTP_USER` | 发件邮箱完整地址 | `you@qq.com` |
| `SMTP_PASS` | **授权码 / 应用专用密码**，不是登录密码 | `abcdabcdabcdabcd` |
| `MAIL_TO` | 收件邮箱，多个用英文逗号分隔 | `you@qq.com,me@163.com` |

常用服务商：

| 邮箱 | SMTP_HOST | 端口 | 密码怎么拿 |
|---|---|---|---|
| QQ 邮箱 | smtp.qq.com | 465 | 设置 → 账户 → 开启 SMTP → 生成授权码 |
| 163 邮箱 | smtp.163.com | 465 | 设置 → POP3/SMTP/IMAP → 客户端授权密码 |
| 126 邮箱 | smtp.126.com | 465 | 同上 |
| Gmail | smtp.gmail.com | 465 | 开两步验证 → 生成「应用专用密码」 |
| Outlook | smtp.office365.com | 587 | 账户安全 → 应用密码 |

> 授权码只存在 GitHub Secrets 里，代码和日志都不会打印它。

### 4. 先手动跑一次
仓库 → **Actions → daily-hotspot → Run workflow**。
跑完点进去看日志：应该出现三行 `[ok]` 和 `邮件已发送`。
若失败，日志会直接写哪个变量缺失或 SMTP 报什么错。

### 5. 完事
之后每天自动发。要改时间就编辑 `.github/workflows/daily.yml` 里的 cron
（**注意是 UTC 时间**，北京时间 = UTC+8，即减 8 小时；`0 22 * * *` 才是北京时间早上 6 点）。

## 本地试跑（可选）

```bash
python hotspot.py                 # 只生成 out/hotspot-YYYYMMDD.html 和 .md
python hotspot.py --send          # 生成并发信（需先设好上面 5 个环境变量）
python hotspot.py --top 10        # 每个榜单只要 10 条
```

Linux/macOS 临时设变量：
```bash
export SMTP_HOST=smtp.qq.com SMTP_PORT=465
export SMTP_USER=you@qq.com SMTP_PASS=你的授权码 MAIL_TO=you@qq.com
python hotspot.py --send
```

Windows PowerShell：
```powershell
$env:SMTP_HOST="smtp.qq.com"; $env:SMTP_PORT="465"
$env:SMTP_USER="you@qq.com"; $env:SMTP_PASS="授权码"; $env:MAIL_TO="you@qq.com"
python hotspot.py --send
```

## 已知限制（提前说清楚，免得踩坑）

1. **定时不是精确到秒**：GitHub 的高峰时段定时任务可能延迟几分钟到半小时。
   要绝对准点得用付费 runner 或你自己的服务器。
2. **仓库 60 天没有提交，定时任务会被自动停用**，GitHub 会给邮件提醒；
   去 Actions 页面点一下 Enable 即可。想彻底避免，可以每两个月随便改一行动一下。
3. **公开热榜 ≠ 权威事实**：榜单是平台算法结果，可能含营销话题（脚本已过滤微博广告位）。
   日报里已注明“以官方发布为准”。
4. **微博热度值**有时会被接口统一限流成一个数，属正常，不影响排序。
5. 知乎热榜接口需要登录态，未纳入；如需可自行加 Cookie 版本。

## 文件说明

| 文件 | 作用 |
|---|---|
| `hotspot.py` | 抓取 + 渲染 + 发信主程序，纯标准库 |
| `.github/workflows/daily.yml` | GitHub Actions 定时工作流 |
| `SKILL.md` | 作为“技能”使用时的说明（在本对话里让我按此生成日报） |
| `README.md` | 就是本文 |
