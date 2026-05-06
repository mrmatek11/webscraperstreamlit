# SNAP — Web Snapshot Tool (Streamlit Frontend)

Webowy interfejs dla snap.py — scraper stron z HTML, assetami i screenshotami.

## Zawartość projektu

```
snap_web/
├── app.py              ← główna aplikacja Streamlit
├── snap.py             ← silnik scrapera (Twój plik)
├── requirements.txt    ← zależności Python
├── packages.txt        ← zależności systemowe (dla Streamlit Cloud)
├── post_install.sh     ← instalacja Playwright browsers
└── .streamlit/
    └── config.toml     ← konfiguracja wyglądu
```

## Deployment na Streamlit Cloud (share.streamlit.io)

### 1. GitHub
Wrzuć cały folder `snap_web/` jako nowe repozytorium GitHub (publiczne lub prywatne).

### 2. Streamlit Cloud
1. Wejdź na https://share.streamlit.io
2. Kliknij **New app**
3. Wybierz swoje repo, branch `main`, plik `app.py`
4. Kliknij **Deploy**

### 3. Po deployu — uruchom playwright
Na Streamlit Cloud w **App settings → Secrets** NIE MA potrzeby nic dodawać.

Playwright zainstaluje się automatycznie przez `packages.txt` i `post_install.sh`.

Jeśli `post_install.sh` nie odpalił się sam, dodaj do `requirements.txt` na końcu:
```
playwright install chromium
```
albo dodaj plik `setup.sh`:
```bash
#!/bin/bash
pip install playwright
playwright install chromium
```

## Odłączenie od GitHub (Streamlit OAuth)

Wejdź na: https://github.com/settings/applications → **Authorized OAuth Apps** → **Streamlit** → **Revoke**

## Tryby działania

| Tryb | Co robi |
|------|---------|
| `screenshots` | Tylko screenshoty PNG, szybko |
| `full` | HTML + wszystkie assety + screenshoty, ZIP |
| `crawl` | Auto-discovery z sitemap + linków, potem full |
| `clean-*` | Najpierw niszczy popupy/cookie-bannery, potem wybrany tryb |

## Lokalne uruchomienie

```bash
pip install -r requirements.txt
playwright install chromium
streamlit run app.py
```
