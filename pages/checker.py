import streamlit as st
import pandas as pd
import requests
import ssl
import socket
from datetime import datetime
from time import time, sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# ─── Konfiguracja strony ─────────────────────────────
st.set_page_config(page_title="Audyt Domen", layout="wide")
st.title("🔍 Audyt domen – HTTP + SSL")
st.caption("Wklej domeny lub wgraj plik CSV. Sprawdzę status i certyfikat SSL każdej z nich.")

# ─── Funkcje pomocnicze ──────────────────────────────

def check_ssl_cert(domain, port=443, timeout=5):
    """Zwraca szczegóły certyfikatu SSL dla danej domeny."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        # Pobieramy daty i wystawcę
        not_after = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        not_before = datetime.strptime(cert['notBefore'], "%b %d %H:%M:%S %Y %Z")
        issuer = dict(x[0] for x in cert['issuer'])
        issuer_str = issuer.get('organizationName', 'Nieznany')
        days_left = (not_after - datetime.now()).days
        return {
            "ssl_valid": True,
            "issuer": issuer_str,
            "not_before": not_before.strftime("%Y-%m-%d"),
            "not_after": not_after.strftime("%Y-%m-%d"),
            "days_left": days_left,
            "ssl_error": ""
        }
    except Exception as e:
        return {
            "ssl_valid": False,
            "issuer": "",
            "not_before": "",
            "not_after": "",
            "days_left": None,
            "ssl_error": str(e)
        }

def check_domain(domain):
    """Pełne sprawdzenie pojedynczej domeny."""
    url = f"https://{domain}"
    result = {
        "domain": domain,
        "status_code": None,
        "http_ok": False,
        "http_error": "",
        "ssl_valid": False,
        "ssl_issuer": "",
        "ssl_expiry": "",
        "ssl_days_left": None,
        "ssl_error": "",
        "response_time_s": None
    }
    start = time()
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["http_ok"] = resp.ok
        result["response_time_s"] = round(time() - start, 2)
    except Exception as e:
        result["http_error"] = str(e)
        result["response_time_s"] = round(time() - start, 2)

    # SSL – sprawdzamy niezależnie, nawet jeśli HTTP padło
    ssl_info = check_ssl_cert(domain)
    result.update({
        "ssl_valid": ssl_info["ssl_valid"],
        "ssl_issuer": ssl_info["issuer"],
        "ssl_expiry": ssl_info["not_after"],
        "ssl_days_left": ssl_info["days_left"],
        "ssl_error": ssl_info["ssl_error"]
    })
    return result

def parse_domains_from_csv(text):
    """Próbuje wyciągnąć domeny z wklejonego CSV (pierwsza kolumna, zakładając nagłówek 'domain' lub po prostu pierwsza)."""
    try:
        df = pd.read_csv(io.StringIO(text))
        # Szukamy kolumny 'domain' (case-insensitive), jeśli nie ma, bierzemy pierwszą
        cols = [c.lower() for c in df.columns]
        if 'domain' in cols:
            col_name = df.columns[cols.index('domain')]
        else:
            col_name = df.columns[0]
        domains = df[col_name].dropna().astype(str).str.strip().tolist()
        # Oczyszczamy z http://, https://
        domains = [d.replace("http://", "").replace("https://", "").rstrip("/") for d in domains]
        return [d for d in domains if d]
    except:
        return None

# ─── Interfejs ────────────────────────────────────────

# Wybór trybu wprowadzania
input_mode = st.radio(
    "Sposób wprowadzenia domen:",
    ["Wklej listę domen (jedna na linię)", "Wklej CSV (z Google Sheets, Excela itp.)", "Wgraj plik CSV"],
    horizontal=True
)

domains_list = []

if input_mode == "Wklej listę domen (jedna na linię)":
    raw = st.text_area(
        "Wklej domeny (bez http://, każda w nowej linii):",
        height=200,
        placeholder="example.com\ngoogle.com\n..."
    )
    if raw:
        domains_list = [line.strip().rstrip("/") for line in raw.splitlines() if line.strip()]

elif input_mode == "Wklej CSV (z Google Sheets, Excela itp.)":
    csv_paste = st.text_area(
        "Wklej zawartość pliku CSV (pierwsza kolumna = domena):",
        height=200,
        placeholder="domain\nexample.com\ngoogle.com"
    )
    if csv_paste:
        parsed = parse_domains_from_csv(csv_paste)
        if parsed:
            domains_list = parsed
            st.success(f"Znaleziono {len(domains_list)} domen.")
        else:
            st.error("Nie udało się odczytać domen z CSV. Upewnij się, że dane są w formacie CSV z kolumną 'domain'.")

else:  # wgraj plik
    uploaded = st.file_uploader("Wybierz plik CSV", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            cols = [c.lower() for c in df.columns]
            if 'domain' in cols:
                col_name = df.columns[cols.index('domain')]
            else:
                col_name = df.columns[0]
            domains_list = df[col_name].dropna().astype(str).str.strip().tolist()
            domains_list = [d.replace("http://", "").replace("https://", "").rstrip("/") for d in domains_list]
            domains_list = [d for d in domains_list if d]
            st.success(f"Wczytano {len(domains_list)} domen z pliku.")
        except Exception as e:
            st.error(f"Błąd odczytu pliku: {e}")

# ─── Przycisk startu ─────────────────────────────────
if st.button("🚀 Rozpocznij audyt", type="primary", use_container_width=True):
    if not domains_list:
        st.warning("Najpierw wprowadź domeny.")
    else:
        # Usuwamy ewentualne duplikaty
        domains_list = list(dict.fromkeys(domains_list))
        total = len(domains_list)
        st.info(f"Sprawdzam {total} domen...")

        results = []
        progress = st.progress(0, text="Postęp...")
        
        # Równoległe sprawdzanie dla szybkości (ale z limitem, żeby nie przeciążać)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_domain, d): d for d in domains_list}
            for idx, future in enumerate(as_completed(futures), 1):
                res = future.result()
                results.append(res)
                progress.progress(idx / total, text=f"{idx}/{total} – {res['domain']}")
        
        progress.empty()
        df = pd.DataFrame(results)
        
        # ─── Podsumowanie błędów ──────────────────────
        st.subheader("📊 Wyniki")
        ok_count = df["http_ok"].sum()
        ssl_ok_count = df["ssl_valid"].sum()
        problematic = df[~df["http_ok"] | ~df["ssl_valid"]]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ HTTP OK", f"{ok_count}/{total}")
        col2.metric("🔒 SSL OK", f"{ssl_ok_count}/{total}")
        col3.metric("⚠️ Problemy", len(problematic))
        
        if not problematic.empty:
            st.subheader("❗ Lista domen z problemami")
            # Wybieramy istotne kolumny do wyświetlenia
            show_cols = ["domain", "status_code", "http_error", "ssl_valid", "ssl_expiry", "ssl_days_left", "ssl_error"]
            st.dataframe(problematic[show_cols], use_container_width=True)
        else:
            st.success("Wszystkie domeny sprawne – brawo! 🎉")
        
        # ─── Pełna tabela ─────────────────────────────
        with st.expander("Zobacz szczegółową tabelę wszystkich domen"):
            st.dataframe(df, use_container_width=True)
        
        # ─── Eksport do CSV ───────────────────────────
        csv_full = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Pobierz pełne wyniki (CSV)",
            data=csv_full,
            file_name=f"audyt_domen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
