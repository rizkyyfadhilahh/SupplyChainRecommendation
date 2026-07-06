# Supply Chain Recommendation System — Run Guide

Panduan ini menjelaskan cara menjalankan project dari awal setelah source code diterima tanpa `venv`, `node_modules`, `.next`, dan package hasil instalasi lainnya.

---

## 1. Struktur Project

Pastikan struktur folder utama seperti berikut:

```txt
project/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── data_loader.py
│   │   ├── domain_config.json      ← sudah ada di repo
│   │   ├── routers/
│   │   ├── services/
│   │   └── repositories/
│   │
│   ├── temp_data/                  ← WAJIB dibuat dan diisi dari Google Drive
│   │   ├── 3 month/
│   │   │   ├── events_bc_01_Des_24_Feb.csv
│   │   │   └── links_bc_01_Des_24_Feb.csv
│   │   ├── master_facility.csv
│   │   ├── trans_mb51_ds_*.csv     (opsional, untuk stok)
│   │   └── restan_mb51_ds_*.csv    (opsional, untuk stok)
│   │
│   ├── requirements.txt
│   └── .env                        ← WAJIB dibuat manual
│
└── frontend/
    ├── app/
    ├── package.json
    └── .env.local                  ← WAJIB dibuat manual
```

Folder berikut **tidak disertakan** dan harus dibuat/install ulang:

```txt
backend/venv/
backend/temp_data/          ← download dari Google Drive
backend/.env                ← buat manual
frontend/node_modules/
frontend/.next/
frontend/.env.local         ← buat manual
```

---

## 2. Download Data dari Google Drive

⚠️ **Langkah paling penting!** Tanpa data ini, aplikasi tidak bisa jalan.

### Link Download:
**https://drive.google.com/drive/folders/1IF2N68c-bCimWUCS0fpoNTDrAKWWXSV0?usp=sharing**

### Cara Download:

1. Buka link di atas
2. Download **semua file CSV** yang ada
3. Buat folder `backend/temp_data/`:
   ```bash
   mkdir backend/temp_data
   mkdir "backend/temp_data/3 month"
   ```
4. Pindahkan file-file yang sudah didownload ke folder yang sesuai:
   - `events_bc_01_Des_24_Feb.csv` → `backend/temp_data/3 month/`
   - `links_bc_01_Des_24_Feb.csv` → `backend/temp_data/3 month/`
   - `master_facility.csv` → `backend/temp_data/`
   - File stok (trans_mb51, restan_mb51) → `backend/temp_data/`

### Checklist File Data:

- [ ] Folder `backend/temp_data/3 month/` sudah dibuat
- [ ] File `events_bc_01_Des_24_Feb.csv` ada di folder `3 month/`
- [ ] File `links_bc_01_Des_24_Feb.csv` ada di folder `3 month/`
- [ ] File `master_facility.csv` ada di folder `temp_data/`
- [ ] (Opsional) File stok `trans_mb51_*.csv` dan `restan_mb51_*.csv` ada di `temp_data/`

---

## 3. Persiapan Backend

### 3a. Masuk ke folder backend

```bash
cd backend
```

### 3b. Buat virtual environment

```bash
python -m venv venv
```

### 3c. Aktifkan virtual environment

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

Jika PowerShell memblokir aktivasi:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 3d. Install package backend

```bash
pip install -r requirements.txt
```

⏱️ Proses ini butuh **5-10 menit** karena install package berat (pandas, numpy, xgboost, dll).

---

## 4. Setup Environment Backend

### 4a. Buat file `.env`

Buat file `.env` di dalam folder `backend/`:

**Windows PowerShell:**
```powershell
New-Item -Path .env -ItemType File
```

**Linux / macOS:**
```bash
touch .env
```

### 4b. Isi file `.env`

Copy paste konfigurasi berikut ke file `backend/.env`:

```env
API_KEY=dev-secret-key
ALLOWED_ORIGINS=http://localhost:3000
APP_DEBUG=false
```

⚠️ **Nilai `API_KEY` HARUS sama persis** dengan yang ada di `frontend/.env.local` nanti.

---

## 5. Cek Backend

### 5a. Pastikan masih di folder backend dan venv aktif

```bash
# Harus terlihat (venv) di awal prompt
(venv) PS C:\project\backend>
```

### 5b. Jalankan backend

```bash
uvicorn app.main:app --reload
```

### 5c. Tunggu data loading selesai

Backend akan load data besar ke SQLite. Tunggu hingga muncul log:

```
load_application_data STARTING
loading master_facility
loading events_bc
...
load_application_data FINISHED
Application data loaded successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

⏱️ Proses loading butuh **2-5 menit** tergantung ukuran file CSV.

### 5d. Cek backend berjalan

Buka browser dan akses:

```
http://localhost:8000/health
```

Harus menampilkan:

```json
{"status": "ok"}
```

Cek data sudah dimuat:

```
http://localhost:8000/health/data
```

Harus menampilkan:

```json
{"status": "ready", "app_data_loaded": true}
```

Jika `"status": "initializing"`, artinya data masih dimuat. Tunggu sebentar lagi.

---

## 6. Persiapan Frontend

### 6a. Buka terminal baru

⚠️ **Jangan tutup terminal backend!** Buka terminal baru.

### 6b. Masuk ke folder frontend

```bash
cd frontend
```

### 6c. Install package frontend

```bash
npm install
```

⏱️ Proses ini butuh **3-5 menit**.

---

## 7. Setup Environment Frontend

### 7a. Buat file `.env.local`

Buat file `.env.local` di dalam folder `frontend/`:

**Windows PowerShell:**
```powershell
New-Item -Path .env.local -ItemType File
```

**Linux / macOS:**
```bash
touch .env.local
```

### 7b. Isi file `.env.local`

Copy paste konfigurasi berikut ke file `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-secret-key
```

⚠️ **Nilai `NEXT_PUBLIC_API_KEY` HARUS sama** dengan `API_KEY` di `backend/.env`.

---

## 8. Jalankan Frontend

```bash
npm run dev
```

Frontend akan berjalan di:

```
http://localhost:3000
```

Buka URL tersebut di browser.

---

## 9. Cara Menjalankan Project (Summary)

Gunakan **dua terminal** terpisah:

### Terminal 1 — Backend

```bash
cd backend
.\venv\Scripts\Activate.ps1   # Windows
# atau: source venv/bin/activate  (Linux/macOS)

uvicorn app.main:app --reload
```

Backend berjalan di: **http://localhost:8000**

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Frontend berjalan di: **http://localhost:3000**

---

## 10. Troubleshooting

### ❌ Backend error: `load_application_data FAILED`

**Penyebab:** File CSV tidak ditemukan.

**Solusi:**
1. Pastikan folder `backend/temp_data/` ada
2. Pastikan file CSV sudah didownload dari Google Drive
3. Cek nama file dan struktur folder sesuai [Bagian 2](#2-download-data-dari-google-drive)

---

### ❌ Error 401 di semua request

**Penyebab:** API key tidak sama antara backend dan frontend.

**Solusi:**
1. Buka `backend/.env` dan `frontend/.env.local`
2. Pastikan nilai `API_KEY` dan `NEXT_PUBLIC_API_KEY` **sama persis**: `dev-secret-key`
3. Restart backend dan frontend

---

### ❌ Frontend error: `ECONNREFUSED`

**Penyebab:** Backend belum berjalan.

**Solusi:**
1. Pastikan backend sudah jalan di terminal pertama
2. Cek `http://localhost:8000/health` di browser
3. Jika belum jalan, jalankan backend dulu sebelum frontend

---

### ❌ Backend error: `ModuleNotFoundError`

**Penyebab:** Virtual environment belum aktif atau package belum terinstall.

**Solusi:**
```bash
cd backend
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

### ❌ PowerShell menolak aktivasi venv

**Solusi:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

---

### ❌ Data tidak ditemukan saat trace

**Penyebab:** Folder `temp_data` kosong atau file CSV belum ada.

**Solusi:**
1. Download file dari Google Drive (lihat [Bagian 2](#2-download-data-dari-google-drive))
2. Pastikan struktur folder benar
3. Restart backend

---

### ❌ `health/data` selalu menampilkan `"initializing"`

**Penyebab:** Data masih dimuat atau gagal dimuat.

**Solusi:**
1. Tunggu **2-5 menit** — file events_bc sangat besar
2. Jika lebih dari 10 menit, cek log error di terminal backend
3. Reload data tanpa restart:
   ```bash
   curl -X POST -H "X-API-Key: dev-secret-key" http://localhost:8000/api/system/reload
   ```

---

## 11. Catatan Penting

### File yang tidak di-commit ke Git

```txt
backend/.env                ← berisi API key
frontend/.env.local         ← berisi API key
backend/temp_data/          ← data bisnis (ratusan MB)
backend/venv/               ← virtual environment
frontend/node_modules/      ← dependencies
frontend/.next/             ← build artifacts
```

### API Key

⚠️ Untuk project ini, gunakan API key: **`dev-secret-key`**

Pastikan nilai ini **sama persis** di:
- `backend/.env` → `API_KEY=dev-secret-key`
- `frontend/.env.local` → `NEXT_PUBLIC_API_KEY=dev-secret-key`

### Dokumentasi API

Setelah backend berjalan, akses Swagger UI untuk dokumentasi lengkap:

```
http://localhost:8000/docs
```

Klik **Authorize** dan masukkan API key: `dev-secret-key`

---

## 12. Quick Start (TL;DR)

```bash
# 1. Download data dari Google Drive
# https://drive.google.com/drive/folders/1IF2N68c-bCimWUCS0fpoNTDrAKWWXSV0?usp=sharing
# Taruh di backend/temp_data/

# 2. Setup Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Buat backend/.env dengan isi:
# API_KEY=dev-secret-key
# ALLOWED_ORIGINS=http://localhost:3000
# APP_DEBUG=false

uvicorn app.main:app --reload

# 3. Setup Frontend (terminal baru)
cd frontend
npm install

# Buat frontend/.env.local dengan isi:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# NEXT_PUBLIC_API_KEY=dev-secret-key

npm run dev

# 4. Buka browser
# http://localhost:3000
```

---