# 📋 DOKUMENTASI AKSES & PANDUAN PENGOPERASIAN
## Sistem Survey Kepuasan Layanan (Live Production)

Dokumen ini berisi informasi resmi mengenai tautan akses, kredensial login admin, serta panduan operasional penggunaan aplikasi untuk masyarakat dan pihak pengelola instansi.

---

## 🌐 1. Tautan Akses (Live Cloud)

### A. Tautan untuk Masyarakat / Responden (Frontend)
Tautan ini adalah yang dibagikan kepada masyarakat luas, dicetak dalam bentuk banner/QR Code, atau di-share melalui media sosial/WhatsApp:

* **Halaman Survey Publik:**
  ```text
  https://<domain-vercel-anda>.vercel.app/survey/pelayanan-umum
  ```
  *(Atau buka langsung halaman utama `https://<domain-vercel-anda>.vercel.app`, sistem akan otomatis mengarahkan ke survey yang aktif)*

* **Akses Lokal (Jika dijalankan di komputer kantor):**
  ```text
  http://localhost:3000/survey/pelayanan-umum
  ```

---

### B. Tautan untuk Pengelola / Admin
Tautan khusus ini digunakan oleh staf atau pimpinan untuk memantau grafik, melihat masukan responden, mengunduh laporan Excel, dan mengatur branding instansi:

* **Halaman Login Admin:**
  ```text
  https://<domain-vercel-anda>.vercel.app/admin/login
  ```
* **Dashboard Admin (Setelah Login):**
  ```text
  https://<domain-vercel-anda>.vercel.app/admin
  ```

---

### C. Tautan Backend API & Server Cloud
* **API Base URL (Railway):**
  `https://survey-backend-production-f2d0.up.railway.app`
* **Health Check Server:**
  `https://survey-backend-production-f2d0.up.railway.app/health`
* **Database Cloud:**
  MongoDB Atlas Cluster (`adminsurvey.oeuag0h.mongodb.net`)

---

## 🔑 2. Akun & Kredensial Login Admin

Untuk masuk ke halaman Admin (`/admin/login`), gunakan salah satu kredensial di bawah ini sesuai yang Anda masukkan di Railway:

| Parameter | Kredensial Yang Anda Set di Railway | Kredensial Default Sistem |
| :--- | :--- | :--- |
| **Email Admin** | `admin@domain.com` *(atau email yang Anda isi)* | `admin@survey.local` |
| **Password Admin** | `PasswordAdminKu123!` *(atau password yang Anda isi)* | `AdminSurvey2026!` |
| **Role** | `Super Admin` | `Super Admin` |

> 💡 **Tips Keamanan:** Setelah berhasil masuk ke Dashboard Admin, Anda dapat mengganti password kapan saja melalui menu **Ganti Password** di pojok kanan atas dashboard.

---

## 🛠️ 3. Panduan Fitur & Pengoperasian

### 1. Cara Mengunduh Laporan ke Excel (.xlsx)
1. Buka halaman admin dan login.
2. Di halaman Dashboard Utama, Anda akan melihat ringkasan grafik bintang, nilai rata-rata kepuasan, dan tabel komentar responden.
3. Gunakan filter periode (misal: *Hari Ini*, *7 Hari Terakhir*, *30 Hari Terakhir*, atau *Bulan Ini*).
4. Klik tombol **Export Excel** di pojok kanan atas tabel.
5. File `.xlsx` rapi akan otomatis terunduh dan siap dilampirkan untuk laporan pimpinan atau evaluasi bulanan.

### 2. Cara Mengambil & Mencetak QR Code Survey
1. Di Dashboard Admin, masuk ke menu **Survey** (atau klik tombol **QR Code** pada survey yang aktif).
2. Klik tombol **Unduh QR Code**.
3. Gambar QR Code beresolusi tinggi akan tersimpan di komputer Anda.
4. Anda dapat mencetak QR Code tersebut pada:
   - Standing akrilik di meja loket / ruang tunggu.
   - X-Banner di pintu masuk instansi.
   - Struk antrean atau brosur pelayanan.
5. Warga cukup membuka kamera smartphone untuk langsung mengisi survey tanpa perlu mengetik link.

### 3. Mengatur Nama Instansi & Logo (Branding)
1. Di Dashboard Admin, buka tab **Branding / Pengaturan**.
2. Ubah **Nama Instansi** (contoh: *Puskesmas Maju Sehat*, *Kantor Pelayanan Terpadu*, dsb.).
3. Pilih **Warna Tema** yang sesuai dengan identitas instansi Anda.
4. Unggah **Logo Resmi Instansi**.
5. Klik **Simpan Perubahan**. Seluruh tampilan survey publik akan otomatis mengikuti identitas instansi Anda.

---

## 🛡️ 4. Informasi Teknis & Keamanan

1. **Anonimitas Penuh:** Responden tidak dimintai data sensitif (KTP, No HP, Nama), sehingga meningkatkan kejujuran pengisian dan mematuhi privasi data.
2. **Anti-Spam Rate Limiting:** Sistem secara cerdas membatasi pengiriman berulang-ulang dalam hitungan detik dari jaringan yang sama menggunakan hashing IP terenkripsi.
3. **Penyimpanan Data Persisten:** Seluruh data tersimpan di MongoDB Atlas Cloud dengan enkripsi otomatis, backup berkala, dan kapasitas gratis hingga 512 MB (mampu menampung ratusan ribu data survey).
4. **Keamanan Token JWT:** Sesi login admin menggunakan token JWT terenkripsi dengan proteksi cookie `HttpOnly` dan `Secure`.

---

*Dokumentasi ini dibuat otomatis pada: 2026-10-08*
