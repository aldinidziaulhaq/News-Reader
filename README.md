# News Reader

Web sederhana berbasis Streamlit untuk membaca berita terkini dari media Indonesia: Detik, Kompas, CNN Indonesia, Antara News, Tempo, dan Republika, lengkap dengan isi artikel penuh, pencarian kata kunci, dan pengurutan berita.

## Fitur

- Ambil berita dari beberapa sumber sekaligus
- Cari berita berdasarkan kata kunci (judul dan ringkasan)
- Urutkan berita: terbaru, terlama, atau A-Z
- Tampilkan isi artikel lengkap, bukan hanya ringkasan
- Tampilkan gambar artikel jika tersedia
- Cache otomatis agar aplikasi tetap cepat
- Tampilan responsif: satu berita utama dan grid 3 kolom

## Struktur Proyek

```
news-reader-app/
├── app.py
├── requirements.txt
├── link.txt
├── .streamlit/
├── config.toml
└── README.md
```

## Menjalankan Secara Lokal

```bash
git clone https://github.com/<username-anda>/news-reader-app.git
cd news-reader-app
pip install -r requirements.txt
streamlit run app.py
```

Buka `http://localhost:8501` di browser.

## Deploy ke Streamlit Community Cloud

1. Push kode ke GitHub:

   ```bash
   git init
   git add .
   git commit -m "Initial commit: News Reader App"
   git branch -M main
   git remote add origin https://github.com/<username-anda>/news-reader-app.git
   git push -u origin main
   ```

2. Buka [share.streamlit.io](https://share.streamlit.io/) dan login dengan akun GitHub.
3. Klik **New app**, pilih repository, branch `main`, dan file utama `app.py`.
4. Klik **Deploy**. Setelah selesai, aplikasi tersedia di `https://<nama-app>-<username>.streamlit.app` dan otomatis diperbarui setiap kali Anda `git push`.

## Konfigurasi

- Tambah sumber berita: edit `RSS_SOURCES` di `app.py`.
- Atur durasi cache: ubah `CACHE_TTL_LIST` dan `CACHE_TTL_ARTICLE` (dalam detik).
- Ganti tema warna: ubah `.streamlit/config.toml`.

## Library

| Library           | Kegunaan                                  |
|-------------------|-------------------------------------------|
| `streamlit`       | Antarmuka web                             |
| `feedparser`      | Membaca RSS feed                          |
| `requests`        | Mengambil data RSS dan halaman artikel    |
| `trafilatura`     | Mengekstrak isi artikel lengkap           |
| `python-dateutil` | Membaca format tanggal dari RSS           |
| `lxml`            | Parser HTML/XML untuk trafilatura         |

## Catatan

- Hak cipta konten tetap milik penerbit asli. Aplikasi hanya membaca RSS publik dan menyediakan tautan ke sumber asli.
- Jika isi artikel penuh gagal diambil, aplikasi menampilkan ringkasan RSS beserta tautan ke sumber asli.
- Untuk penggunaan skala besar atau komersial, gunakan API resmi penyedia berita.