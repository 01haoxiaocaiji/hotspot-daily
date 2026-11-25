#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日热点简报 hotspot.py
抓取 微博 / 百度 / 今日头条 公开热榜，生成 HTML + Markdown 日报，可选 SMTP 发信。

用法:
    python hotspot.py                    # 只生成文件到 ./out
    python hotspot.py --send             # 生成并发送邮件（读环境变量）
    python hotspot.py --send --dry-run   # 只打印配置，不真发

环境变量（发信时必填）:
    SMTP_HOST  SMTP_PORT  SMTP_USER  SMTP_PASS  MAIL_TO
零第三方依赖，仅标准库，方便在 GitHub Actions 里直接跑。
"""
import argparse
import gzip
import html
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from urllib.error import URLError
from urllib.request import Request, urlopen

CST = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


# ---------------------------------------------------------------- 抓取
def fetch_json(url, referer=None, timeout=20):
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8", "replace"))


def clean(s):
    return (s or "").strip().strip("#").strip()


def fetch_weibo(n=15):
    d = fetch_json("https://weibo.com/ajax/side/hotSearch", referer="https://weibo.com/")
    data = d.get("data") or {}
    items = []
    for it in data.get("realtime") or []:
        if it.get("is_ad"):
            continue
        w = clean(it.get("word") or it.get("note"))
        if not w:
            continue
        items.append({"title": w, "hot": int(it.get("num") or 0)})
        if len(items) >= n:
            break
    top = clean((data.get("hotgov") or {}).get("name"))
    if not items:
        raise ValueError("微博热搜为空")
    return {"key": "weibo", "name": "微博热搜", "color": "#ef4444",
            "top": top, "items": items}


def fetch_baidu(n=15):
    d = fetch_json("https://top.baidu.com/api/board?platform=wise&tab=realtime",
                   referer="https://top.baidu.com/")
    items, top = [], ""
    for card in (d.get("data") or {}).get("cards") or []:
        if card.get("component") != "tabTextList":
            continue
        for group in card.get("content") or []:
            for it in group.get("content") or []:
                w = clean(it.get("word"))
                if not w:
                    continue
                if it.get("isTop"):
                    top = w
                    continue
                items.append({"title": w, "hot": int(it.get("hotScore") or 0)})
                if len(items) >= n:
                    break
            if len(items) >= n:
                break
    if not items:
        raise ValueError("百度热搜为空")
    return {"key": "baidu", "name": "百度热搜", "color": "#3b82f6",
            "top": top, "items": items}


def fetch_toutiao(n=15):
    d = fetch_json("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
                   referer="https://www.toutiao.com/")
    items = []
    for it in (d.get("data") or [])[:n]:
        t = clean(it.get("Title"))
        if not t:
            continue
        try:
            hot = int(it.get("HotValue") or 0)
        except (TypeError, ValueError):
            hot = 0
        items.append({"title": t, "hot": hot})
    if not items:
        raise ValueError("头条热榜为空")
    return {"key": "toutiao", "name": "今日头条热榜", "color": "#f59e0b",
            "top": "", "items": items}


SOURCES = [("微博热搜", fetch_weibo), ("百度热搜", fetch_baidu), ("今日头条热榜", fetch_toutiao)]


def collect():
    boards, errors = [], []
    for name, fn in SOURCES:
        try:
            boards.append(fn())
            print("  [ok]   " + name)
        except (URLError, ValueError, KeyError, json.JSONDecodeError, OSError) as exc:
            errors.append("%s: %s" % (name, exc))
            print("  [fail] %s -> %s" % (name, exc), file=sys.stderr)
    if not boards:
        raise RuntimeError("全部数据源抓取失败：" + " | ".join(errors))
    return boards, errors


# ---------------------------------------------------------------- 渲染
def fmt_hot(v):
    if not v:
        return ""
    if v >= 100000000:
        return "%.1f亿" % (v / 100000000.0)
    if v >= 10000:
        return "%.1f万" % (v / 10000.0)
    return str(v)


def render_html(boards, now):
    date_str = now.strftime("%Y-%m-%d")
    wd = WEEKDAYS[now.weekday()]
    parts = []
    for b in boards:
        rows = []
        for i, it in enumerate(b["items"], 1):
            hot = fmt_hot(it["hot"])
            hot_html = (' <span style="color:#9ca3af;font-size:12px;">· %s</span>' % hot) if hot else ""
            rows.append('<li style="margin:0 0 2px;">%s%s</li>'
                        % (html.escape(it["title"]), hot_html))
        top_html = ""
        if b["top"]:
            top_html = ('<div style="margin-top:10px;padding:8px 10px;background:#fef2f2;'
                        'border-radius:6px;font-size:13px;color:#b91c1c;">'
                        "<b>置顶</b> " + html.escape(b["top"]) + "</div>")
        parts.append(
            '<div style="background:#ffffff;padding:18px 20px 10px;border-top:1px solid #f1f2f4;">'
            '<div style="font-size:15px;font-weight:700;color:#111827;'
            'border-left:4px solid %s;padding-left:9px;">%s</div>%s'
            '<ol style="margin:12px 0 0;padding-left:20px;color:#374151;'
            'font-size:14px;line-height:1.95;">%s</ol>'
            "</div>"
            % (b["color"], html.escape(b["name"]), top_html, "".join(rows))
        )
    body = "".join(parts)
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日热点 %s</title></head>
<body style="margin:0;padding:0;background:#f4f5f7;">
<div style="max-width:640px;margin:0 auto;padding:20px 12px;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="background:#111827;border-radius:12px 12px 0 0;padding:22px 20px;">
    <div style="font-size:12px;letter-spacing:3px;color:#9ca3af;">DAILY BRIEF</div>
    <div style="font-size:22px;font-weight:700;color:#ffffff;margin-top:8px;">每日热点 · %s %s</div>
    <div style="font-size:12px;color:#9ca3af;margin-top:8px;">抓取于 %s（北京时间）</div>
  </div>
  %s
  <div style="background:#ffffff;border-radius:0 0 12px 12px;padding:14px 20px 18px;
       font-size:12px;color:#9ca3af;line-height:1.7;">
    数据来自各平台公开热榜接口，仅作速览，不代表本邮件对事实的确认；重要事项请以官方发布为准。
  </div>
</div></body></html>""" % (date_str, date_str, wd, now.strftime("%Y-%m-%d %H:%M"), body)


def render_md(boards, now):
    lines = ["# 每日热点 · %s %s" % (now.strftime("%Y-%m-%d"), WEEKDAYS[now.weekday()]), "",
             "> 抓取于 %s（北京时间）｜数据来自各平台公开热榜" % now.strftime("%Y-%m-%d %H:%M"), ""]
    for b in boards:
        lines.append("## %s" % b["name"])
        lines.append("")
        if b["top"]:
            lines.append("**置顶**：%s" % b["top"])
            lines.append("")
        for i, it in enumerate(b["items"], 1):
            hot = fmt_hot(it["hot"])
            lines.append("%d. %s%s" % (i, it["title"], ("（%s）" % hot) if hot else ""))
        lines.append("")
    lines.append("---")
    lines.append("数据来自公开热榜接口，仅作速览，重要事项以官方发布为准。")
    return "\n".join(lines)


# ---------------------------------------------------------------- 发信
def send_mail(subject, html_body):
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "465") or 465)
    user = os.environ.get("SMTP_USER", "").strip()
    pwd = os.environ.get("SMTP_PASS", "").strip()
    to_raw = os.environ.get("MAIL_TO", "").strip()
    missing = [k for k, v in [("SMTP_HOST", host), ("SMTP_USER", user),
                              ("SMTP_PASS", pwd), ("MAIL_TO", to_raw)] if not v]
    if missing:
        raise SystemExit("缺少环境变量: " + ", ".join(missing))
    to_list = [x.strip() for x in to_raw.replace(";", ",").split(",") if x.strip()]

    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr(("每日热点", user))
    msg["To"] = ", ".join(to_list)
    msg["Date"] = formatdate(localtime=False)

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=ctx) as s:
            s.login(user, pwd)
            s.sendmail(user, to_list, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.sendmail(user, to_list, msg.as_string())
    print("  邮件已发送 -> " + ", ".join(to_list))


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="发送邮件")
    ap.add_argument("--dry-run", action="store_true", help="只生成文件，不发送")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--top", type=int, default=15, help="每个榜单条数")
    args = ap.parse_args()

    now = datetime.now(CST)
    print("== 抓取热榜 ==")
    boards, errors = collect()
    for b in boards:
        b["items"] = b["items"][: args.top]

    os.makedirs(args.out_dir, exist_ok=True)
    stem = "hotspot-%s" % now.strftime("%Y%m%d")
    html_path = os.path.join(args.out_dir, stem + ".html")
    md_path = os.path.join(args.out_dir, stem + ".md")
    html_body = render_html(boards, now)
    md_body = render_md(boards, now)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_body)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_body)
    print("  已生成: %s" % html_path)
    print("  已生成: %s" % md_path)

    subject = "[每日热点] %s %s" % (now.strftime("%Y-%m-%d"), WEEKDAYS[now.weekday()])
    if args.send and not args.dry_run:
        send_mail(subject, html_body)
    elif args.send and args.dry_run:
        print("  [dry-run] 将发送主题: %s" % subject)
    if errors:
        print("  [注意] 部分数据源失败: " + " | ".join(errors), file=sys.stderr)


if __name__ == "__main__":
    main()
