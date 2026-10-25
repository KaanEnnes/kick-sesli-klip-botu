"""
token_al.py — Kick bot token'ını tarayıcıdan OTOMATİK alır ve .env'e yazar.

Çalıştır:  python token_al.py
Tarayıcı açılır -> Kick'te "İzin ver" dersin -> token .env'e kaydedilir. Hepsi bu.

Önce .env içine KICK_CLIENT_ID ve KICK_CLIENT_SECRET'i koy
(https://kick.com/settings/developer -> uygulama oluştur, redirect: http://localhost:8765/callback).
"""

import base64
import hashlib
import os
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

AUTH = "https://id.kick.com/oauth/authorize"
TOKEN = "https://id.kick.com/oauth/token"
REDIRECT = "http://localhost:8765/callback"
SCOPE = "chat:write"
ENV = os.path.join(os.path.dirname(__file__), ".env")


def env_oku():
    d = {}
    if os.path.exists(ENV):
        for satir in open(ENV, encoding="utf-8"):
            if "=" in satir and not satir.strip().startswith("#"):
                k, v = satir.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def env_yaz(anahtar, deger):
    satirlar, bulundu = [], False
    if os.path.exists(ENV):
        satirlar = open(ENV, encoding="utf-8").read().splitlines()
    for i, s in enumerate(satirlar):
        if s.startswith(anahtar + "="):
            satirlar[i] = f"{anahtar}={deger}"
            bulundu = True
    if not bulundu:
        satirlar.append(f"{anahtar}={deger}")
    open(ENV, "w", encoding="utf-8").write("\n".join(satirlar) + "\n")


def main():
    env = env_oku()
    cid = env.get("KICK_CLIENT_ID", "")
    csecret = env.get("KICK_CLIENT_SECRET", "")
    if not cid or not csecret:
        print("Önce .env içine KICK_CLIENT_ID ve KICK_CLIENT_SECRET ekle.")
        return

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    url = AUTH + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "code_challenge": challenge,
        "code_challenge_method": "S256", "state": state,
    })

    kod = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            kod["code"] = q.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>Tamam, bu sekmeyi kapatabilirsin.</h2>".encode("utf-8"))
        def log_message(self, *a):
            pass

    print("Tarayıcı açılıyor, Kick'te 'İzin ver' de...")
    webbrowser.open(url)
    srv = HTTPServer(("localhost", 8765), H)
    srv.handle_request()  # tek isteği bekle

    if not kod.get("code"):
        print("Kod alınamadı.")
        return

    r = requests.post(TOKEN, data={
        "grant_type": "authorization_code", "client_id": cid,
        "client_secret": csecret, "redirect_uri": REDIRECT,
        "code": kod["code"], "code_verifier": verifier,
    }, timeout=10)
    if r.status_code != 200:
        print("Token hatası:", r.status_code, r.text[:300])
        return

    tok = r.json()
    env_yaz("KICK_BOT_TOKEN", tok["access_token"])
    if tok.get("refresh_token"):
        env_yaz("KICK_REFRESH_TOKEN", tok["refresh_token"])
    print(">>> Token .env'e kaydedildi. Artık 'python bot.py' çalıştırabilirsin.")


if __name__ == "__main__":
    main()
