# News Reader

Web sederhana berbasis **Streamlit** untuk membaca berita terkini dari berbagai sumber media massa Indonesia (Detik, Kompas, CNN Indonesia,Antara News, Tempo, Republika), lengkap dengan tampilan **isi artikel penuh**,pencarian kata kunci, dan pengurutan berita.

## Fitur

- Mengambil berita secara real-time dari beberapa sumber sekaligus
- Pencarian berita berdasarkan kata kunci (judul & ringkasan)
- Pengurutan berita: terbaru, terlama, atau alfabetis
- Menampilkan **isi artikel lengkap** (bukan hanya ringkasan) menggunakan ekstraksi konten otomatis
- Menampilkan gambar/thumbnail artikel jika tersedia
- Caching otomatis agar aplikasi tetap cepat dan tidak membebani sumber berita
- Tampilan responsif dengan grid 2 kolom dan tema yang dapat dikustomisasi

## Struktur Proyek

```
news-reader-app/
├── app.py                   
├── requirements.txt           
├── link.txt
├── config.toml            
└── README.md
```

## Menjalankan Secara Lokal

1. **Clone repository ini**

   ```bash
   git clone https://github.com/<username-anda>/news-reader-app.git
   cd news-reader-app
   ```

2. **Buat virtual environment (opsional tapi disarankan)**

   ```bash
   python -m venv venv
   source venv/bin/activate    
   ```

3. **Install dependency**

   ```bash
   pip install -r requirements.txt
   ```

4. **Jalankan aplikasi**

   ```bash
   streamlit run app.py
   ```

5. Buka browser ke `http://localhost:8501`

## Deploy ke Streamlit Community Cloud (via GitHub)

1. **Push kode ke repository GitHub**

   ```bash
   git init
   git add .
   git commit -m "Initial commit: News Reader App"
   git branch -M main
   git remote add origin https://github.com/<username-anda>/news-reader-app.git
   git push -u origin main
   ```

2. **Buka [share.streamlit.io](https://share.streamlit.io/)** dan login menggunakan akun GitHub Anda.

3. Klik **"New app"**, lalu pilih:
   - **Repository**: `<username-anda>/news-reader-app`
   - **Branch**: `main`
   - **Main file path**: `app.py`

4. Klik **"Deploy"**. Streamlit Cloud akan otomatis:
   - Membaca `requirements.txt` dan menginstall seluruh dependency
   - Membaca `.streamlit/config.toml` untuk tema aplikasi
   - Menjalankan `app.py` sebagai entry point

5. Setelah proses build selesai (biasanya 1–3 menit), aplikasi akan tersedia
   di URL publik seperti:

   ```
   https://<nama-app>-<username>.streamlit.app
   ```

6. Setiap kali Anda melakukan `git push` ke branch `main`, Streamlit Cloud
   akan otomatis melakukan **redeploy**.

## Konfigurasi Tambahan (Opsional)

- **Menambah sumber berita baru**: edit dictionary `RSS_SOURCES` di `app.py`
  dan tambahkan pasangan `"Nama Sumber": "URL RSS"`.
- **Mengatur durasi cache**: ubah nilai `CACHE_TTL_LIST` (daftar berita) dan
  `CACHE_TTL_ARTICLE` (isi artikel penuh) di bagian atas `app.py` — dalam satuan detik.
- **Mengganti tema warna**: ubah nilai pada `.streamlit/config.toml`.

## Teknologi yang Digunakan

| Library         | Kegunaan                                             |
|-----------------|-------------------------------------------------------|
| `streamlit`     | Framework utama untuk membangun antarmuka web         |
| `feedparser`    | Mem-parsing RSS feed dari sumber berita                |
| `requests`      | Mengambil data RSS & halaman artikel via HTTP           |
| `trafilatura`   | Mengekstrak isi artikel lengkap dari halaman HTML       |
| `python-dateutil` | Mem-parsing berbagai format tanggal dari RSS          |
| `lxml`          | Parser HTML/XML performa tinggi (dipakai trafilatura)   |

## Catatan Penting

- Aplikasi ini **tidak menyimpan/scraping** artikel secara ilegal — hanya
  mengambil ringkasan publik dari RSS feed resmi dan menampilkan tautan ke
  sumber asli untuk pembacaan lengkap. Ekstraksi isi artikel dilakukan untuk
  kenyamanan pembaca; **hak cipta konten tetap milik penerbit asli**.
- Beberapa sumber berita dapat sewaktu-waktu mengubah struktur RSS/HTML
  mereka sehingga ekstraksi konten mungkin tidak selalu sempurna. Jika isi
  artikel penuh gagal diambil, aplikasi akan menampilkan ringkasan RSS
  sebagai fallback beserta tautan ke sumber asli.
- Untuk penggunaan skala besar/komersial, disarankan menggunakan API resmi
  dari penyedia berita (misalnya NewsAPI, atau kerja sama langsung dengan penerbit) alih-alih scraping.
