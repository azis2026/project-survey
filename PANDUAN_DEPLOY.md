# Panduan Deployment Gratis (100% Free Tier)

Dokumen ini berisi panduan lengkap langkah demi langkah untuk mendeploy aplikasi **Survey Kepuasan Layanan** menggunakan kombinasi layanan gratis tanpa kartu kredit:

| Komponen | Platform Gratis | Keterangan & Domain |
| :--- | :--- | :--- |
| **Database** | **MongoDB Atlas (M0)** | Gratis 512 MB selamanya |
| **Backend API** | **Render.com** | Free Web Service Python (`https://survey-backend-xxxx.onrender.com`) |
| **Frontend UI** | **Vercel** *(Rekomendasi)* atau **GitHub Pages** | Domain gratis (`*.vercel.app` atau `*.github.io`) |

---

## Tahap 1: Setup MongoDB Atlas (Database Cloud Gratis)

1. Buka [mongodb.com/atlas](https://www.mongodb.com/cloud/atlas/register) dan daftar akun gratis.
2. Saat memilih paket, pilih **M0 Free** (Shared, 512 MB Storage). Pilih lokasi server terdekat (misal: *Singapore*).
3. Buat Database User:
   - Masuk ke menu **Security** -> **Database Access**.
   - Klik **Add New Database User**.
   - Pilih metode **Password**, masukkan Username (misal: `adminsurvey`) dan Password yang kuat (catat password ini).
   - Berikan role **Read and write to any database**.
4. Buka akses jaringan (Network Access):
   - Masuk ke menu **Security** -> **Network Access**.
   - Klik **Add IP Address**, lalu klik tombol **Allow Access from Anywhere** (`0.0.0.0/0`).
   - Klik **Confirm**.
5. Salin Connection String:
   - Kembali ke tab **Database**, klik **Connect** pada cluster Anda.
   - Pilih **Drivers** -> Driver: **Python**, Version: **3.12 or later**.
   - Salin connection string yang formatnya seperti ini:
     ```text
     mongodb+srv://adminsurvey:<password>@cluster0.xxxx.mongodb.net/?retryWrites=true&w=majority
     ```
   - Ganti `<password>` dengan password yang Anda buat di langkah 3.

---

## Tahap 2: Upload Proyek ke GitHub

1. Buka [github.com](https://github.com) dan buat repository baru (misal: `project-survey`), pilih **Public** atau **Private**.
2. Di komputer lokal Anda (terminal di folder `c:\Users\harit\Music\Project Survey`), jalankan perintah berikut:

```powershell
# 1. Inisialisasi Git
git init

# 2. Tambahkan semua file yang sudah siap (file .env sudah otomatis aman di-ignore)
git add .

# 3. Buat commit pertama
git commit -m "feat: setup cloud deployment for render, vercel, and mongodb atlas"

# 4. Ganti branch utama menjadi main
git branch -M main

# 5. Hubungkan ke repository GitHub Anda (ganti URL di bawah dengan URL repo Anda)
git remote add origin https://github.com/<username-github-anda>/project-survey.git

# 6. Push kode ke GitHub
git push -u origin main
```

---

## Tahap 3: Deploy Backend ke Render.com (Gratis)

1. Buka [render.com](https://render.com) dan login menggunakan akun GitHub Anda.
2. Di Dashboard Render, klik **New +** -> pilih **Blueprint** (atau **Web Service**).
   - *Jika memilih Blueprint*: Render akan membaca file `render.yaml` yang sudah kami siapkan secara otomatis!
   - *Jika memilih Web Service manual*:
     - Pilih repository `project-survey`.
     - **Name**: `survey-backend`
     - **Root Directory**: `backend`
     - **Runtime**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
     - **Instance Type**: `Free`
3. Masukkan **Environment Variables**:
   - `MONGO_URL` = *(Connection string MongoDB Atlas dari Tahap 1)*
   - `DB_NAME` = `survey_db`
   - `JWT_SECRET` = *(string acak untuk keamanan token, min. 32 karakter)*
   - `ADMIN_EMAIL` = `admin@domain.com` *(Email untuk login admin awal)*
   - `ADMIN_PASSWORD` = *(Password untuk login admin awal)*
   - `FRONTEND_URL` = *(Isi sementara dengan `http://localhost:3000`, nanti akan diupdate setelah frontend live)*
4. Klik **Create Web Service**.
5. Tunggu proses build selesai. Setelah status menjadi **Live**, salin URL backend Anda, contoh:
   ```text
   https://survey-backend-xxxx.onrender.com
   ```

---

## Tahap 4: Deploy Frontend

### Pilihan A: Menggunakan Vercel (SANGAT DIREKOMENDASIKAN)
Vercel adalah cara termudah karena secara otomatis menangani routing React (`/admin`, `/survey/:slug`), gratis domain SSL, dan terhubung langsung ke GitHub.

1. Buka [vercel.com](https://vercel.com) dan login dengan akun GitHub Anda.
2. Klik **Add New...** -> **Project**.
3. Import repository `project-survey`.
4. Di halaman konfigurasi:
   - **Framework Preset**: `Create React App`
   - **Root Directory**: Klik **Edit** dan pilih folder `frontend`.
5. Buka bagian **Environment Variables**, tambahkan:
   - **Key**: `REACT_APP_BACKEND_URL`
   - **Value**: `https://survey-backend-xxxx.onrender.com` *(URL Backend Render Anda tanpa garis miring di akhir)*
6. Klik **Deploy**.
7. Dalam 1-2 menit, aplikasi Anda sudah live dengan domain gratis, contoh:
   ```text
   https://project-survey.vercel.app
   ```

---

### Pilihan B: Menggunakan GitHub Pages
Jika Anda memilih menggunakan GitHub Pages:

1. Di repository GitHub Anda, masuk ke **Settings** -> **Secrets and variables** -> **Actions**.
2. Tambahkan Repository Secret:
   - `REACT_APP_BACKEND_URL` = `https://survey-backend-xxxx.onrender.com`
3. Anda bisa menggunakan GitHub Actions untuk build dan deploy folder `frontend/build` ke branch `gh-pages`. (File `404.html` untuk SPA redirect sudah kami siapkan di `frontend/public/404.html`).

---

## Tahap 5: Hubungkan Frontend ke Backend (Langkah Terakhir)

1. Kembali ke dashboard **Render.com** -> Buka Web Service backend Anda.
2. Masuk ke tab **Environment**.
3. Ubah variabel `FRONTEND_URL` menjadi URL frontend Anda, contoh:
   ```text
   https://project-survey.vercel.app
   ```
4. Klik **Save Changes**. Render akan me-restart backend secara otomatis dengan izin CORS yang sesuai.

---

## Tahap 6: Uji Coba Aplikasi

1. Buka URL Frontend Anda (contoh: `https://project-survey.vercel.app`).
2. Masuk ke halaman login admin:
   `https://project-survey.vercel.app/admin/login`
3. Login menggunakan `ADMIN_EMAIL` dan `ADMIN_PASSWORD` yang Anda masukkan di Render.
4. Anda sekarang dapat mengelola survey, melihat grafik analitik, mengunduh laporan Excel, dan mengatur branding!
