"""Gmail SMTP mailer: notice summaries (with .ics deadlines attached) and priority-task digests."""
import html
import os
import smtplib
import ssl
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr

from dotenv import load_dotenv

load_dotenv()

URG = {"high": ("#e11d48", "🔴 Urgent"), "medium": ("#d97706", "🟡 Important"), "low": ("#059669", "🟢 FYI")}


def enabled():
    return bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"))


def default_to():
    return os.getenv("SMTP_USER", "")


def send(to: str, subject: str, html_body: str, text_body: str, attachments=()):
    msg = EmailMessage()
    msg["From"] = formataddr((os.getenv("MAIL_FROM_NAME", "NoticeLens"), os.environ["SMTP_USER"]))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    for name, data, mime in attachments:
        maintype, subtype = mime.split("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
    host, port = os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "465"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            s.send_message(msg)


def _e(x):
    return html.escape(str(x or ""))


def _fmt(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%a, %d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def _days(iso):
    try:
        n = (datetime.strptime(iso, "%Y-%m-%d").date() - date.today()).days
    except (TypeError, ValueError):
        return ""
    return "Passed" if n < 0 else "Today!" if n == 0 else "Tomorrow" if n == 1 else f"{n} days left"


def _ics(title, tldr, dates):
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    ev = []
    for i, d in enumerate(x for x in dates if x.get("date")):
        start = d["date"].replace("-", "")
        end = (datetime.strptime(d["date"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
        summ = ("⏰ " if d.get("is_deadline") else "") + f"{title} – {d.get('label', '')}"
        ev += ["BEGIN:VEVENT", f"UID:{start}-{i}-{abs(hash(title))}@noticelens", f"DTSTAMP:{stamp}",
               f"DTSTART;VALUE=DATE:{start}", f"DTEND;VALUE=DATE:{end}", f"SUMMARY:{summ[:200]}",
               f"DESCRIPTION:{(tldr or '')[:500]}", "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY",
               f"DESCRIPTION:{title[:100]}", "END:VALARM", "END:VEVENT"]
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NoticeLens//EN", *ev, "END:VCALENDAR"]).encode()


def _shell(inner, preheader=""):
    return f"""<!doctype html><html><body style="margin:0;background:#f1f5f9;font-family:Segoe UI,Roboto,Noto Sans,Arial,sans-serif;color:#0f172a">
<span style="display:none">{_e(preheader)}</span>
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0">
<tr><td style="background:linear-gradient(90deg,#4f46e5,#c026d3);background-color:#4f46e5;padding:18px 24px;color:#fff;font-weight:700;font-size:18px">📋 NoticeLens</td></tr>
<tr><td style="padding:24px">{inner}</td></tr>
<tr><td style="padding:14px 24px;background:#f8fafc;color:#64748b;font-size:12px">Sent by NoticeLens · Smart Notice Board Summarizer</td></tr>
</table></td></tr></table></body></html>"""


def summary_email(s: dict):
    color, label = URG.get(s.get("urgency"), ("#64748b", "📌"))
    rel = s.get("relevance") or {}
    dates = s.get("dates") or []
    nxt = sorted([d for d in dates if d.get("date") and d["date"] >= date.today().isoformat()],
                 key=lambda d: (not d.get("is_deadline"), d["date"]))
    parts = [f"""<div style="font-size:12px;font-weight:700;color:{color}">{label} · {_e((s.get('category') or '').title())}</div>
<h1 style="font-size:22px;margin:6px 0 4px">{_e(s.get('emoji'))} {_e(s.get('title'))}</h1>
<div style="font-size:12px;color:#64748b;margin-bottom:14px">{_e(rel.get('reason'))}</div>"""]
    if nxt:
        d = nxt[0]
        parts.append(f"""<div style="background:{color};color:#fff;border-radius:12px;padding:14px 16px;margin-bottom:16px">
<div style="font-size:11px;text-transform:uppercase;opacity:.9">Next deadline</div>
<div style="font-size:18px;font-weight:700">⏳ {_days(d['date'])} · {_fmt(d['date'])}</div>
<div style="font-size:12px;opacity:.9">{_e(d.get('label'))[:140]}</div></div>""")
    if s.get("update"):
        rows = "".join(
            f"<li>{'💰' if c['kind'] == 'amount' else '📅'} <s style='color:#94a3b8'>{_e(c.get('old') if c['kind'] == 'amount' else _fmt(c.get('old')))}</s> → <b>{_e(c['new'] if c['kind'] == 'amount' else _fmt(c['new']))}</b></li>"
            for c in s["update"].get("changes", []) if c.get("old"))
        rows += "".join(f"<li>{_e(c)}</li>" for c in s["update"].get("ai_changes", []))
        parts.append(f"""<div style="border:2px solid #a5b4fc;background:#eef2ff;border-radius:12px;padding:12px 16px;margin-bottom:16px">
<b style="color:#4338ca">🔁 Updates an earlier notice</b><div style="font-size:12px;color:#475569">{_e(s['update']['of']['title'])}</div>
<ul style="margin:8px 0 0;padding-left:18px">{rows}</ul></div>""")
    parts.append(f"""<div style="font-size:11px;font-weight:700;color:#4f46e5;text-transform:uppercase">In short</div>
<p style="font-size:15px;line-height:1.5;margin:4px 0 16px">{_e(s.get('tldr'))}</p>""")
    if s.get("key_points"):
        parts.append('<div style="font-size:11px;font-weight:700;color:#4f46e5;text-transform:uppercase">Key points</div><ul style="margin:6px 0 16px;padding-left:18px;line-height:1.5">'
                     + "".join(f"<li>{_e(p)}</li>" for p in s["key_points"]) + "</ul>")
    if s.get("actions"):
        parts.append('<div style="font-size:11px;font-weight:700;color:#4f46e5;text-transform:uppercase">✅ What you need to do</div><table width="100%" style="margin:6px 0 16px">'
                     + "".join(f"<tr><td style='padding:6px 0;border-bottom:1px solid #f1f5f9'>☐ {_e(a.get('task'))}</td>"
                               f"<td align='right' style='white-space:nowrap;color:#e11d48;font-size:12px;font-weight:600'>{_fmt(a.get('deadline')) if a.get('deadline') else ''}</td></tr>"
                               for a in s["actions"]) + "</table>")
    if s.get("penalty"):
        parts.append(f"<div style='background:#fff1f2;color:#be123c;border-radius:10px;padding:10px 14px;font-size:14px'>⚠️ <b>If you ignore this:</b> {_e(s['penalty'])}</div>")
    if dates:
        parts.append('<div style="font-size:12px;color:#64748b;margin-top:16px">📅 All dates are attached as a calendar file (.ics) with a 1-day reminder.</div>')
    text = f"{s.get('title')}\n\n{s.get('tldr')}\n\n" + "\n".join("• " + p for p in s.get("key_points", [])) + \
           "\n\nTo do:\n" + "\n".join(f"☐ {a.get('task')} {('(' + _fmt(a['deadline']) + ')') if a.get('deadline') else ''}" for a in s.get("actions", []))
    atts = [("deadlines.ics", _ics(s.get("title", "Notice"), s.get("tldr", ""), dates), "text/calendar")] if dates else []
    subject = f"{'⏰ ' + _days(nxt[0]['date']) + ' · ' if nxt else ''}{s.get('emoji', '')} {s.get('title', 'Notice summary')}"
    return subject, _shell("".join(parts), s.get("tldr", "")), text, atts


def digest_email(tasks: list, kpis: dict | None = None):
    kp = kpis or {}
    tiles = "".join(f"<td align='center' style='padding:10px;background:#f8fafc;border-radius:10px'><div style='font-size:22px;font-weight:700'>{_e(v)}</div>"
                    f"<div style='font-size:11px;color:#64748b'>{_e(k)}</div></td><td width='8'></td>" for k, v in kp.items())
    rows = ""
    for i, t in enumerate(tasks, 1):
        color, label = URG.get(t.get("urgency"), ("#64748b", ""))
        rows += f"""<tr><td valign="top" style="padding:10px 10px 10px 0;border-bottom:1px solid #f1f5f9">
<div style="width:26px;height:26px;border-radius:8px;background:{'#4f46e5' if i == 1 else '#e2e8f0'};color:{'#fff' if i == 1 else '#0f172a'};text-align:center;line-height:26px;font-weight:700;font-size:12px">{i}</div></td>
<td style="padding:10px 0;border-bottom:1px solid #f1f5f9"><div style="font-size:14px;font-weight:600">{_e(t.get('task'))}</div>
<div style="font-size:12px;margin-top:3px"><span style="color:{color};font-weight:700">{label}</span> ·
<span style="color:#e11d48;font-weight:600">⏳ {_days(t.get('date')) if t.get('date') else 'No date'}{' · ' + _fmt(t.get('date')) if t.get('date') else ''}</span> ·
<span style="color:#64748b">{_e(t.get('emoji'))} {_e(t.get('title'))}</span></div></td></tr>"""
    inner = f"""<h1 style="font-size:22px;margin:0 0 4px">🎯 Your top priority tasks</h1>
<div style="color:#64748b;font-size:13px;margin-bottom:16px">{date.today().strftime('%A, %d %B %Y')}</div>
{'<table cellpadding="0" cellspacing="0" style="margin-bottom:16px"><tr>' + tiles + '</tr></table>' if tiles else ''}
<table width="100%" cellpadding="0" cellspacing="0">{rows or '<tr><td>🎉 Nothing pending!</td></tr>'}</table>"""
    text = "Your top priority tasks\n\n" + "\n".join(
        f"{i}. {t.get('task')} — {_fmt(t.get('date')) if t.get('date') else 'no date'} ({t.get('title')})" for i, t in enumerate(tasks, 1))
    first = tasks[0] if tasks else None
    subject = f"🎯 {len(tasks)} priority tasks" + (f" · next: {_days(first.get('date'))}" if first and first.get("date") else "")
    return subject, _shell(inner, text[:120]), text, []
