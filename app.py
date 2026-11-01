"""
News Reader App
================
Aplikasi Streamlit untuk membaca berita dari berbagai sumber RSS Indonesia,
lengkap dengan tampilan isi artikel penuh. Tampilan dipercantik dengan HTML dan CSS.

Author : Senior Developer
"""

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import feedparser
import requests
import streamlit as st
import trafilatura
from dateutil import parser as date_parser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(raw: str) -> str:
    """Hapus tag HTML sederhana dari ringkasan RSS."""
    if not raw:
        return ""
    return html.unescape(_TAG_RE.sub("", raw)).strip()


def esc(text: str) -> str:
    """Escape teks agar aman disisipkan ke HTML (tanda $ dicegah jadi rumus LaTeX)."""
    return html.escape(text or "", quote=True).replace("$", "&#36;")


# --------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="News Reader - Berita Terkini",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# KONSTANTA
# --------------------------------------------------------------------------
RSS_SOURCES = {
    "Detik": "https://rss.detik.com/index.php/detikcom",
    "Kompas": "https://rss.kompas.com/api/all",
    "CNN Indonesia": "https://www.cnnindonesia.com/nasional/rss",
    "Antara News": "https://www.antaranews.com/rss/terkini.xml",
    "Tempo Nasional": "https://rss.tempo.co/nasional",
    "Republika": "https://www.republika.co.id/rss",
}

# Domain resmi tiap sumber — dipakai sebagai fallback pencarian via Google News RSS
# jika feed RSS resmi diblokir (403/hang) oleh server sumber (mis. karena IP cloud/data center).
SOURCE_DOMAINS = {
    "Detik": "detik.com",
    "Kompas": "kompas.com",
    "CNN Indonesia": "cnnindonesia.com",
    "Antara News": "antaranews.com",
    "Tempo Nasional": "tempo.co",
    "Republika": "republika.co.id",
}

# Warna penanda tiap sumber (dipakai pada label sumber)
SOURCE_COLORS = {
    "Detik": "#e4572e",
    "Kompas": "#1f6feb",
    "CNN Indonesia": "#d7263d",
    "Antara News": "#0b8a5f",
    "Tempo Nasional": "#3b4252",
    "Republika": "#7c3aed",
}

GOOGLE_NEWS_FALLBACK_TEMPLATE = (
    "https://news.google.com/rss/search?q=site:{domain}+when:2d&hl=id&gl=ID&ceid=ID:id"
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

CACHE_TTL_LIST = 600      # 10 menit untuk daftar berita
CACHE_TTL_ARTICLE = 3600  # 60 menit untuk isi artikel
REQUEST_TIMEOUT = 10      # detik
MAX_RETRIES = 2

WIB = timezone(timedelta(hours=7))
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
BULAN_SINGKAT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Inter:wght@400;500;600&display=swap');

:root {
    --paper: #f3f5f8;
    --card: #ffffff;
    --ink: #0e1726;
    --ink-soft: #1b2434;
    --muted: #5b6678;
    --line: #dde2ea;
    --accent: #d7263d;
    --accent-dark: #a81b2e;
}

html, body, .stApp {
    font-family: 'Inter', sans-serif;
    color: var(--ink);
}
.stApp { background: var(--paper); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1240px; padding-top: 2rem; padding-bottom: 4rem; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: var(--card);
    border-right: 1px solid var(--line);
}
.brand { border-left: 5px solid var(--accent); padding: 0.1rem 0 0.1rem 0.8rem; margin-bottom: 0.4rem; }
.brand-name {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 800;
    font-size: 1.55rem;
    letter-spacing: -0.02em;
    color: var(--ink);
    line-height: 1.1;
}
.brand-sub { font-size: 0.85rem; color: var(--muted); margin-top: 0.25rem; }
[data-testid="stWidgetLabel"] p { font-weight: 600; font-size: 0.85rem; color: var(--ink); }
div[data-baseweb="input"], div[data-baseweb="select"] > div { border-radius: 10px; }
span[data-baseweb="tag"] { background: var(--ink) !important; color: #ffffff !important; border-radius: 6px; }
span[data-baseweb="tag"] span { color: #ffffff !important; }
.side-foot { font-size: 0.8rem; color: var(--muted); margin-top: 0.6rem; }

/* ---------- Masthead ---------- */
.masthead {
    background: var(--ink);
    color: #ffffff;
    border-radius: 20px;
    padding: 2.3rem 2.7rem 2.4rem 2.7rem;
    margin-bottom: 0.4rem;
}
.mast-bar { width: 56px; height: 6px; background: var(--accent); border-radius: 3px; margin-bottom: 1.2rem; }
.mast-date { font-size: 0.95rem; color: #9fb0c8; margin-bottom: 0.5rem; }
.mast-title {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 800;
    font-size: 3.4rem;
    line-height: 1.05;
    letter-spacing: -0.025em;
    margin: 0 0 0.7rem 0;
    color: #ffffff;
}
.mast-sub { font-size: 1.02rem; color: #c9d4e4; max-width: 560px; line-height: 1.55; margin: 0; }

/* ---------- Bilah hasil ---------- */
.result-bar {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    flex-wrap: wrap;
    margin: 1.8rem 0 1.1rem 0;
    padding-bottom: 0.7rem;
    border-bottom: 2px solid var(--ink);
}
.result-count { font-size: 1rem; color: var(--ink-soft); }
.result-count b { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.5rem; margin-right: 0.15rem; }
.result-note { font-size: 0.88rem; color: var(--muted); }
.section-label {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 700;
    font-size: 1.3rem;
    letter-spacing: -0.01em;
    margin: 2rem 0 0.9rem 0;
    color: var(--ink);
}

/* ---------- Kartu (container Streamlit) ---------- */
div[class*="st-key-card_"], div[class*="st-key-lead_"] {
    background: var(--card);
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    padding: 0.9rem !important;
    box-shadow: 0 1px 2px rgba(14, 23, 38, 0.04);
    transition: border-color 0.15s ease;
}
div[class*="st-key-card_"]:hover, div[class*="st-key-lead_"]:hover { border-color: var(--ink) !important; }

.thumb {
    aspect-ratio: 16 / 9;
    overflow: hidden;
    border-radius: 12px;
    background: #e3e8ef;
    margin-bottom: 0.9rem;
}
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb.ph {
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--ink) 0%, #243552 100%);
    color: #ffffff;
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 700;
    font-size: 1.3rem;
}

.chip-row { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.55rem; flex-wrap: wrap; }
.chip {
    color: var(--c);
    background: color-mix(in srgb, var(--c) 12%, white);
    font-weight: 600;
    font-size: 0.78rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
}
.meta { font-size: 0.8rem; color: var(--muted); }

.card-title {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    line-height: 1.28;
    letter-spacing: -0.01em;
    color: var(--ink);
    margin: 0 0 0.5rem 0;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 4.3em;
}
.card-sum {
    font-size: 0.92rem;
    line-height: 1.55;
    color: var(--muted);
    margin: 0 0 0.8rem 0;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* Berita utama */
.lead-title {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 800;
    font-size: 2.1rem;
    line-height: 1.12;
    letter-spacing: -0.02em;
    color: var(--ink);
    margin: 0.3rem 0 0.8rem 0;
}
.lead-sum { font-size: 1.02rem; line-height: 1.65; color: var(--ink-soft); margin: 0 0 1rem 0; }
div[class*="st-key-lead_"] .thumb { margin-bottom: 0; height: 100%; min-height: 260px; aspect-ratio: auto; }

/* ---------- Tombol ---------- */
.stButton > button, .stLinkButton > a {
    border-radius: 10px;
    border: 1.5px solid var(--ink);
    background: transparent;
    color: var(--ink);
    font-weight: 600;
    padding: 0.55rem 1rem;
    transition: background 0.15s ease, color 0.15s ease;
}
.stButton > button:hover, .stLinkButton > a:hover {
    background: var(--ink);
    color: #ffffff !important;
    border-color: var(--ink);
}
.stButton > button p, .stLinkButton > a p { color: inherit; }
button[data-testid="stBaseButton-primary"], a[data-testid="stBaseLinkButton-primary"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #ffffff !important;
}
button[data-testid="stBaseButton-primary"]:hover, a[data-testid="stBaseLinkButton-primary"]:hover {
    background: var(--accent-dark) !important;
    border-color: var(--accent-dark) !important;
}
.stProgress > div > div > div > div { background-color: var(--accent); }

/* ---------- Pemberitahuan ---------- */
.notice {
    background: var(--card);
    border: 1px solid var(--line);
    border-left: 5px solid var(--accent);
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 1rem 0;
    color: var(--ink-soft);
    font-size: 0.95rem;
    line-height: 1.55;
}
.notice b { color: var(--ink); }

/* ---------- Halaman baca ---------- */
.read-source { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; margin: 1.2rem 0 0.9rem 0; }
.read-title {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-weight: 800;
    font-size: 2.7rem;
    line-height: 1.1;
    letter-spacing: -0.025em;
    color: var(--ink);
    margin: 0;
}
.read-hero {
    aspect-ratio: 16 / 9;
    overflow: hidden;
    border-radius: 16px;
    background: #e3e8ef;
    margin: 1.6rem 0 2rem 0;
}
.read-hero img { width: 100%; height: 100%; object-fit: cover; display: block; }
.read-rule { height: 1px; background: var(--line); margin: 1.6rem 0 1.8rem 0; }
.read-body p {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.18rem;
    line-height: 1.78;
    color: var(--ink-soft);
    margin: 0 0 1.3rem 0;
}
.read-body p:first-child { font-size: 1.32rem; line-height: 1.6; font-weight: 600; color: var(--ink); }

@media (max-width: 640px) {
    .masthead { padding: 1.6rem 1.4rem; }
    .mast-title { font-size: 2.3rem; }
    .lead-title { font-size: 1.6rem; }
    .read-title { font-size: 1.9rem; }
    .read-body p { font-size: 1.08rem; }
}
</style>
"""


# --------------------------------------------------------------------------
# SESSION HTTP DENGAN RETRY
# --------------------------------------------------------------------------
def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(REQUEST_HEADERS)
    return session


_SESSION = _build_session()


# --------------------------------------------------------------------------
# FUNGSI BANTUAN (CACHED)
# --------------------------------------------------------------------------
def _to_wib_naive(dt: datetime) -> datetime:
    """Samakan semua tanggal ke WIB tanpa timezone agar bisa diurutkan tanpa error."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(WIB).replace(tzinfo=None)
    return dt


def _parse_feed_entries(raw_content: bytes):
    """Ubah konten RSS mentah menjadi list of dict entri berita."""
    feed = feedparser.parse(raw_content)
    entries = []
    for e in feed.entries:
        published = None
        for key in ("published", "updated", "pubDate"):
            if key in e:
                try:
                    published = _to_wib_naive(date_parser.parse(e[key]))
                except Exception:
                    published = None
                break

        image_url = None
        if "media_content" in e and e.media_content:
            image_url = e.media_content[0].get("url")
        elif "media_thumbnail" in e and e.media_thumbnail:
            image_url = e.media_thumbnail[0].get("url")
        elif "links" in e:
            for link in e.links:
                if link.get("type", "").startswith("image"):
                    image_url = link.get("href")
                    break

        entries.append(
            {
                "title": e.get("title", "(Tanpa judul)"),
                "link": e.get("link", ""),
                "summary": e.get("summary", ""),
                "published": published,
                "image": image_url,
            }
        )
    return entries


def _raw_fetch(url: str):
    """Ambil konten mentah sebuah URL. Mengembalikan bytes atau None jika gagal."""
    try:
        resp = _SESSION.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


@st.cache_data(ttl=CACHE_TTL_LIST, show_spinner=False)
def fetch_rss(url: str, fallback_domain: str = None):
    """
    Ambil dan parse RSS feed dari `url`. Jika gagal atau hasilnya kosong
    (mis. sumber memblokir permintaan dari server/cloud), otomatis coba
    ambil berita dari sumber yang sama melalui Google News RSS sebagai
    fallback (jika `fallback_domain` diberikan).
    Tidak pernah melempar exception — mengembalikan list kosong jika semua gagal.
    """
    raw = _raw_fetch(url)
    entries = []
    if raw:
        try:
            entries = _parse_feed_entries(raw)
        except Exception:
            entries = []

    if entries:
        return entries

    # --- Fallback: Google News RSS (jarang diblokir, cocok untuk deploy cloud) ---
    if fallback_domain:
        gnews_url = GOOGLE_NEWS_FALLBACK_TEMPLATE.format(domain=fallback_domain)
        raw_fallback = _raw_fetch(gnews_url)
        if raw_fallback:
            try:
                return _parse_feed_entries(raw_fallback)
            except Exception:
                return []

    return []


@st.cache_data(ttl=CACHE_TTL_ARTICLE, show_spinner=False)
def fetch_full_article(url: str):
    """Ekstrak isi artikel penuh dari sebuah URL menggunakan trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )
        return text
    except Exception:
        return None


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def format_datetime(dt):
    if not dt:
        return "Tanggal tidak diketahui"
    return f"{dt.day} {BULAN_SINGKAT[dt.month - 1]} {dt.year}, {dt:%H:%M}"


# --------------------------------------------------------------------------
# FUNGSI HTML
# --------------------------------------------------------------------------
def card_container(key: str):
    """Container berbingkai dengan key (agar bisa di-style CSS). Aman untuk Streamlit lama."""
    try:
        return st.container(border=True, key=key)
    except TypeError:
        return st.container(border=True)


def chip_html(source: str) -> str:
    color = SOURCE_COLORS.get(source, "#3b4252")
    return f'<span class="chip" style="--c:{color}">{esc(source)}</span>'


def thumb_html(article: dict) -> str:
    img = article.get("image") or ""
    if img.startswith(("http://", "https://")):
        return (
            '<div class="thumb">'
            f'<img src="{esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
            "</div>"
        )
    return f'<div class="thumb ph">{esc(article.get("source", ""))}</div>'


def snippet(article: dict, limit: int) -> str:
    text = strip_html(article.get("summary", ""))
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text


def masthead_html() -> str:
    now = datetime.now(WIB)
    tanggal = f"{HARI[now.weekday()]}, {now.day} {BULAN[now.month - 1]} {now.year}"
    return (
        '<div class="masthead">'
        '<div class="mast-bar"></div>'
        f'<div class="mast-date">{tanggal}</div>'
        '<div class="mast-title">Berita Terkini</div>'
        '<p class="mast-sub">Kumpulan berita terbaru dari sumber pilihan Anda, '
        "lengkap dengan isi artikel yang bisa dibaca langsung di sini.</p>"
        "</div>"
    )


# --------------------------------------------------------------------------
# STATE
# --------------------------------------------------------------------------
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None  # dict artikel yang dipilih


def open_article(article: dict):
    st.session_state.selected_article = article


def close_article():
    st.session_state.selected_article = None


# --------------------------------------------------------------------------
# TAMPILKAN CSS
# --------------------------------------------------------------------------
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="brand">'
        '<div class="brand-name">News Reader</div>'
        '<div class="brand-sub">Baca berita terkini dari berbagai sumber terpercaya di Indonesia.</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    selected_sources = st.multiselect(
        "Pilih sumber berita",
        options=list(RSS_SOURCES.keys()),
        default=["Detik", "Kompas", "CNN Indonesia"],
    )

    keyword = st.text_input("Cari kata kunci", placeholder="Contoh: ekonomi, pemilu, olahraga...")

    sort_option = st.selectbox(
        "Urutkan berdasarkan",
        options=["Terbaru", "Terlama", "Judul (A-Z)"],
    )

    st.divider()
    if st.button("Segarkan berita", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div class="side-foot">Dibuat menggunakan Streamlit</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# HALAMAN DETAIL ARTIKEL
# --------------------------------------------------------------------------
def render_article_detail(article: dict):
    _, mid, _ = st.columns([1, 2.6, 1])
    with mid:
        st.button("Kembali ke daftar berita", on_click=close_article)

        head = (
            '<div class="read-source">'
            f'{chip_html(article.get("source", domain_of(article["link"])))}'
            f'<span class="meta">{esc(format_datetime(article["published"]))}</span>'
            f'<span class="meta">{esc(domain_of(article["link"]))}</span>'
            "</div>"
            f'<div class="read-title">{esc(article["title"])}</div>'
        )
        img = article.get("image") or ""
        if img.startswith(("http://", "https://")):
            head += (
                '<div class="read-hero">'
                f'<img src="{esc(img)}" alt="" referrerpolicy="no-referrer">'
                "</div>"
            )
        else:
            head += '<div class="read-rule"></div>'
        st.markdown(head, unsafe_allow_html=True)

        with st.spinner("Mengambil isi artikel lengkap..."):
            full_text = fetch_full_article(article["link"])

        if full_text:
            paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
        else:
            st.markdown(
                '<div class="notice"><b>Isi artikel lengkap tidak dapat diambil otomatis.</b><br>'
                "Silakan baca ringkasan di bawah, atau buka artikel asli melalui tombol di akhir halaman.</div>",
                unsafe_allow_html=True,
            )
            clean_summary = strip_html(article.get("summary", ""))
            paragraphs = [clean_summary] if clean_summary else ["Tidak ada ringkasan tersedia."]

        body = "".join(f"<p>{esc(p)}</p>" for p in paragraphs)
        st.markdown(f'<div class="read-body">{body}</div>', unsafe_allow_html=True)

        st.markdown('<div class="read-rule"></div>', unsafe_allow_html=True)
        st.link_button(
            "Baca di situs asli",
            article["link"],
            use_container_width=True,
            type="primary",
        )


# --------------------------------------------------------------------------
# KOMPONEN DAFTAR BERITA
# --------------------------------------------------------------------------
def render_lead(article: dict):
    with card_container("lead_story"):
        col_img, col_text = st.columns([1.15, 1])
        with col_img:
            st.markdown(thumb_html(article), unsafe_allow_html=True)
        with col_text:
            summary = snippet(article, 320)
            st.markdown(
                '<div class="chip-row">'
                f'{chip_html(article["source"])}'
                f'<span class="meta">{esc(format_datetime(article["published"]))}</span>'
                "</div>"
                f'<div class="lead-title">{esc(article["title"])}</div>'
                f'<p class="lead-sum">{esc(summary)}</p>',
                unsafe_allow_html=True,
            )
            st.button(
                "Baca selengkapnya",
                key=f"read_0_{article['link']}",
                on_click=open_article,
                args=(article,),
                use_container_width=True,
                type="primary",
            )


def render_card(idx: int, article: dict):
    with card_container(f"card_{idx}"):
        summary = snippet(article, 180)
        st.markdown(
            f"{thumb_html(article)}"
            '<div class="chip-row">'
            f'{chip_html(article["source"])}'
            f'<span class="meta">{esc(format_datetime(article["published"]))}</span>'
            "</div>"
            f'<div class="card-title">{esc(article["title"])}</div>'
            f'<p class="card-sum">{esc(summary)}</p>',
            unsafe_allow_html=True,
        )
        st.button(
            "Baca selengkapnya",
            key=f"read_{idx}_{article['link']}",
            on_click=open_article,
            args=(article,),
            use_container_width=True,
        )


# --------------------------------------------------------------------------
# HALAMAN DAFTAR BERITA
# --------------------------------------------------------------------------
def render_article_list():
    st.markdown(masthead_html(), unsafe_allow_html=True)

    if not selected_sources:
        st.markdown(
            '<div class="notice"><b>Belum ada sumber berita dipilih.</b><br>'
            "Pilih minimal satu sumber berita pada panel di sebelah kiri.</div>",
            unsafe_allow_html=True,
        )
        return

    all_articles = []
    failed_sources = []
    progress = st.progress(0.0, text="Mengambil berita...")
    for i, source_name in enumerate(selected_sources):
        url = RSS_SOURCES[source_name]
        fallback_domain = SOURCE_DOMAINS.get(source_name)
        try:
            entries = fetch_rss(url, fallback_domain)
        except Exception:
            entries = []
        if not entries:
            failed_sources.append(source_name)
        for e in entries:
            e["source"] = source_name
        all_articles.extend(entries)
        progress.progress((i + 1) / len(selected_sources), text=f"Mengambil berita dari {source_name}...")
    progress.empty()

    if failed_sources:
        st.markdown(
            '<div class="notice"><b>Gagal mengambil berita dari: '
            + esc(", ".join(failed_sources))
            + ".</b><br>Sumber ini mungkin sedang tidak dapat diakses, atau memblokir "
            "permintaan otomatis. Coba lagi beberapa saat, atau pilih sumber lain.</div>",
            unsafe_allow_html=True,
        )

    # Filter berdasarkan kata kunci
    if keyword:
        kw = keyword.lower()
        all_articles = [
            a for a in all_articles
            if kw in a["title"].lower() or kw in a.get("summary", "").lower()
        ]

    # Urutkan
    if sort_option == "Terbaru":
        all_articles.sort(key=lambda a: a["published"] or datetime.min, reverse=True)
    elif sort_option == "Terlama":
        all_articles.sort(key=lambda a: a["published"] or datetime.min)
    else:
        all_articles.sort(key=lambda a: a["title"].lower())

    if not all_articles:
        st.markdown(
            '<div class="notice"><b>Tidak ada berita yang ditemukan.</b><br>'
            "Coba ubah kata kunci atau pilih sumber berita lain.</div>",
            unsafe_allow_html=True,
        )
        return

    # Bilah hasil
    jumlah_sumber = len(selected_sources) - len(failed_sources)
    catatan = f"Urutan: {sort_option}"
    if keyword:
        catatan += f" | Kata kunci: {keyword}"
    st.markdown(
        '<div class="result-bar">'
        f'<span class="result-count"><b>{len(all_articles)}</b> berita dari {jumlah_sumber} sumber</span>'
        f'<span class="result-note">{esc(catatan)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Berita utama
    render_lead(all_articles[0])

    # Berita lainnya dalam grid 3 kolom
    rest = all_articles[1:]
    if rest:
        st.markdown('<div class="section-label">Berita lainnya</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, article in enumerate(rest):
            with cols[i % 3]:
                render_card(i + 1, article)


# --------------------------------------------------------------------------
# ROUTER UTAMA
# --------------------------------------------------------------------------
if st.session_state.selected_article:
    render_article_detail(st.session_state.selected_article)
else:
    render_article_list()