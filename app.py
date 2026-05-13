import streamlit as st
import subprocess
import sys
import os
import glob
import zipfile
import threading
import queue
import time
import uuid
import shutil
import configparser
from pathlib import Path
from datetime import datetime

# ── Auto-install Playwright Chromium ─────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def ensure_playwright():
    try:
        r = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300
        )
        subprocess.run(
            [sys.executable, "-m", "playwright", "install-deps", "chromium"],
            capture_output=True, text=True, timeout=120
        )
        return True, r.stdout
    except Exception as e:
        return False, str(e)

_pw_ok, _pw_msg = ensure_playwright()

# ── Global job queue ──────────────────────────────────────────────────────────
@st.cache_resource
def get_job_state():
    return {
        "lock": threading.Lock(),
        "active_sid": None,
        "waiting": [],
    }

JOB = get_job_state()

# ── Dirs ──────────────────────────────────────────────────────────────────────
RESULTS_BASE = Path("./results")
RESULTS_BASE.mkdir(exist_ok=True)
APP_DIR = Path(__file__).parent

def session_results_dir(sid):
    p = RESULTS_BASE / sid
    p.mkdir(exist_ok=True)
    return p

def cleanup_old_sessions(max_age_hours=2):
    now = time.time()
    for d in RESULTS_BASE.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > max_age_hours * 3600:
            try: shutil.rmtree(d)
            except: pass

cleanup_old_sessions()

# ── Read snap.cfg defaults ────────────────────────────────────────────────────
def read_snap_cfg():
    """Read defaults from snap.cfg next to app.py."""
    cfg = configparser.ConfigParser()
    cfg_path = APP_DIR / "snap.cfg"
    if cfg_path.exists():
        cfg.read(cfg_path, encoding='utf-8')
    return {
        'workers':               cfg.getint('performance', 'workers', fallback=1),
        'viewport_width':        cfg.getint('browser', 'viewport_width', fallback=1440),
        'viewport_height':       cfg.getint('browser', 'viewport_height', fallback=900),
        'max_screenshot_height': cfg.getint('browser', 'max_screenshot_height', fallback=15000),
        'max_pages':             cfg.getint('crawl', 'max_pages', fallback=50),
    }

CFG_DEFAULTS = read_snap_cfg()

# ── Write per-session snap.cfg ────────────────────────────────────────────────
def write_session_cfg(out_dir: Path, workers, viewport_w, viewport_h, max_shot_h, max_pages) -> Path:
    cfg_path = out_dir / "snap.cfg"
    content = f"""[performance]
workers = {workers}

[browser]
viewport_width  = {viewport_w}
viewport_height = {viewport_h}
max_screenshot_height = {max_shot_h}

[crawl]
max_pages = {max_pages}
"""
    cfg_path.write_text(content, encoding='utf-8')
    return cfg_path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="SNAP — Web Snapshot Tool", page_icon="📸", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }
.stApp { background: #0d0d0d; color: #e0e0e0; }
.block-container { padding-top: 2rem; max-width: 1100px; }
.stTextArea textarea, .stTextInput input {
    background: #111 !important; border: 1px solid #2a2a2a !important;
    color: #e0e0e0 !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important; border-radius: 4px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #00ff88 !important; box-shadow: 0 0 0 1px #00ff88 !important;
}
.stButton > button {
    background: #00ff88 !important; color: #000 !important; border: none !important;
    font-family: 'JetBrains Mono', monospace !important; font-weight: 700 !important;
    font-size: 0.85rem !important; border-radius: 4px !important; padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover { background: #00cc70 !important; }
.stButton > button:disabled { background: #2a2a2a !important; color: #555 !important; }
.stDownloadButton > button {
    background: #111 !important; color: #00ff88 !important;
    border: 1px solid #00ff88 !important; font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important; border-radius: 4px !important;
}
.terminal {
    background: #050505; border: 1px solid #1a1a1a; border-radius: 4px; padding: 1rem;
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #aaa;
    height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;
}
.terminal .ok  { color: #00ff88; }
.terminal .err { color: #ff4444; }
.terminal .inf { color: #44aaff; }
.terminal .wrn { color: #ffaa00; }
.stProgress > div > div > div > div { background: #00ff88 !important; }
.stTabs [data-baseweb="tab-list"] { background: #111; border-bottom: 1px solid #2a2a2a; }
.stTabs [data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.78rem !important;
    color: #666 !important; background: transparent !important;
}
.stTabs [aria-selected="true"] { color: #00ff88 !important; border-bottom: 2px solid #00ff88 !important; }
.stSelectbox > div > div {
    background: #111 !important; border-color: #2a2a2a !important;
    color: #e0e0e0 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important;
}
.stSlider label, .stCheckbox label, .stRadio label { color: #aaa !important; font-size: 0.8rem !important; }
.stSlider > div > div > div { background: #2a2a2a !important; }
.stSlider > div > div > div > div { background: #00ff88 !important; }
.stNumberInput input { background: #111 !important; border: 1px solid #2a2a2a !important; color: #e0e0e0 !important; font-family: 'JetBrains Mono', monospace !important; }
.section-header {
    font-size: 0.7rem; color: #555; text-transform: uppercase; letter-spacing: 2px;
    margin-bottom: 0.5rem; margin-top: 1rem; border-bottom: 1px solid #1a1a1a; padding-bottom: 0.3rem;
}
.queue-box {
    background: #0d0d1f; border: 1px solid #333; border-left: 3px solid #44aaff;
    border-radius: 4px; padding: 0.8rem 1rem; font-size: 0.78rem; color: #aaa; margin-bottom: 1rem;
}
.queue-box strong { color: #44aaff; }
.cfg-box {
    background: #111; border: 1px solid #1a1a1a; border-radius: 4px;
    padding: 0.8rem 1rem; margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""<div style="background:#111;border:1px solid #2a2a2a;border-left:3px solid #00ff88;
padding:1.2rem 1.5rem;margin-bottom:1.5rem;font-family:'JetBrains Mono',monospace;
font-size:0.75rem;color:#00ff88;white-space:pre;line-height:1.3;">  ███████╗███╗   ██╗ █████╗ ██████╗
  ██╔════╝████╗  ██║██╔══██╗██╔══██╗
  ███████╗██╔██╗ ██║███████║██████╔╝
  ╚════██║██║╚██╗██║██╔══██║██╔═══╝
  ███████║██║ ╚████║██║  ██║██║
  ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  <span style="color:#666">web snapshot tool  //  v4.1</span></div>""",
unsafe_allow_html=True)

# ── Playwright status ─────────────────────────────────────────────────────────
if not _pw_ok:
    st.markdown(f"""<div style="background:#1f0d0d;border:1px solid #ff4444;border-radius:4px;
    padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.75rem;color:#ff8888;">
    ⚠ Playwright Chromium nie jest gotowy — mogą wystąpić błędy.<br>
    <span style="color:#666">{_pw_msg[:200]}</span></div>""", unsafe_allow_html=True)
else:
    st.markdown("""<div style="background:#0d1f15;border:1px solid #00ff88;border-radius:4px;
    padding:0.5rem 1rem;margin-bottom:1rem;font-size:0.7rem;color:#00ff88;">
    ✓ Playwright Chromium gotowy</div>""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────────
if "sid"         not in st.session_state: st.session_state.sid         = str(uuid.uuid4())[:8]
if "log_lines"   not in st.session_state: st.session_state.log_lines   = []
if "running"     not in st.session_state: st.session_state.running     = False
if "in_queue"    not in st.session_state: st.session_state.in_queue    = False
if "result_zip"  not in st.session_state: st.session_state.result_zip  = None
if "screenshots" not in st.session_state: st.session_state.screenshots = []
if "done"        not in st.session_state: st.session_state.done        = False

SID = st.session_state.sid

# ── Queue helpers ─────────────────────────────────────────────────────────────
def queue_position(sid):
    w = JOB["waiting"]
    return w.index(sid) + 1 if sid in w else 0

def enter_queue(sid):
    if sid not in JOB["waiting"]:
        JOB["waiting"].append(sid)

def leave_queue(sid):
    if sid in JOB["waiting"]:
        JOB["waiting"].remove(sid)

def is_my_turn(sid):
    return JOB["active_sid"] is None or JOB["active_sid"] == sid

# ── Background runner ─────────────────────────────────────────────────────────
def stream_process(cmd, log_q, cwd):
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=cwd
        )
        for line in proc.stdout:
            log_q.put(line.rstrip())
        proc.wait()
        log_q.put(f"__EXIT__{proc.returncode}")
    except Exception as e:
        log_q.put(f"[ERROR] {e}")
        log_q.put("__EXIT__1")

# ── Layout — LEFT COLUMN ──────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-header">// URL INPUT</div>', unsafe_allow_html=True)
    urls_raw = st.text_area(
        "", placeholder="https://example.com\nhttps://another-site.com",
        height=120, key="urls_input", label_visibility="collapsed"
    )
    st.markdown('<div style="font-size:0.65rem;color:#555;margin-top:-0.5rem;margin-bottom:0.8rem;">jeden URL per linia</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">// TRYB</div>', unsafe_allow_html=True)
    mode = st.selectbox("", options=["screenshots","full","crawl","clean-screenshots","clean-full","clean-crawl"],
        format_func=lambda x: {
            "screenshots":       "📸  Screenshots only — szybko",
            "full":              "📦  Full — HTML + assets + screenshoty",
            "crawl":             "🕷️  Crawl — auto-discover z sitemap + linków",
            "clean-screenshots": "🧹📸  Clean + Screenshots",
            "clean-full":        "🧹📦  Clean + Full",
            "clean-crawl":       "🧹🕷️  Clean + Crawl",
        }[x], label_visibility="collapsed"
    )

    # ── snap.cfg settings ─────────────────────────────────────────────────────
    with st.expander("⚙️  Ustawienia zaawansowane (snap.cfg)", expanded=False):
        st.markdown('<div style="font-size:0.68rem;color:#555;margin-bottom:0.8rem;">Nadpisują snap.cfg dla tej sesji</div>', unsafe_allow_html=True)

        cfg_col1, cfg_col2 = st.columns(2)
        with cfg_col1:
            cfg_workers = st.number_input(
                "Workers (równoległe karty)", min_value=1, max_value=8,
                value=CFG_DEFAULTS['workers'], step=1,
                help="Ile kart przeglądarki działa równolegle. Na Streamlit Cloud zalecane: 1"
            )
            cfg_viewport_w = st.number_input(
                "Viewport width (px)", min_value=320, max_value=2560,
                value=CFG_DEFAULTS['viewport_width'], step=10
            )
            cfg_viewport_h = st.number_input(
                "Viewport height (px)", min_value=400, max_value=2160,
                value=CFG_DEFAULTS['viewport_height'], step=10
            )
        with cfg_col2:
            cfg_max_shot = st.number_input(
                "Max screenshot height (px)", min_value=1000, max_value=60000,
                value=CFG_DEFAULTS['max_screenshot_height'], step=1000
            )
            if "crawl" in mode:
                cfg_max_pages = st.number_input(
                    "Max stron (crawl)", min_value=1, max_value=500,
                    value=min(CFG_DEFAULTS['max_pages'], 50), step=5
                )
            else:
                cfg_max_pages = CFG_DEFAULTS['max_pages']

        keep_folders = st.checkbox("Zachowaj foldery po spakowaniu", value=False)

    st.markdown("")
    can_run = not st.session_state.running and not st.session_state.in_queue
    run_btn = st.button(
        "▶  START" if can_run else ("⏳  TRWA..." if st.session_state.running else "🕐  W KOLEJCE..."),
        disabled=not can_run, use_container_width=True
    )

# ── Layout — RIGHT COLUMN ─────────────────────────────────────────────────────
with col_right:
    st.markdown('<div class="section-header">// LOG</div>', unsafe_allow_html=True)
    queue_placeholder  = st.empty()
    log_placeholder    = st.empty()
    status_placeholder = st.empty()
    progress_placeholder = st.empty()

    def render_log():
        lines = st.session_state.log_lines[-120:]
        html_lines = []
        for line in lines:
            l = line.replace("<","&lt;").replace(">","&gt;")
            if   "[OK]" in l or "✓" in l:  cls = "ok"
            elif "[FAIL]" in l or "ERROR" in l or "error" in l.lower(): cls = "err"
            elif "[*]" in l or "─" in l or "[cfg]" in l: cls = "inf"
            elif "[!]" in l:               cls = "wrn"
            else:                          cls = ""
            html_lines.append(f'<span class="{cls}">{l}</span>')
        log_placeholder.markdown(
            '<div class="terminal">' + "\n".join(html_lines) + '</div>',
            unsafe_allow_html=True
        )

    render_log()

# ── START button ──────────────────────────────────────────────────────────────
if run_btn:
    urls = [u.strip() for u in urls_raw.strip().splitlines()
            if u.strip() and not u.strip().startswith("#")]
    if not urls:
        st.error("Wpisz przynajmniej jeden URL!")
    else:
        st.session_state["_pending_urls"]      = urls
        st.session_state["_pending_mode"]      = mode
        st.session_state["_pending_workers"]   = cfg_workers
        st.session_state["_pending_vp_w"]      = cfg_viewport_w
        st.session_state["_pending_vp_h"]      = cfg_viewport_h
        st.session_state["_pending_max_shot"]  = cfg_max_shot
        st.session_state["_pending_max_pages"] = cfg_max_pages
        st.session_state["_pending_keep"]      = keep_folders
        st.session_state.log_lines   = []
        st.session_state.result_zip  = None
        st.session_state.screenshots = []
        st.session_state.done        = False
        st.session_state.in_queue    = True
        enter_queue(SID)
        st.rerun()

# ── Queue waiting ─────────────────────────────────────────────────────────────
if st.session_state.in_queue and not st.session_state.running:
    pos = queue_position(SID)

    if not is_my_turn(SID):
        queue_placeholder.markdown(
            f'<div class="queue-box">🕐 Czekasz w kolejce — pozycja <strong>{pos}</strong>. '
            f'Inny użytkownik scrapu je. Odświeżam co 3s...</div>',
            unsafe_allow_html=True
        )
        time.sleep(3)
        st.rerun()
    else:
        JOB["active_sid"] = SID
        leave_queue(SID)
        st.session_state.in_queue = False
        st.session_state.running  = True
        queue_placeholder.empty()

        urls        = st.session_state.get("_pending_urls", [])
        _mode       = st.session_state.get("_pending_mode", "screenshots")
        _workers    = st.session_state.get("_pending_workers", 1)
        _vp_w       = st.session_state.get("_pending_vp_w", 1440)
        _vp_h       = st.session_state.get("_pending_vp_h", 900)
        _max_shot   = st.session_state.get("_pending_max_shot", 15000)
        _max_pages  = st.session_state.get("_pending_max_pages", 50)
        _keep       = st.session_state.get("_pending_keep", False)

        out_dir = session_results_dir(SID)

        # write per-session snap.cfg
        cfg_path = write_session_cfg(out_dir, _workers, _vp_w, _vp_h, _max_shot, _max_pages)

        cmd = [
            sys.executable, "snap.py",
            "--mode",   _mode,
            "--output", str(out_dir),
            "--config", str(cfg_path),
        ]
        if _keep:
            cmd.append("--keep-folders")
        cmd.extend(urls)

        log_q = queue.Queue()
        t = threading.Thread(target=stream_process, args=(cmd, log_q, APP_DIR), daemon=True)
        t.start()

        prog = progress_placeholder.progress(0)
        total_urls = max(len(urls), 1)
        done_count = 0
        start_ts   = time.time()

        status_placeholder.markdown(
            '<div style="font-size:0.75rem;color:#44aaff;">▶ running...</div>',
            unsafe_allow_html=True
        )

        exit_code = None
        while exit_code is None:
            new_lines = []
            try:
                while True:
                    line = log_q.get_nowait()
                    if line.startswith("__EXIT__"):
                        exit_code = int(line.replace("__EXIT__", ""))
                    else:
                        new_lines.append(line)
                        if "[OK]" in line or "[FAIL]" in line:
                            done_count = min(done_count + 1, total_urls)
                            prog.progress(done_count / total_urls)
            except queue.Empty:
                pass
            if new_lines:
                st.session_state.log_lines.extend(new_lines)
                render_log()
            time.sleep(0.3)

        # drain
        while not log_q.empty():
            try:
                line = log_q.get_nowait()
                if not line.startswith("__EXIT__"):
                    st.session_state.log_lines.append(line)
            except queue.Empty:
                break

        elapsed = time.time() - start_ts
        st.session_state.running  = False
        st.session_state.done     = True
        JOB["active_sid"]         = None
        prog.progress(1.0)

        # find ZIP
        zips = sorted(glob.glob(str(out_dir / "*.zip")), key=os.path.getmtime)
        if zips:
            st.session_state.result_zip = zips[-1]

        # collect screenshots — tylko screenshot_full.png lub PNG z depth=2
        shots = []
        if st.session_state.result_zip:
            try:
                with zipfile.ZipFile(st.session_state.result_zip) as zf:
                    for name in sorted(zf.namelist()):
                        if not name.lower().endswith(".png"):
                            continue
                        parts = Path(name).parts
                        if "assets" in [p.lower() for p in parts]:
                            continue
                        fname = Path(name).name.lower()
                        if fname == "screenshot_full.png":
                            shots.append((name, zf.read(name)))
                        elif len(parts) == 2 and fname.endswith(".png"):
                            shots.append((name, zf.read(name)))
            except Exception:
                pass
        st.session_state.screenshots = shots

        if exit_code == 0:
            status_placeholder.markdown(
                f'<div style="font-size:0.75rem;color:#00ff88;">✓ zakończono [{elapsed:.1f}s] — {len(shots)} screenshotów</div>',
                unsafe_allow_html=True
            )
        else:
            status_placeholder.markdown(
                f'<div style="font-size:0.75rem;color:#ff4444;">✗ błąd (exit {exit_code}) [{elapsed:.1f}s]</div>',
                unsafe_allow_html=True
            )
        render_log()
        st.rerun()

# ── RESULTS ───────────────────────────────────────────────────────────────────
if st.session_state.done:
    st.markdown("---")
    st.markdown('<div class="section-header">// WYNIKI</div>', unsafe_allow_html=True)

    res_col1, res_col2 = st.columns([1, 3])

    with res_col1:
        if st.session_state.result_zip:
            zip_path = st.session_state.result_zip
            zip_name = Path(zip_path).name
            zip_size = os.path.getsize(zip_path) / (1024 * 1024)
            st.markdown(f"""
            <div style="background:#111;border:1px solid #2a2a2a;border-radius:4px;padding:1rem;margin-bottom:1rem;">
                <div style="font-size:0.65rem;color:#555;margin-bottom:0.5rem;">PLIK ZIP</div>
                <div style="font-size:0.8rem;color:#e0e0e0;word-break:break-all;">{zip_name}</div>
                <div style="font-size:0.72rem;color:#666;margin-top:0.3rem;">{zip_size:.2f} MB</div>
            </div>""", unsafe_allow_html=True)
            with open(zip_path, "rb") as f:
                st.download_button("⬇  Pobierz ZIP", data=f, file_name=zip_name,
                                   mime="application/zip", use_container_width=True)
        else:
            st.markdown('<div style="color:#ff4444;font-size:0.8rem;">Brak ZIP — sprawdź log</div>', unsafe_allow_html=True)

        shots = st.session_state.screenshots
        st.markdown(f"""
        <div style="background:#111;border:1px solid #2a2a2a;border-radius:4px;padding:1rem;margin-top:0.5rem;">
            <div style="font-size:0.65rem;color:#555;margin-bottom:0.3rem;">SCREENSHOTY</div>
            <div style="font-size:1.5rem;color:#00ff88;font-weight:700;">{len(shots)}</div>
        </div>""", unsafe_allow_html=True)

    with res_col2:
        shots = st.session_state.screenshots
        if shots:
            st.markdown('<div style="font-size:0.7rem;color:#555;margin-bottom:0.8rem;">PODGLĄD</div>', unsafe_allow_html=True)
            tabs = st.tabs([Path(name).stem[:30] for name, _ in shots[:10]])
            for i, (tab, (name, data)) in enumerate(zip(tabs, shots[:10])):
                with tab:
                    st.image(data, caption=name, use_container_width=True)
                    st.download_button(f"⬇ {Path(name).name}", data=data,
                                       file_name=Path(name).name, mime="image/png",
                                       key=f"shot_{i}")
            if len(shots) > 10:
                st.markdown(f'<div style="font-size:0.72rem;color:#555;margin-top:0.5rem;">...i {len(shots)-10} więcej w ZIP</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#555;font-size:0.8rem;">Brak screenshotów</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
active = JOB["active_sid"]
waiting_count = len(JOB["waiting"])
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1rem;border-top:1px solid #1a1a1a;
font-size:0.65rem;color:#333;text-align:center;">
snap.py v4.1  //  streamlit frontend  //  sesja: {SID}
{"  //  🟢 serwer wolny" if not active else f"  //  🔴 zajęty ({active})"}
{"  //  kolejka: " + str(waiting_count) if waiting_count else ""}
</div>""", unsafe_allow_html=True)
