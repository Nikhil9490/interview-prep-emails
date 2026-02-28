import os
import json
import re
import smtplib
import ssl
from io import BytesIO
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import matplotlib.pyplot as plt
from dotenv import load_dotenv
from docx import Document
from openai import OpenAI

STATE_FILE = "state.json"
TOPICS_FILE = "topics.docx"
LOG_DIR = "logs"

# ---------- Utilities ----------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def escape_html(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"day_index": 0, "last_sent_utc": None}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def load_day_plans_from_docx(path: str) -> list[str]:
    doc = Document(path)
    plans = [(p.text or "").strip() for p in doc.paragraphs if (p.text or "").strip()]
    if not plans:
        raise ValueError("topics.docx is empty. Add one day-plan per paragraph.")
    return plans

def already_sent_today(state: dict, now: datetime) -> bool:
    if os.environ.get("FORCE_SEND", "0").strip() == "1":
        return False
    last = state.get("last_sent_utc")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return False
    return last_dt.date() == now.date()

def write_log(now: datetime, subject: str, text_body: str) -> None:
    ensure_dir(LOG_DIR)
    path = os.path.join(LOG_DIR, f"{now.strftime('%Y-%m-%d')}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(subject + "\n\n")
        f.write(text_body)

def get_last_n_learning(plans: list[str], current_index: int, n: int = 6) -> list[str]:
    out = []
    i = current_index - 1
    while i >= 0 and len(out) < n:
        if plans[i].strip().upper() != "REVISION":
            out.append(plans[i])
        i -= 1
    return list(reversed(out))

# ---------- Equation rendering (always readable) ----------

def render_equation_png(latex: str) -> bytes:
    """
    Render equation to PNG using matplotlib mathtext with BLACK on WHITE.
    Works for most ML equations without requiring a TeX install.
    """
    expr = f"${latex}$"

    fig = plt.figure(figsize=(0.01, 0.01), dpi=220)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_facecolor("white")

    t = ax.text(0, 0, expr, fontsize=18, color="black")

    fig.canvas.draw()
    bbox = t.get_window_extent()
    width, height = bbox.width / fig.dpi, bbox.height / fig.dpi
    fig.set_size_inches(width + 0.35, height + 0.25)

    fig.canvas.draw()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=220, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return buf.getvalue()

# ---------- Email sending (inline images) ----------

def send_email(subject: str, text_body: str, html_body: str, inline_images=None) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]
    to_email = os.environ["TO_EMAIL"]
    from_name = os.environ.get("FROM_NAME", "Daily Interview Newsletter")

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    if inline_images:
        for cid, png_bytes in inline_images:
            img = MIMEImage(png_bytes, _subtype="png")
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
            msg.attach(img)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(user, pwd)
        server.sendmail(user, [to_email], msg.as_string())

# ---------- JSON parsing from model output ----------

def extract_json_object(text: str) -> dict:
    """
    Model sometimes adds whitespace or accidental text.
    We'll extract the first JSON object by locating the first '{' and last '}'.
    """
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    raw = text[start:end+1]
    return json.loads(raw)

def normalize_lesson_payload(d: dict) -> dict:
    # Minimal defaults to avoid KeyErrors if model misses something
    d.setdefault("title", "")
    d.setdefault("subtitle", "")
    d.setdefault("core_intuition", [])
    d.setdefault("equations", [])
    d.setdefault("qa_sections", [])
    d.setdefault("pitfalls", [])
    d.setdefault("implementation", {"sklearn": "", "toy_data": "", "practice_notes": []})
    d.setdefault("speaking_script", [])
    d.setdefault("mini_drill", {"practice": [], "follow_ups": []})
    return d

def normalize_revision_payload(d: dict) -> dict:
    d.setdefault("title", "Revision")
    d.setdefault("subtitle", "Quiz + drills + mini design prompts")
    d.setdefault("quiz", [])
    d.setdefault("answer_key", [])
    d.setdefault("speaking_drills", [])
    d.setdefault("design_prompts", [])
    d.setdefault("checklist", [])
    return d

# ---------- Newsletter HTML renderer (deterministic) ----------

def shell_html(title: str, subtitle: str, inner_html: str) -> str:
    return f"""
<html>
  <body style="margin:0;padding:0;background:#f6f7fb;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f7fb;padding:26px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="width:680px;max-width:680px;">
            <tr>
              <td style="padding:0 8px 14px 8px;">
                <div style="font-family:Arial,Helvetica,sans-serif;color:#6b7280;font-size:12px;letter-spacing:.9px;text-transform:uppercase;">
                  Daily Interview Newsletter
                </div>
              </td>
            </tr>

            <tr>
              <td style="background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;overflow:hidden;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="padding:18px 22px;background:linear-gradient(90deg,#7c3aed,#2563eb);">
                      <div style="font-family:Arial,Helvetica,sans-serif;color:#ffffff;font-size:26px;font-weight:800;line-height:1.2;">
                        {escape_html(title)}
                      </div>
                      <div style="font-family:Arial,Helvetica,sans-serif;color:rgba(255,255,255,.92);font-size:14px;margin-top:6px;">
                        {escape_html(subtitle)}
                      </div>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:20px 22px;">
                      <div style="font-family:Arial,Helvetica,sans-serif;color:#111827;font-size:15px;line-height:1.65;">
                        {inner_html}
                      </div>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:14px 22px;border-top:1px solid #e5e7eb;background:#fafafa;">
                      <div style="font-family:Arial,Helvetica,sans-serif;color:#6b7280;font-size:12px;line-height:1.4;">
                        Action: explain this aloud in 2 minutes + implement the template once.
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:12px 8px 0 8px;">
                <div style="font-family:Arial,Helvetica,sans-serif;color:#9ca3af;font-size:11px;line-height:1.4;">
                  If something looks off, reply with the snippet and I’ll improve the generator.
                </div>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()

def card(title: str, body: str) -> str:
    return f"""
<div style="margin:16px 0;padding:16px 16px;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;">
  <div style="margin:0 0 10px 0;font-size:18px;font-weight:900;color:#111827;">{escape_html(title)}</div>
  {body}
</div>
""".strip()

def list_ul(items: list[str]) -> str:
    if not items:
        return '<div style="color:#6b7280;">(none)</div>'
    lis = "".join([f'<li style="margin:6px 0;">{escape_html(x)}</li>' for x in items])
    return f'<ul style="margin:10px 0 10px 18px;padding:0;">{lis}</ul>'

def list_ol(items: list[str]) -> str:
    if not items:
        return '<div style="color:#6b7280;">(none)</div>'
    lis = "".join([f'<li style="margin:6px 0;">{escape_html(x)}</li>' for x in items])
    return f'<ol style="margin:10px 0 10px 18px;padding:0;">{lis}</ol>'

def qa_block(question: str, answer: str) -> str:
    safe_q = escape_html(question)
    safe_a = escape_html(answer).replace("\n", "<br>")

    return """
<div style="margin:12px 0;padding:14px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;">
  <div style="font-weight:900;color:#1d4ed8;margin:0 0 8px 0;">Q: {q}</div>
  <div style="color:#111827;margin:0;">{a}</div>
</div>
""".format(q=safe_q, a=safe_a)

def code_pre(code: str) -> str:
    if not code.strip():
        return '<div style="color:#6b7280;">(not provided)</div>'

    safe = escape_html(code)

    return """
<pre style="background:#0b1220;color:#e5e7eb;padding:14px;border-radius:14px;overflow:auto;border:1px solid #111827;margin:10px 0;">
{code}
</pre>
""".format(code=safe)

def equation_cards(equations: list[str]) -> tuple[str, list[tuple[str, bytes]]]:
    """
    Returns HTML for equation cards and list of (cid, png_bytes) to attach.
    """
    inline_images = []
    blocks = []
    for idx, latex in enumerate(equations[:8], start=1):
        cid = f"eq{idx}"
        try:
            png = render_equation_png(latex)
            inline_images.append((cid, png))
            blocks.append(f"""
<div style="margin:12px 0;padding:12px 14px;background:#ffffff;border-radius:14px;border:1px solid #e5e7eb;">
  <img src="cid:{cid}" style="max-width:100%;height:auto;display:block;">
</div>
""".strip())
        except Exception:
            blocks.append(f"""
<div style="margin:12px 0;padding:12px 14px;background:#ffffff;border-radius:14px;border:1px solid #e5e7eb;">
  <code>{escape_html(latex)}</code>
</div>
""".strip())
    return "\n".join(blocks) if blocks else '<div style="color:#6b7280;">(none)</div>', inline_images

def render_lesson_newsletter(payload: dict) -> tuple[str, list[tuple[str, bytes]]]:
    payload = normalize_lesson_payload(payload)

    # Core intuition (list of bullets)
    core = list_ul(payload["core_intuition"])

    # Equations (image cards)
    eq_html, eq_imgs = equation_cards(payload["equations"])

    # Q/A grouped
    qa_sections_html = []
    for sec in payload["qa_sections"]:
        sec_title = sec.get("title", "Q&A")
        items = sec.get("items", [])
        blocks = [f'<div style="margin:10px 0 6px;font-weight:900;color:#111827;">{escape_html(sec_title)}</div>']
        for it in items:
            q = it.get("q", "").strip()
            a = it.get("a", "").strip()
            if q and a:
                blocks.append(qa_block(q, a))
        qa_sections_html.append("\n".join(blocks))
    qa_html = "\n".join(qa_sections_html) if qa_sections_html else '<div style="color:#6b7280;">(none)</div>'

    # Pitfalls
    pitfalls = list_ul(payload["pitfalls"])

    # Implementation
    impl = payload.get("implementation", {})
    impl_html = (
        '<div style="font-weight:900;margin:8px 0 6px;">sklearn template</div>'
        + code_pre(impl.get("sklearn", ""))
        + '<div style="font-weight:900;margin:14px 0 6px;">tiny synthetic snippet</div>'
        + code_pre(impl.get("toy_data", ""))
        + '<div style="font-weight:900;margin:14px 0 6px;">what to change in practice</div>'
        + list_ul(impl.get("practice_notes", []))
    )

    # Speaking script
    speaking = list_ul(payload["speaking_script"])

    # Mini drill
    md = payload.get("mini_drill", {})
    practice_items = md.get("practice", [])
    followups = md.get("follow_ups", [])
    drill_blocks = []
    if practice_items:
        drill_blocks.append('<div style="font-weight:900;margin:6px 0 8px;">Practice</div>')
        for it in practice_items:
            q = it.get("q","").strip()
            a = it.get("a","").strip()
            if q and a:
                drill_blocks.append(qa_block(q, a))
    drill_html = "\n".join(drill_blocks) if drill_blocks else '<div style="color:#6b7280;">(none)</div>'

    inner = "\n".join([
        card("Core intuition", core),
        card("Key equations", eq_html),
        card("Interview Q&A — coverage-first", qa_html),
        card("Pitfalls / failure modes", pitfalls),
        card("Implementation templates", impl_html),
        card("Speaking script", speaking),
        card("Mini-drill", drill_html),
    ])

    title = payload.get("title") or "Daily Lesson"
    subtitle = payload.get("subtitle") or "Interview-ready explanations + templates + drills"

    return shell_html(title, subtitle, inner), eq_imgs

def render_revision_newsletter(payload: dict) -> tuple[str, list[tuple[str, bytes]]]:
    payload = normalize_revision_payload(payload)

    inner = "\n".join([
        card("Recall quiz", list_ol(payload["quiz"])),
        card("Answer key", list_ol(payload["answer_key"])),
        card("Speaking drills", list_ul(payload["speaking_drills"])),
        card("Mini system design prompts", list_ul(payload["design_prompts"])),
        card("Checklist", list_ul(payload["checklist"])),
    ])

    return shell_html(payload["title"], payload["subtitle"], inner), []

# ---------- Prompts (JSON-only) ----------

def lesson_prompt(day_plan: str) -> str:
    template = """
You generate daily ML/DS/LLM interview prep content.

Return ONLY valid JSON (no markdown, no commentary).

Schema:
{
  "title": "short title for today",
  "subtitle": "1-line subtitle",
  "core_intuition": ["bullet", "..."],

  "equations": ["latex-like mathtext string", "..."],

  "qa_sections": [
    {
      "title": "subtopic name",
      "items": [
        {"q": "question", "a": "answer"},
        {"q": "...", "a": "..."}
      ]
    }
  ],

  "pitfalls": ["bullet", "..."],

  "implementation": {
    "sklearn": "python code",
    "toy_data": "python code",
    "practice_notes": ["bullet", "..."]
  },

  "speaking_script": ["bullet", "..."],

  "mini_drill": {
    "practice": [{"q": "question", "a": "answer"}, {"q": "...", "a": "..."}],
    "follow_ups": [{"q": "follow-up question", "a": "short answer"}, {"q": "...", "a": "..."}]
  }
}

ANSWER STYLE (IMPORTANT):
- Make answers INTERVIEW-SIZED and EASY:
  - Target 3–6 sentences total.
  - Sentence 1: direct answer in plain English.
  - Sentences 2–4: key reasoning (max 2 key points).
  - Last sentence: practical detail (what you do in practice / example / tradeoff).
- Avoid long paragraphs. Avoid academic tone. Avoid excess jargon.
- If a term is unavoidable (e.g., “log-sum-exp”), define it in 6–12 simple words.
- Prefer “what/why/how” over derivations.
- If you mention a formula, keep it short and use equations list (not inside answers).

CONTENT COVERAGE:
- qa_sections should total ~10–16 Q/A pairs (not 20) unless topic is huge.
- Prefer high-frequency interview questions.
- equations: 2–4 max.

Mini-drill follow-ups MUST include answers.

Today's plan: __DAY_PLAN__
"""
    return template.replace("__DAY_PLAN__", day_plan).strip()

def revision_prompt(recent_plans: list[str]) -> str:
    recent = "; ".join(recent_plans) if recent_plans else ""
    template = """
You are generating a weekly revision pack.

Return ONLY valid JSON. No markdown. No commentary.

Schema:
{
  "title": "Revision Newsletter",
  "subtitle": "Quiz + drills + mini design prompts",
  "quiz": ["question 1", "... (12 total)"],
  "answer_key": ["answer 1", "... (12 total)"],
  "speaking_drills": ["Explain X in 2 minutes", "... (3 total)"],
  "design_prompts": ["prompt 1 with outline answer", "... (2 total)"],
  "checklist": ["bullet", "..."]
}

This week topics: __RECENT__
"""
    return template.replace("__RECENT__", recent).strip()
# ---------- Model call ----------

def generate_json(prompt: str) -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content or ""
    return extract_json_object(text)

# ---------- Main ----------

def main():
    load_dotenv()
    now = utc_now()

    required = ["OPENAI_API_KEY", "SMTP_HOST", "SMTP_USER", "SMTP_PASS", "TO_EMAIL"]
    for k in required:
        if not os.getenv(k):
            raise RuntimeError(f"Missing env var: {k}")

    state = load_state()
    plans = load_day_plans_from_docx(TOPICS_FILE)

    if already_sent_today(state, now):
        print("Already sent today (UTC). Exiting.")
        return

    day_index = int(state.get("day_index", 0))
    day_index = max(0, min(day_index, len(plans) - 1))

    today_plan = plans[day_index].strip()
    is_revision = today_plan.upper() == "REVISION"

    if is_revision:
        recent = get_last_n_learning(plans, day_index, n=6)
        prompt = revision_prompt(recent)
        subject = f"Revision Newsletter — Day {day_index + 1}"
        payload = generate_json(prompt)
        text_body = json.dumps(payload, indent=2)
        html_body, inline_imgs = render_revision_newsletter(payload)
    else:
        prompt = lesson_prompt(today_plan)
        subject = f"Daily Interview Newsletter — Day {day_index + 1}: {today_plan}"
        payload = generate_json(prompt)
        # Use a readable plain-text fallback (not JSON dump)
        # keep it simple:
        text_body = f"{payload.get('title','')}\n{payload.get('subtitle','')}\n\n" + \
                    "Core intuition:\n- " + "\n- ".join(payload.get("core_intuition", [])) + "\n\n" + \
                    "Pitfalls:\n- " + "\n- ".join(payload.get("pitfalls", []))
        html_body, inline_imgs = render_lesson_newsletter(payload)

    if os.environ.get("DRY_RUN", "0").strip() == "1":
        print(subject)
        print(text_body[:2000])
    else:
        send_email(subject, text_body, html_body, inline_images=inline_imgs)

    write_log(now, subject, text_body)

    # advance
    if day_index + 1 < len(plans):
        state["day_index"] = day_index + 1
    state["last_sent_utc"] = now.isoformat()
    save_state(state)

    print(f"Sent: {subject}")

if __name__ == "__main__":
    main()