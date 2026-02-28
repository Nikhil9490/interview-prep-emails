# interview-prep-emails

📬 # Daily AI Interview Prep Emailer

A fully automated system that sends me one structured AI/ML interview lesson every morning at 10:00 AM.

Built with Python, OpenAI API, and GitHub Actions.

No servers. No cron jobs. No manual effort.

🚀 What This Project Does

Every day at 10AM (New York time), this system:

Selects the next topic from a curated ML/AI interview roadmap

Generates a high-quality structured lesson using GPT

Formats it as a clean, newsletter-style email

Sends it to my inbox

Updates internal state to move to the next topic

It automatically progresses through topics like:

Linear Regression

Logistic Regression

Naive Bayes

SVM

Tree-based models

Deep Learning

NLP

RAG & LLM systems

No repeats. No skipping. No manual tracking.

🧠 Why I Built This

Interview preparation often fails because of inconsistency.

Instead of “studying when I feel like it,” I built a system that forces daily exposure to core concepts — structured, concise, and interview-focused.

This project combines:

Automation

LLM content generation

Email delivery systems

GitHub Actions scheduling

State persistence across runs

It’s basically a self-updating AI study pipeline.

🛠 Tech Stack

Python 3.11

OpenAI API

SMTP (Gmail App Password)

GitHub Actions (scheduled automation)

python-docx (topic source)

JSON-based state tracking

⚙️ How It Works (Architecture)
GitHub Actions (Hourly Trigger)
            ↓
DST-safe 10AM NY Gate
            ↓
Run main.py
            ↓
Generate Lesson via OpenAI
            ↓
Send Styled HTML Email
            ↓
Update state.json
            ↓
Commit state back to repo

Key design decision:

The workflow commits state.json back to the repository so the system remembers what was sent last.

This makes the automation fully persistent without needing a database.

📅 Scheduling Logic

The workflow runs hourly in UTC, but only proceeds if the current time in America/New_York is 10AM.

This makes it DST-safe.

schedule:
  - cron: "0 * * * *"

Then inside the job:

HOUR=$(TZ=America/New_York date +%H)
🔐 Required GitHub Secrets

Set these in:

Repo → Settings → Secrets and variables → Actions

OPENAI_API_KEY

OPENAI_MODEL

SMTP_HOST

SMTP_PORT

SMTP_USER

SMTP_PASS

TO_EMAIL

If using Gmail:

SMTP_HOST → smtp.gmail.com

SMTP_PORT → 587

SMTP_PASS → Google App Password (not your normal password)

🧩 State Management

state.json tracks:

{
  "day_index": 0,
  "last_sent_utc": null
}

After each successful run, GitHub Actions commits the updated file so the next topic is sent tomorrow.

🧪 Running Locally
pip install -r requirements.txt
python main.py

Make sure .env is configured locally if testing outside GitHub.

📈 Why This Is Interesting

This project demonstrates:

LLM prompt engineering for structured content

Production automation without a server

Safe state persistence in CI/CD

Timezone-aware scheduling

Email formatting with HTML

Practical DevOps thinking for small AI tools

It’s a lightweight but realistic automation system — the kind that’s actually useful.

🏁 Status

Fully automated.
Runs daily at 10:00 AM New York time.
Advances topics automatically.

No manual intervention required.
