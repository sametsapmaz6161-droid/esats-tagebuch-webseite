"""Kapitel-Timer: Einmalig bei Deployment starten, später fällige E-Mails versenden."""
import json
import os
import smtplib
import subprocess
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

STATUS = Path("kapitel-status.json")
EMPFAENGER = "sametsapmaz6161@gmail.com"
URL = "https://sametsapmaz6161-droid.github.io/esats-tagebuch-webseite/"
KAPITEL = 30


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


def jetzt():
    return datetime.now(timezone.utc)


if os.environ.get("EVENT_NAME") == "push":
    # Der Zeitpunkt der Bereitstellung des neuen Kapitelplans ist die Startmarke.
    status = {"start_at": jetzt().isoformat().replace("+00:00", "Z"), "last_notified": 1}
    speichern(status, "Kapitel-Freischaltung starten [skip ci]")
    print("Gemeinsamer Kapitelstart gesetzt:", status["start_at"])
else:
    if not STATUS.exists():
        raise SystemExit("kapitel-status.json fehlt. Zuerst den Workflow mit index.html committen.")
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    start = datetime.fromisoformat(status["start_at"].replace("Z", "+00:00"))
    minuten = max(0, int((jetzt() - start).total_seconds() // 60))
    freigeschaltet = min(KAPITEL, 1 + minuten)
    zuletzt = int(status.get("last_notified", 1))
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
