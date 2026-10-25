"""
Kick Sesli Klip Botu
--------------------
Yayının SESİNİ dinler. "klip al" (veya ayarladığın tetikleyiciler) duyunca
Kick sohbetine "!clip" yazar -> Botrix klibi otomatik alır.

Akış:
  streamlink (yayını çeker) -> ffmpeg (sesi 16kHz mono'ya çevirir) -> Vosk (Türkçe STT)
  -> tetikleyici duyulursa -> Kick API ile sohbete mesaj.

Ayarlar .env dosyasından okunur (bkz. .env.ornek).
"""

import json
import os
import sys
import time
import subprocess

import requests
from vosk import Model, KaldiRecognizer


def _env_yukle():
    """Yanındaki .env dosyasını ortam değişkenlerine yükler (python-dotenv gerekmez)."""
    yol = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(yol):
        return
    for satir in open(yol, encoding="utf-8"):
        satir = satir.strip()
        if satir and not satir.startswith("#") and "=" in satir:
            k, v = satir.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_env_yukle()

# Vosk (C++) yoldaki Türkçe/ASCII olmayan karakterleri (ör. "Masaüstü") kaldıramaz.
# Script klasörüne geçip modeli GÖRELİ yolla açarak bunu aşıyoruz.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ---------------- AYARLAR (.env) ----------------
KANAL = os.environ.get("KICK_KANAL", "").strip().lower()          # ör: "yayinci_adi"
BOT_TOKEN = os.environ.get("KICK_BOT_TOKEN", "").strip()          # chat:write yetkili token
KOMUT = os.environ.get("KLIP_KOMUTU", "!clip").strip()            # sohbete yazılacak komut
TETIKLEYICILER = [t.strip() for t in os.environ.get(
    "TETIKLEYICILER", "klip al").split(",") if t.strip()]
BEKLEME = int(os.environ.get("BEKLEME_SN", "30"))                 # iki klip arası min süre
GUVEN_ESIGI = float(os.environ.get("GUVEN_ESIGI", "0.85"))        # kelime güveni bu altındaysa alma
ISINMA = float(os.environ.get("ISINMA_SN", "3"))                  # bağlandıktan sonra tetiği susturma süresi
MODEL_KLASORU = os.environ.get("VOSK_MODEL", "model")  # göreli yol (bkz. os.chdir yukarıda)
KALITE = os.environ.get("YAYIN_KALITESI", "worst")               # ses için en düşüğü yeter
BROADCASTER_ID = os.environ.get("KICK_BROADCASTER_ID", "").strip()
# ------------------------------------------------

KICK_CHAT_URL = "https://api.kick.com/public/v1/chat"
SAMPLERATE = 16000


def tetik_bulundu(kelimeler):
    """Tetik ifadesi (ör. 'klip al') ardışık kelimeler olarak geçiyor VE her
    kelimesinin güveni eşiğin üstünde mi? Böylece sadece net söylenince alır."""
    hedefler = [[w.lower() for w in t.split()] for t in TETIKLEYICILER]
    sozcukler = [k.get("word", "").lower() for k in kelimeler]
    for hedef in hedefler:
        n = len(hedef)
        for i in range(len(sozcukler) - n + 1):
            if sozcukler[i:i + n] == hedef:
                if min(kelimeler[i + j].get("conf", 0) for j in range(n)) >= GUVEN_ESIGI:
                    return True
    return False


def kanal_user_id(slug: str):
    """Yayıncının broadcaster_user_id'sini herkese açık uçtan çözer."""
    try:
        r = requests.get(
            f"https://kick.com/api/v2/channels/{slug}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("user_id")
    except Exception as e:
        print(f"user_id çözülemedi: {e}")
    return None


def sohbete_yaz(mesaj: str) -> bool:
    govde = {"type": "user", "content": mesaj}
    if BROADCASTER_ID:
        govde["broadcaster_user_id"] = int(BROADCASTER_ID)
    try:
        r = requests.post(
            KICK_CHAT_URL,
            headers={"Authorization": f"Bearer {BOT_TOKEN}",
                     "Content-Type": "application/json"},
            json=govde,
            timeout=8,
        )
        if r.status_code in (200, 201):
            print(f">>> sohbete yazıldı: {mesaj}")
            return True
        print(f"!!! sohbet hatası {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"!!! sohbet isteği başarısız: {e}")
        return False


def _ffmpeg_yolu():
    yerel = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg.exe")
    return yerel if os.path.exists(yerel) else os.environ.get("FFMPEG_YOL", "ffmpeg")


def ses_akisi_baslat():
    """streamlink | ffmpeg zinciri; ffmpeg stdout'tan ham PCM verir."""
    streamlink = subprocess.Popen(
        [sys.executable, "-m", "streamlink", "--stdout",
         f"https://kick.com/{KANAL}", KALITE],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    ffmpeg = subprocess.Popen(
        [_ffmpeg_yolu(), "-loglevel", "quiet", "-i", "pipe:0",
         "-f", "s16le", "-ar", str(SAMPLERATE), "-ac", "1", "pipe:1"],
        stdin=streamlink.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return streamlink, ffmpeg


def _slug_coz(girdi: str) -> str:
    """'https://kick.com/abc?x=1' veya 'abc' -> 'abc'."""
    g = girdi.replace("﻿", "").strip()  # görünmez BOM/boşlukları at
    if "kick.com/" in g:
        g = g.split("kick.com/", 1)[1]
    return g.strip("/").split("?")[0].split("/")[0].lower()


def _kanal_kaydet(slug: str):
    """Seçilen kanalı .env'e KICK_KANAL olarak yazar (bir dahaki açılışta Enter'la gelir)."""
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    satirlar, bulundu = [], False
    if os.path.exists(yol):
        satirlar = open(yol, encoding="utf-8").read().splitlines()
    for i, s in enumerate(satirlar):
        if s.startswith("KICK_KANAL="):
            satirlar[i] = f"KICK_KANAL={slug}"
            bulundu = True
    if not bulundu:
        satirlar.append(f"KICK_KANAL={slug}")
    open(yol, "w", encoding="utf-8").write("\n".join(satirlar) + "\n")


def _kanal_sec():
    """Açılışta yayın linkini/kanalını sorar, broadcaster_user_id'yi çözer."""
    while True:
        varsayilan = KANAL
        istem = f"Yayın linki veya kanal adı" + (f" (Enter = {varsayilan})" if varsayilan else "") + ": "
        girilen = input(istem).strip()
        slug = _slug_coz(girilen) if girilen else varsayilan
        if not slug:
            print("Bir kanal gir (ör. https://kick.com/mpagee veya mpagee).")
            continue
        print(f"'{slug}' çözülüyor...")
        uid = kanal_user_id(slug)
        if not uid:
            print(f"'{slug}' bulunamadı ya da çevrimdışı. Tekrar dene.")
            continue
        _kanal_kaydet(slug)
        return slug, str(uid)


def main():
    if not BOT_TOKEN:
        print("KICK_BOT_TOKEN yok — önce 'python token_al.py' çalıştır.")
        sys.exit(1)
    if not os.path.isdir(MODEL_KLASORU):
        print(f"Vosk Türkçe modeli yok: {MODEL_KLASORU}")
        sys.exit(1)

    global KANAL, BROADCASTER_ID
    KANAL, BROADCASTER_ID = _kanal_sec()

    model = Model(MODEL_KLASORU)
    rec = KaldiRecognizer(model, SAMPLERATE)   # grammar YOK: tam model -> çok daha az sahte tetik
    rec.SetWords(True)                         # kelime bazında güven skoru için

    son_klip = 0.0
    print(f"Kanal: {KANAL} (id {BROADCASTER_ID}) | tetikleyiciler: {TETIKLEYICILER} | "
          f"güven>={GUVEN_ESIGI} | komut: {KOMUT}")

    while True:  # yayın koparsa yeniden bağlan
        sl = ff = None
        try:
            print("Yayına bağlanılıyor / ses dinleniyor...")
            sl, ff = ses_akisi_baslat()
            baglanma = time.time()  # ısınma: ilk saniyelerdeki sahte tetiği yok say
            while True:
                data = ff.stdout.read(4000)
                if not data:
                    print("Ses akışı bitti (yayın kapandı?). 10 sn sonra yeniden denenecek.")
                    break
                if time.time() - baglanma < ISINMA:
                    rec.AcceptWaveform(data)  # modeli besle ama tetikleme
                    continue
                if rec.AcceptWaveform(data):
                    sonuc = json.loads(rec.Result())
                    metin = sonuc.get("text", "")
                    if not metin:
                        continue
                    kelimeler = sonuc.get("result", [])
                    print(f"duydum: {metin}")
                    if tetik_bulundu(kelimeler):
                        if time.time() - son_klip >= BEKLEME:
                            if sohbete_yaz(KOMUT):
                                son_klip = time.time()
                        else:
                            kalan = int(BEKLEME - (time.time() - son_klip))
                            print(f"... bekleme modunda ({kalan} sn), atlandı")
        except KeyboardInterrupt:
            print("\nKapatıldı.")
            return
        except Exception as e:
            print(f"Hata: {e}")
        finally:
            for p in (ff, sl):
                if p:
                    try:
                        p.kill()
                    except Exception:
                        pass
        time.sleep(10)


if __name__ == "__main__":
    main()
