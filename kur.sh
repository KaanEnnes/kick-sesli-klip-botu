#!/usr/bin/env bash
# Ücretsiz Linux sunucuda TEK KOMUT: bağımlılıkları kurar, Türkçe modeli indirir, botu başlatır.
# Kullanım:   bash kur.sh
set -e
cd "$(dirname "$0")"

echo "[1/4] Sistem paketleri (ffmpeg, python, streamlink)..."
if command -v apt-get >/dev/null; then
  sudo apt-get update -y
  sudo apt-get install -y ffmpeg python3 python3-pip python3-venv unzip wget streamlink
fi

echo "[2/4] Python ortamı + kütüphaneler..."
python3 -m venv .venv
. .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet vosk requests streamlink

echo "[3/4] Vosk Türkçe modeli..."
if [ ! -d "model" ]; then
  wget -q https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip -O tr.zip
  unzip -q tr.zip
  mv vosk-model-small-tr-0.3 model
  rm tr.zip
fi

echo "[4/4] Bot başlıyor..."
exec python3 bot.py
