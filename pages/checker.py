import streamlit as st
import pandas as pd
import requests
import ssl
import socket
import re
import io
import json
import time as _time
import urllib3
import concurrent.futures
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="CHECKER — Domain Auditor", layout="wide",
                   initial_sidebar_state="collapsed")

# ── Shared CSS (matches app.py theme) ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'JetBrains Mono',monospace}
.stApp{background:#1a1918;color:#ccc8c2}
.block-container{padding-top:2rem;max-width:1400px}
.stTextArea textarea,.stTextInput input{background:#222120!important;border:1px solid #353331!important;color:#ccc8c2!important;font-family:'JetBrains Mono',monospace!important;font-size:.8rem!important;border-radius:6px!important}
.stTextArea textarea:focus,.stTextInput input:focus{border-color:#8a8078!important;box-shadow:0 0 0 1px #8a8078!important}
.stButton>button{background:#3d3835!important;color:#ccc8c2!important;border:1px solid #4a4540!important;font-family:'JetBrains Mono',monospace!important;font-weight:700!important;font-size:.85rem!important;border-radius:6px!important;padding:.5rem 1.5rem!important}
.stButton>button:hover{background:#4d4845!important;border-color:#5a5550!important}
.stButton>button:disabled{background:#2a2826!important;color:#5a5550!important;border-color:#353331!important}
.stDownloadButton>button{background:#222120!important;color:#b0a89e!important;border:1px solid #4a4540!important;font-family:'JetBrains Mono',monospace!important;font-weight:700!important;border-radius:6px!important}
.stProgress>div>div>div>div{background:#8fa88e!important}
.stTabs [data-baseweb="tab-list"]{background:#222120;border-bottom:1px solid #353331}
.stTabs [data-baseweb="tab"]{font-family:'JetBrains Mono',monospace!important;font-size:.78rem!important;color:#7a7672!important;background:transparent!important}
.stTabs [aria-selected="true"]{color:#b0a89e!important;border-bottom:2px solid #b0a89e!important}
.stSelectbox>div>div{background:#222120!important;border-color:#353331!important;color:#ccc8c2!important;font-family:'JetBrains Mono',monospace!important;font-size:.8rem!important}
.stSlider label,.stCheckbox label,.stRadio label{color:#9a9590!important;font-size:.8rem!important}
.stSlider>div>div>div{background:#353331!important}
.stSlider>div>div>div>div{background:#8fa88e!important}
.stNumberInput input{background:#222120!important;border:1px solid #353331!important;color:#ccc8c2!important;font-family:'JetBrains Mono',monospace!important}
.stFileUploader label{color:#9a9590!important;font-size:.8rem!important}
.section-header{font-size:.7rem;color:#7a7672;text-transform:uppercase;letter-spacing:2px;margin-bottom:.5rem;margin-top:1rem;border-bottom:1px solid #2d2b29;padding-bottom:.3rem}
.metric-card{background:#222120;border:1px solid #2d2b29;border-radius:6px;padding:1rem;text-align:center}
.metric-label{font-size:.6rem;color:#5a5550;text-transform:uppercase;letter-spacing:1px;margin-bottom:.3rem}
.metric-value{font-size:1.6rem;font-weight:700;color:#b0a89e}
.metric-sub{font-size:.65rem;color:#7a7672;margin-top:.2rem}
.status-ok{color:#8fa88e}
.status-err{color:#c4766e}
.status-warn{color:#b8a472}
.status-info{color:#8fa4b8}
.tag{display:inline-block;padding:2px 8px;border-radius:3px;font-size:.65rem;font-weight:700;margin:1px}
.tag-ok{background:#1e2a1e;color:#8fa88e;border:1px solid #2a3a2a}
.tag-err{background:#2a1e1e;color:#c4766e;border:1px solid #3a2a2a}
.tag-warn{background:#2a261e;color:#b8a472;border:1px solid #3a3228}
.tag-info{background:#1e222a;color:#8fa4b8;border:1px solid #28323a}
.tag-nolabel{background:#222120;color:#7a7672;border:1px solid #353331}
.results-table{width:100%;border-collapse:collapse;font-size:.72rem}
.results-table th{background:#222120;color:#7a7672;text-transform:uppercase;font-size:.6rem;letter-spacing:1px;padding:6px 8px;text-align:left;border-bottom:1px solid #353331;position:sticky;top:0}
.results-table td{padding:5px 8px;border-bottom:1px solid #2d2b29;vertical-align:top;color:#9a9590}
.results-table tr:hover td{background:#1e1d1c}
.problems-box{background:#2a2220;border:1px solid #c4766e;border-radius:6px;padding:.8rem 1rem;margin-bottom:1rem;font-size:.75rem;color:#c4766e}
.success-box{background:#1e2a1e;border:1px solid #353331;border-radius:6px;padding:.8rem 1rem;margin-bottom:1rem;font-size:.75rem;color:#8fa88e}
.info-box{background:#1e222a;border:1px solid #353331;border-radius:6px;padding:.8rem 1rem;margin-bottom:1rem;font-size:.75rem;color:#8fa4b8}
</style>
""", unsafe_allow_html=True)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""<div style="background:#222120;border:1px solid #2d2b29;border-radius:6px;
padding:0.8rem 1.2rem;margin-bottom:1.5rem;font-family:'JetBrains Mono',monospace;
display:flex;align-items:baseline;gap:1rem;">
<span style="font-size:1.1rem;font-weight:700;color:#b0a89e;letter-spacing:1px;">checker</span>
<span style="font-size:0.7rem;color:#5a5550;">domain auditor  ·  HTTP / SSL / DNS / Redirects</span>
<span style="margin-left:auto;font-size:0.68rem;color:#5a5550;">
<a href="/" style="color:#8fa4b8;text-decoration:none;">[ snap ]</a>
</span>
</div>""", unsafe_allow_html=True)

# ── CHECK FUNCTIONS ───────────────────────────────────────────────────────────

SESSION_OPTIONS = requests.Session()

def check_ssl_cert(domain, port=443, timeout=8):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        not_after = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        not_before = datetime.strptime(cert['notBefore'], "%b %d %H:%M:%S %Y %Z")
        issuer = dict(x[0] for x in cert['issuer'])
        issuer_str = issuer.get('organizationName', 'nieznany')
        san = cert.get('subjectAltName', [])
        sans = [v for t, v in san if t == 'DNS']
        days_left = (not_after - datetime.now()).days
        return {"ssl_valid": True, "issuer": issuer_str,
                "not_before": not_before.strftime("%Y-%m-%d"),
                "not_after": not_after.strftime("%Y-%m-%d"),
                "days_left": days_left, "sans": ", ".join(sans[:5]),
                "ssl_error": ""}
    except Exception as e:
        return {"ssl_valid": False, "issuer": "", "not_before": "",
                "not_after": "", "days_left": None, "sans": "",
                "ssl_error": str(e)[:120]}

def check_dns(domain):
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, 'A', lifetime=5)
        ips = [r.address for r in answers]
        try:
            mxs = dns.resolver.resolve(domain, 'MX', lifetime=5)
            mx = [f"{r.exchange}(pri:{r.preference})" for r in mxs]
        except Exception:
            mx = []
        return {"dns_ok": True, "a_records": ", ".join(ips), "mx_records": "; ".join(mx)}
    except ImportError:
        # fallback without dnspython
        try:
            ips = socket.getaddrinfo(domain, None, socket.AF_INET)
            ip_list = list(set(addr[4][0] for addr in ips))
            return {"dns_ok": True, "a_records": ", ".join(ip_list), "mx_records": "-"}
        except Exception as e:
            return {"dns_ok": False, "a_records": "", "mx_records": "", "dns_error": str(e)[:80]}
    except Exception as e:
        return {"dns_ok": False, "a_records": "", "mx_records": "", "dns_error": str(e)[:80]}

def check_domain_full(domain, timeout=10, verify_ssl=True):
    result = {
        "domain": domain, "status_code": None, "final_url": "",
        "http_ok": False, "http_error": "", "response_time_s": None,
        "redirects": 0, "redirect_chain": "",
        "ssl_valid": False, "ssl_issuer": "", "ssl_expiry": "",
        "ssl_days_left": None, "ssl_error": "", "ssl_sans": "",
        "dns_ok": False, "dns_a": "", "dns_mx": "", "dns_error": "",
        "has_www": False, "www_status": None, "www_final_url": "",
        "server_header": "", "hsts": False,
        "security_headers": "", "errors": []
    }

    # DNS
    dns = check_dns(domain)
    result["dns_ok"] = dns["dns_ok"]
    result["dns_a"] = dns.get("a_records", "")
    result["dns_mx"] = dns.get("mx_records", "")
    result["dns_error"] = dns.get("dns_error", "")

    # HTTPS request
    start = _time.time()
    url = f"https://{domain}"
    try:
        resp = SESSION_OPTIONS.get(url, timeout=timeout, allow_redirects=True,
                                   verify=verify_ssl, headers={"User-Agent": "Checker/1.0"})
        result["status_code"] = resp.status_code
        result["http_ok"] = resp.ok
        result["final_url"] = resp.url or url
        result["response_time_s"] = round(_time.time() - start, 3)
        result["redirects"] = len(resp.history)
        if resp.history:
            result["redirect_chain"] = " -> ".join(
                [f"{r.status_code}:{r.headers.get('Location','?')}" for r in resp.history])
        result["server_header"] = resp.headers.get("Server", "")
        result["hsts"] = "strict-transport-security" in {k.lower() for k in resp.headers}
        # Collect security headers
        sec = []
        h_lower = {k.lower(): v for k, v in resp.headers.items()}
        if "content-security-policy" in h_lower: sec.append("CSP")
        if "x-frame-options" in h_lower: sec.append("XFO")
        if "x-content-type-options" in h_lower: sec.append("XCTO")
        if "x-xss-protection" in h_lower: sec.append("XXSS")
        if "referrer-policy" in h_lower: sec.append("RP")
        result["security_headers"] = ", ".join(sec) if sec else "brak"
    except requests.exceptions.SSLError as e:
        result["http_error"] = f"SSL: {str(e)[:100]}"
        result["response_time_s"] = round(_time.time() - start, 3)
        result["errors"].append("ssl_http")
    except requests.exceptions.ConnectionError as e:
        result["http_error"] = f"Polaczenie: {str(e)[:80]}"
        result["response_time_s"] = round(_time.time() - start, 3)
        result["errors"].append("connection")
        # Try HTTP fallback
        try:
            resp = SESSION_OPTIONS.get(f"http://{domain}", timeout=timeout,
                                       allow_redirects=True, headers={"User-Agent": "Checker/1.0"})
            result["status_code"] = resp.status_code
            result["http_ok"] = resp.ok
            result["final_url"] = resp.url or f"http://{domain}"
            result["errors"].remove("connection")
            result["errors"].append("http_only")
        except Exception:
            pass
    except Exception as e:
        result["http_error"] = str(e)[:100]
        result["response_time_s"] = round(_time.time() - start, 3)
        result["errors"].append("other")

    # SSL cert check
    ssl_info = check_ssl_cert(domain)
    result["ssl_valid"] = ssl_info["ssl_valid"]
    result["ssl_issuer"] = ssl_info["issuer"]
    result["ssl_expiry"] = ssl_info["not_after"]
    result["ssl_days_left"] = ssl_info["days_left"]
    result["ssl_error"] = ssl_info["ssl_error"]
    result["ssl_sans"] = ssl_info.get("sans", "")

    # WWW variant
    if not domain.startswith("www."):
        www = f"www.{domain}"
        try:
            resp = SESSION_OPTIONS.get(f"https://{www}", timeout=timeout/2,
                                       allow_redirects=True, verify=verify_ssl,
                                       headers={"User-Agent": "Checker/1.0"})
            result["has_www"] = True
            result["www_status"] = resp.status_code
            result["www_final_url"] = resp.url or f"https://{www}"
        except Exception:
            result["has_www"] = False

    return result

# ── Session state ─────────────────────────────────────────────────────────────
if "checker_results" not in st.session_state:
    st.session_state.checker_results = None
if "checker_raw" not in st.session_state:
    st.session_state.checker_raw = ""
if "checker_running" not in st.session_state:
    st.session_state.checker_running = False

# ── INPUT SECTION ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">// DOMENY</div>', unsafe_allow_html=True)

input_mode = st.radio("", ["Lista domen", "CSV z pliku"], horizontal=True,
                       label_visibility="collapsed")

domains_list = []
_raw_text = ""

if input_mode == "Lista domen":
    raw = st.text_area("", placeholder="example.com\ngoogle.pl\nanother-site.org",
                       height=150, key="domains_input", label_visibility="collapsed")
    _raw_text = raw or ""
    st.markdown('<div style="font-size:.65rem;color:#5a5550;margin-top:-.5rem;margin-bottom:.8rem;">jedna domena na linie, bez http://</div>', unsafe_allow_html=True)
    if raw:
        domains_list = [line.strip().replace("http://","").replace("https://","").rstrip("/").split("/")[0]
                        for line in raw.splitlines() if line.strip()]
else:
    uploaded = st.file_uploader("", type=["csv","txt"], label_visibility="collapsed")
    if uploaded:
        try:
            content = uploaded.getvalue().decode("utf-8", errors="ignore")
            try:
                df_tmp = pd.read_csv(io.StringIO(content))
                cols = [c.lower() for c in df_tmp.columns]
                if 'domain' in cols:
                    col_name = df_tmp.columns[cols.index('domain')]
                else:
                    col_name = df_tmp.columns[0]
                domains_list = df_tmp[col_name].dropna().astype(str).str.strip().tolist()
            except Exception:
                domains_list = [l.strip() for l in content.splitlines() if l.strip()]
            domains_list = [d.replace("http://","").replace("https://","").rstrip("/").split("/")[0]
                            for d in domains_list if d]
        except Exception as e:
            st.markdown(f'<div class="problems-box">Blad odczytu pliku: {e}</div>', unsafe_allow_html=True)

if domains_list:
    domains_list = list(dict.fromkeys(domains_list))
    st.markdown(f'<div class="info-box">Wczytano {len(domains_list)} domen (po deduplikacji)</div>',
                unsafe_allow_html=True)

# ── Settings ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">// USTAWIENIA</div>', unsafe_allow_html=True)
with st.expander("Konfiguracja", expanded=False):
    set_col1, set_col2, set_col3 = st.columns(3)
    with set_col1:
        num_workers = st.slider("Watki (rownolegle)", 5, 50, 20,
                                help="Wiecej = szybciej, ale obciaza siec i serwer")
    with set_col2:
        req_timeout = st.slider("Timeout (s)", 5, 30, 10,
                                help="Czas oczekiwania na odpowiedz HTTP")
    with set_col3:
        verify_ssl = st.checkbox("Weryfikuj SSL", value=True,
                                 help="Peln sprawdzenie lancucha certyfikatow")
        check_www = st.checkbox("Sprawdz WWW variant", value=True,
                                help="Czy sprawdzac czy www.domena dziala")

# ── START ─────────────────────────────────────────────────────────────────────
can_run = len(domains_list) > 0 and not st.session_state.checker_running
start_btn = st.button("START AUDYT" if can_run else "TRWA SPRAWDZANIE...",
                       disabled=not can_run, use_container_width=True)

# ── RUN CHECKS ────────────────────────────────────────────────────────────────
if start_btn and domains_list:
    st.session_state.checker_running = True
    total = len(domains_list)
    progress = st.progress(0, text=f"0/{total}")
    status_text = st.empty()

    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        for d in domains_list:
            futures[executor.submit(check_domain_full, d, req_timeout, verify_ssl)] = d

        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            progress.progress(completed / total,
                              text=f"{completed}/{total} -- {res['domain']}")
            elapsed = _time.time()
            status_text.markdown(
                f'<div style="font-size:.7rem;color:#8fa4b8;">'
                f'{completed}/{total} gotowych -- {res["domain"]} '
                f'[{res["response_time_s"] or "?"}s]</div>',
                unsafe_allow_html=True)

    progress.empty()
    status_text.empty()
    st.session_state.checker_results = results
    st.session_state.checker_running = False
    st.session_state.checker_raw = _raw_text if input_mode == "Lista domen" else ""
    st.rerun()

# ── RESULTS ───────────────────────────────────────────────────────────────────
results = st.session_state.checker_results

if results:
    df = pd.DataFrame(results)
    total = len(df)

    # ── Summary metrics ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">// PODSUMOWANIE</div>', unsafe_allow_html=True)

    http_ok = int(df["http_ok"].sum())
    ssl_ok = int(df["ssl_valid"].sum())
    dns_ok = int(df["dns_ok"].sum())
    has_issues = len(df[~df["http_ok"] | ~df["ssl_valid"] | ~df["dns_ok"]])
    avg_time = df["response_time_s"].dropna().mean()
    if pd.isna(avg_time):
        avg_time = 0.0

    # Expiring soon
    expiring = df[df["ssl_days_left"].apply(lambda x: x is not None and x < 30)]
    no_https = df[df["errors"].apply(lambda x: "http_only" in x if isinstance(x, list) else False)]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.markdown(f'<div class="metric-card"><div class="metric-label">HTTP OK</div>'
                f'<div class="metric-value {"status-ok" if http_ok==total else "status-err"}">'
                f'{http_ok}/{total}</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><div class="metric-label">SSL OK</div>'
                f'<div class="metric-value {"status-ok" if ssl_ok==total else "status-err"}">'
                f'{ssl_ok}/{total}</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><div class="metric-label">DNS OK</div>'
                f'<div class="metric-value {"status-ok" if dns_ok==total else "status-info"}">'
                f'{dns_ok}/{total}</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><div class="metric-label">Problemy</div>'
                f'<div class="metric-value {"status-ok" if has_issues==0 else "status-warn"}">'
                f'{has_issues}</div></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="metric-card"><div class="metric-label">Sredni czas</div>'
                f'<div class="metric-value">{avg_time:.2f}s</div>'
                f'<div class="metric-sub">avg response</div></div>', unsafe_allow_html=True)

    # ── Warnings ──────────────────────────────────────────────────────────
    if len(expiring) > 0:
        st.markdown(f'<div class="problems-box">UWAGA: {len(expiring)} domen ma certyfikat SSL '
                    f'wygasajacy w ciagu 30 dni!</div>', unsafe_allow_html=True)
    if len(no_https) > 0:
        st.markdown(f'<div class="problems-box">UWAGA: {len(no_https)} domen dziala TYLKO '
                    f'na HTTP (bez HTTPS)!</div>', unsafe_allow_html=True)
    if has_issues == 0:
        st.markdown('<div class="success-box">Wszystkie domeny sprawne -- zero problemow.</div>',
                    unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">// SZCZEGOLY</div>', unsafe_allow_html=True)

    tab_summary, tab_problems, tab_ssl, tab_dns, tab_all = st.tabs(
        ["Tabela glowna", "Problemy", "SSL", "DNS", "Wszystkie dane"])

    with tab_summary:
        st.markdown('<div style="font-size:.65rem;color:#5a5550;margin-bottom:.5rem;">'
                    'Kliknij naglowek kolumny aby posortowac</div>', unsafe_allow_html=True)
        show = ["domain", "status_code", "response_time_s", "http_ok", "ssl_valid",
                "ssl_days_left", "dns_ok", "redirects", "final_url"]
        display_df = df[show].copy()
        display_df.columns = ["Domena", "HTTP kod", "Czas [s]", "HTTP OK",
                              "SSL OK", "SSL dni", "DNS OK", "Przekier.", "URL koncowy"]
        st.dataframe(display_df, use_container_width=True, height=400)

    with tab_problems:
        problems = df[~df["http_ok"] | ~df["ssl_valid"] | ~df["dns_ok"]]
        if problems.empty:
            st.markdown('<div class="success-box">Brak problemow.</div>',
                        unsafe_allow_html=True)
        else:
            p_cols = ["domain", "status_code", "http_error", "ssl_valid",
                      "ssl_error", "ssl_days_left", "dns_ok", "dns_error"]
            p_show = [c for c in p_cols if c in problems.columns]
            st.dataframe(problems[p_show], use_container_width=True, height=400)

    with tab_ssl:
        ssl_df = df[["domain", "ssl_valid", "ssl_issuer", "ssl_expiry",
                     "ssl_days_left", "ssl_sans", "ssl_error"]].copy()
        ssl_df.columns = ["Domena", "SSL OK", "Wystawca", "Wygasa",
                          "Dni do konca", "SANs", "Blad SSL"]
        st.dataframe(ssl_df, use_container_width=True, height=400)

    with tab_dns:
        dns_df = df[["domain", "dns_ok", "dns_a", "dns_mx", "dns_error"]].copy()
        dns_df.columns = ["Domena", "DNS OK", "Rekordy A", "Rekordy MX", "Blad DNS"]
        st.dataframe(dns_df, use_container_width=True, height=400)

    with tab_all:
        st.dataframe(df, use_container_width=True, height=500)

    # ── Export ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">// EKSPORT</div>', unsafe_allow_html=True)
    ex1, ex2 = st.columns(2)

    csv_data = df.to_csv(index=False).encode("utf-8")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with ex1:
        st.download_button("Pobierz CSV (pelny)",
                           data=csv_data,
                           file_name=f"checker_{ts}.csv",
                           mime="text/csv", use_container_width=True)

    json_data = df.to_json(orient="records", force_ascii=False).encode("utf-8")
    with ex2:
        st.download_button("Pobierz JSON",
                           data=json_data,
                           file_name=f"checker_{ts}.json",
                           mime="application/json", use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid #2d2b29;
font-size:.65rem;color:#4a4540;text-align:center;">
checker v1.0  ·  domain auditor  ·  HTTP / SSL / DNS / Security Headers
</div>""", unsafe_allow_html=True)