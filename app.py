"""
News Reader App
================
Aplikasi Streamlit untuk membaca berita dari berbagai sumber RSS Indonesia,
lengkap dengan tampilan isi artikel penuh.

Author : Senior Developer
"""

import re
from datetime import datetime
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
    return _TAG_RE.sub("", raw).strip()

# --------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="News Reader - Berita Terkini",
    page_icon="📰",
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
def _parse_feed_entries(raw_content: bytes):
    """Ubah konten RSS mentah menjadi list of dict entri berita."""
    feed = feedparser.parse(raw_content)
    entries = []
    for e in feed.entries:
        published = None
        for key in ("published", "updated", "pubDate"):
            if key in e:
                try:
                    published = date_parser.parse(e[key])
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
    return dt.strftime("%d %b %Y, %H:%M")


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
# SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("📰 News Reader")
    st.caption("Baca berita terkini dari berbagai sumber terpercaya di Indonesia.")

    st.divider()

    selected_sources = st.multiselect(
        "Pilih sumber berita",
        options=list(RSS_SOURCES.keys()),
        default=["Detik", "Kompas", "CNN Indonesia"],
    )

    keyword = st.text_input("🔎 Cari kata kunci", placeholder="Contoh: ekonomi, pemilu, olahraga...")

    sort_option = st.selectbox(
        "Urutkan berdasarkan",
        options=["Terbaru", "Terlama", "Judul (A-Z)"],
    )

    st.divider()
    if st.button("🔄 Segarkan berita", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Dibuat dengan ❤️ menggunakan Streamlit")


# --------------------------------------------------------------------------
# HALAMAN DETAIL ARTIKEL
# --------------------------------------------------------------------------
def render_article_detail(article: dict):
    st.button("⬅️ Kembali ke daftar berita", on_click=close_article)

    st.title(article["title"])
    meta_col1, meta_col2 = st.columns([1, 1])
    with meta_col1:
        st.caption(f"📅 {format_datetime(article['published'])}")
    with meta_col2:
        st.caption(f"🌐 Sumber: {domain_of(article['link'])}")

    if article.get("image"):
        st.image(article["image"], use_container_width=True)

    st.divider()

    with st.spinner("Mengambil isi artikel lengkap..."):
        full_text = fetch_full_article(article["link"])

    if full_text:
        st.markdown(full_text)
    else:
        st.warning(
            "Isi artikel lengkap tidak dapat diambil secara otomatis. "
            "Silakan baca ringkasan di bawah, atau buka artikel asli melalui tautan."
        )
        clean_summary = strip_html(article.get("summary", "")) or "_Tidak ada ringkasan tersedia._"
        st.markdown(clean_summary)

    st.divider()
    st.link_button("🔗 Baca di situs asli", article["link"], use_container_width=True)


# --------------------------------------------------------------------------
# HALAMAN DAFTAR BERITA
# --------------------------------------------------------------------------
def render_article_list():
    st.title("📰 Berita Terkini")
    st.caption("Kumpulan berita terbaru dari berbagai sumber pilihan Anda.")

    if not selected_sources:
        st.info("Silakan pilih minimal satu sumber berita pada panel di sebelah kiri.")
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
        st.warning(
            "⚠️ Gagal mengambil berita dari: "
            + ", ".join(failed_sources)
            + ". Sumber ini mungkin sedang tidak dapat diakses, atau memblokir "
            "permintaan otomatis. Coba lagi beberapa saat, atau pilih sumber lain."
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
        st.warning("Tidak ada berita yang ditemukan. Coba ubah kata kunci atau sumber berita.")
        return

    st.success(f"Menampilkan {len(all_articles)} berita.")

    # Tampilkan dalam grid 2 kolom
    cols = st.columns(2)
    for idx, article in enumerate(all_articles):
        with cols[idx % 2]:
            with st.container(border=True):
                if article.get("image"):
                    st.image(article["image"], use_container_width=True)
                st.markdown(f"**{article['title']}**")
                st.caption(f"🌐 {article['source']} · 📅 {format_datetime(article['published'])}")
                summary_text = strip_html(article.get("summary", ""))
                if summary_text:
                    st.write((summary_text[:180] + "...") if len(summary_text) > 180 else summary_text)
                st.button(
                    "Baca selengkapnya ➡️",
                    key=f"read_{idx}_{article['link']}",
                    on_click=open_article,
                    args=(article,),
                    use_container_width=True,
                )


# --------------------------------------------------------------------------
# ROUTER UTAMA
# --------------------------------------------------------------------------
if st.session_state.selected_article:
    render_article_detail(st.session_state.selected_article)
else:
    render_article_list()