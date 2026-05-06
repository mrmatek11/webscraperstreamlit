# SNAP — Web Snapshot Tool (Streamlit Frontend)

## Zawartość projektu

```
snap_web/
├── app.py              ← główna aplikacja Streamlit
├── snap.py             ← silnik scrapera
├── requirements.txt    ← zależności Python
├── packages.txt        ← minimalne zależności systemowe
├── setup.sh            ← instalacja Playwright browsers
└── .streamlit/
    └── config.toml
```

## Deployment na Streamlit Cloud

1. Wrzuć folder jako repo GitHub (może być prywatne)
2. share.streamlit.io → New app → wybierz repo → `app.py` → Deploy
3. Pierwsze uruchomienie zainstaluje Chromium (~5 min)
4. Zobaczysz ✓ Playwright Chromium gotowy

## Odłączenie GitHub OAuth
GitHub → Settings → Applications → Authorized OAuth Apps → Streamlit → Revoke

## Lokalne uruchomienie
```bash
pip install -r requirements.txt
python -m playwright install chromium
streamlit run app.py
```
