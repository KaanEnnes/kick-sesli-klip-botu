# Kick Sesli Klip Botu

Kick yayınının **sesini** dinler; yayında biri **"klip al"** (veya "klip") deyince
yayın sohbetine `!clip` yazar ve Botrix gibi bir klip botu klibi alır.

Botrix'in `!clip` komutunun sesli hâli: sohbete yazmana gerek yok, söylemen yeter.

## Nasıl çalışır

```
streamlink → ffmpeg → Vosk (offline Türkçe STT) → "klip al" → Kick API: sohbete !clip
   yayın     16kHz ses     yazıya çevirme          tetik         (chat:write)
```

- Klip oluşturmayı Kick API'si desteklemiyor, bu yüzden sohbete `!clip` yazılır —
  kanalda `!clip` komutu (Botrix vb.) aktif olmalı.
- Ses tanıma tamamen **offline** (Vosk küçük Türkçe model), internet/GPU gerekmez.
- Yanlış tetiklemeyi azaltmak için: tam dil modeli + ardışık kelime eşleşmesi +
  yüksek güven eşiği (0.9) + bağlantı sonrası kısa ısınma.

## Gereksinimler

- Python 3.10+
- `ffmpeg` ve `streamlink`
- Vosk Türkçe model: `vosk-model-small-tr-0.3`
- Kick developer app (OAuth, `chat:write` yetkisi)

## Kurulum

### Linux (tek komut)

```bash
bash kur.sh
```

Bağımlılıkları kurar, Türkçe modeli indirir, botu başlatır.

### Windows

```powershell
pip install vosk requests streamlink
```

`ffmpeg`'i indirip `bin/ffmpeg.exe` olarak koy, modeli indirip `model/` klasörüne aç:
<https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip>

## Kick token'ı alma

1. <https://kick.com/settings/developer> → yeni uygulama oluştur
2. Redirect URL: `http://localhost:8765/callback`
3. `client_id` ve `client_secret`'i `.env`'e yaz
4. Token'ı al (tarayıcıdan tek tık):

```bash
python token_al.py
```

## Kullanım

```bash
python bot.py
```

Açılışta yayın linkini/kanal adını sorar (Enter = son kullanılan). Bağlanır,
dinlemeye başlar; "klip al" duyunca sohbete `!clip` yazar.

Windows'ta `baslat.bat`'a (veya masaüstündeki kısayola) çift tıklaman yeter.

## Ayarlar (`.env`)

| Anahtar | Açıklama | Varsayılan |
|---|---|---|
| `KICK_CLIENT_ID` / `KICK_CLIENT_SECRET` | Developer app bilgileri | — |
| `KICK_BOT_TOKEN` | `token_al.py` doldurur | — |
| `KICK_KANAL` | Son kullanılan kanal (hatırlanır) | — |
| `KLIP_KOMUTU` | Sohbete yazılacak komut | `!clip` |
| `TETIKLEYICILER` | Tetik kelimeler (virgülle) | `klip al,klip` |
| `GUVEN_ESIGI` | Alt güven sınırı (0–1) | `0.9` |
| `BEKLEME_SN` | İki klip arası min. süre | `30` |
| `ISINMA_SN` | Bağlantı sonrası susma süresi | `3` |
| `YAYIN_KALITESI` | streamlink kalitesi | `worst` |

## Notlar

- Bot, yayının sesini doğrudan Kick'ten çeker; izleyici olarak çalışır, yayıncı olman gerekmez.
- Tek `klip` kelimesi normal konuşmada da geçebilir; fazla tetiklerse `TETIKLEYICILER`'i
  sadece `klip al` yap.
- PC açıkken çalışır. Sürekli açık bir sunucu istersen `kur.sh` herhangi bir Linux VPS'te çalışır.
