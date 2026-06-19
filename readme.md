# Supply Chain Recommendation System — Run Guide

Panduan ini menjelaskan cara menjalankan project dari awal setelah source code diterima tanpa `venv`, `node_modules`, `.next`, dan package hasil instalasi lainnya.

## 1. Struktur Project

Pastikan struktur folder utama seperti berikut:

```txt
project_refactor/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── middleware.py
│   │   ├── config.py
│   │   ├── data_loader.py
│   │   ├── schemas.py
│   │   ├── utils.py
│   │   ├── repositories/
│   │   └── services/
│   │
│   ├── temp_data/
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
│
└── frontend/
    ├── app/
    ├── components/
    ├── package.json
    ├── package-lock.json
    ├── next.config.js
    └── .env.local
```

Folder berikut memang tidak disertakan dan harus dibuat/install ulang di masing-masing device:

```txt
venv/
frontend/.env.local
node_modules/
.next/
__pycache__/
```

Untuk folder temp_data yang perlu diletakkan pada backend -> /backend/temp_data -> dapat didownload pada link: https://drive.google.com/drive/folders/1IF2N68c-bCimWUCS0fpoNTDrAKWWXSV0?usp=sharing

---

## 2. Persiapan Backend

Masuk ke folder backend:

```bash
cd backend
```

Buat virtual environment:

```bash
python -m venv venv
```

Aktifkan virtual environment.

Untuk Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Jika PowerShell memblokir aktivasi, jalankan:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Install package backend:

```bash
pip install -r requirements.txt
```

---

## 3. Setup Environment Backend

Buat file `.env` di dalam folder `backend`.

Contoh isi:

```env
APP_DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000
API_KEY=dev-secret-key
```

Pastikan folder data tersedia di:

```txt
backend/temp_data/
```

Jika data belum ada, backend tidak akan bisa memuat data recommendation.

---

## 4. Cek Backend

Sebelum menjalankan server, lakukan compile check:

```bash
python -m compileall app
```

Jika tidak ada error, jalankan backend:

```bash
uvicorn app.main:app --reload
```

Backend akan berjalan di:

```txt
http://localhost:8000
```

Cek backend melalui browser:

```txt
http://localhost:8000/health
http://localhost:8000/api/options
http://localhost:8000/api/sloc-master
```

Jika endpoint health menampilkan response seperti berikut, backend sudah berjalan:

```json
{
  "status": "ok"
}
```

---

## 5. Persiapan Frontend

Buka terminal baru, lalu masuk ke folder frontend:

```bash
cd frontend
```

Install package frontend:

```bash
npm install
```

---

## 6. Setup Environment Frontend

Buat file `.env.local` di dalam folder `frontend`.

Contoh isi untuk local development:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-secret-key
```

Pastikan `NEXT_PUBLIC_API_KEY` sama dengan `API_KEY` pada file backend `.env`.

---

## 7. Jalankan Frontend

Jalankan frontend:

```bash
npm run dev
```

Frontend akan berjalan di:

```txt
http://localhost:3000
```

Buka URL tersebut di browser.

---

## 8. Cara Menjalankan Project Secara Lengkap

Gunakan dua terminal.

### Terminal 1 — Backend

```bash
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Backend berjalan di:

```txt
http://localhost:8000
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Frontend berjalan di:

```txt
http://localhost:3000
```

Buka aplikasi melalui browser:

```txt
http://localhost:3000
```

---

## 9. Troubleshooting

### Backend error karena package belum ada

Jalankan ulang:

```bash
pip install -r requirements.txt
```

### Frontend error karena package belum ada

Jalankan ulang:

```bash
npm install
```

### Backend tidak menemukan module `app`

Pastikan command dijalankan dari folder `backend`, bukan dari root project.

Command yang benar:

```bash
uvicorn app.main:app --reload
```

Bukan:

```bash
uvicorn main:app --reload
```

### Frontend gagal connect ke backend

Pastikan backend sudah berjalan di:

```txt
http://localhost:8000
```

Pastikan isi `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=dev-secret-key
```

Setelah mengubah `.env.local`, restart frontend:

```bash
npm run dev
```

### Error 401 saat update SLOC config

Pastikan API key sama antara backend dan frontend.

Backend `.env`:

```env
API_KEY=dev-secret-key
```

Frontend `.env.local`:

```env
NEXT_PUBLIC_API_KEY=dev-secret-key
```

### Error data tidak ditemukan

Pastikan folder berikut tersedia:

```txt
backend/temp_data/
```

Dan file CSV yang dibutuhkan sudah berada di folder tersebut.

---

## 10. Catatan Penting

File/folder berikut tidak perlu dikirim karena akan dibuat ulang saat setup:

```txt
venv/
node_modules/
.next/
__pycache__/
*.pyc
```

File berikut tidak boleh dibagikan sembarangan karena berisi konfigurasi lokal atau secret:

```txt
backend/.env
frontend/.env.local
```

Gunakan `.env.example` sebagai contoh konfigurasi.
