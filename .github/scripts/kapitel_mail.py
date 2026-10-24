"""Esats Tagebuch: Kapitel taeglich um 20:00 Uhr (Europe/Berlin) freigeben."""
import json
import os
import smtplib
import subprocess
from datetime import datetime, timezone, time, timedelta
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

STATUS = Path("kapitel-status.json")
EMPFAENGER = "Esat.sapmaz@yahoo.de"
URL = "https://sametsapmaz6161-droid.github.io/esats-tagebuch-webseite/"
KAPITEL = 30
BERLIN = ZoneInfo("Europe/Berlin")
# Der feste erste Veröffentlichungstermin: Samstag, 24. Oktober 2026, 20 Uhr MESZ.
ERSTER_START = datetime(2026, 10, 24, 20, 0, tzinfo=BERLIN)

def git(*args):
    subprocess.run(["git", *args], check=True)

def speichern(status, nachricht):
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", str(STATUS))
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        return
    git("commit", "-m", nachricht)
    git("push")

def kapitel_termin(index):
    tag = ERSTER_START.date() + timedelta(days=index)
    return datetime.combine(tag, time(20, 0), tzinfo=BERLIN)

if os.environ.get("RESET_KAPITEL", "").lower() == "true":
    status = {"start_at": ERSTER_START.isoformat(), "last_notified": 0}
    speichern(status, "Taegliche Kapitel ab 24.10.2026 20 Uhr starten [skip ci]")
    print("Alle Kapitel gesperrt bis:", status["start_at"])
else:
    if not STATUS.exists():
        raise SystemExit("kapitel-status.json fehlt. Bitte zuerst Reset ausführen.")
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    # Schutz vor altem Minuten-Teststatus: niemals versehentlich Testkapitel mailen.
    if datetime.fromisoformat(status["start_at"].replace("Z", "+00:00")) != ERSTER_START:
        raise SystemExit("Noch alter Teststatus aktiv. Bitte den Reset-Workflow ausführen.")
    jetzt = datetime.now(timezone.utc)
    freigeschaltet = sum(jetzt >= kapitel_termin(i).astimezone(timezone.utc) for i in range(KAPITEL))
    zuletzt = int(status.get("last_notified", 0))
    print(f"Freigeschaltet: {freigeschaltet}, zuletzt benachrichtigt: {zuletzt}")
    if freigeschaltet <= zuletzt:
        raise SystemExit(0)
    absender = os.environ.get("GMAIL_USER")
    passwort = os.environ.get("GMAIL_APP_PASSWORD")
    if not absender or not passwort:
        raise SystemExit("GMAIL_USER oder GMAIL_APP_PASSWORD fehlt.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(absender, passwort)
        for nummer in range(zuletzt + 1, freigeschaltet + 1):
            mail = EmailMessage()
            mail["From"] = absender
            mail["To"] = EMPFAENGER
            mail["Subject"] = f"📖 Esats Tagebuch – Kapitel {nummer} ist online!"
            mail.set_content(
                f"Kapitel {nummer} von Esats Tagebuch wurde freigeschaltet! ❤️\n\n"
                f"Hier kannst du weiterlesen:\n{URL}\n\nViel Spaß beim Lesen! 📖"
            )
            smtp.send_message(mail)
            status["last_notified"] = nummer
            speichern(status, f"Kapitel {nummer} per E-Mail gemeldet [skip ci]")
            print(f"E-Mail für Kapitel {nummer} versendet.")
