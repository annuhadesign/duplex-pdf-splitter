# Litnus Studio Cetak

Unggah isi folder ini ke root repositori GitHub akun yang terhubung ke Streamlit. Entrypoint: app.py. Jangan mengunggah kredensial asli.

1. Buat database PostgreSQL eksternal dan salin connection string dengan SSL.
2. Buat OAuth client Google tipe Web. Tambahkan authorized redirect URI: https://NAMA-APP.streamlit.app/oauth2callback. Sesuaikan audience/testing users pada Google OAuth.
3. Buka Settings > Secrets pada aplikasi Streamlit. Salin secrets.example.toml dan ganti semua placeholder. Isi admin_emails dengan email Google admin yang tepat. Jangan commit secrets.toml ke GitHub.
4. Jalankan aplikasi. Tabel harga dan riwayat dibuat otomatis; user database membutuhkan izin membuat tabel. Tarif awal mengikuti kode lama.
5. Admin login lewat menu Admin. Ubah tarif, lihat simulasi, isi alasan, lalu simpan. Semua sesi membaca tarif terbaru saat rerun. Simpan ditolak jika versi telah berubah oleh admin lain.

Tanpa database, aplikasi menyediakan pratinjau memakai tarif bawaan; admin tidak bisa menyimpan. Saat database gagal diakses, kalkulasi dihentikan agar tidak menggunakan tarif lama secara diam-diam.

Lokal: pip install -r requirements.txt lalu streamlit run app.py. Untuk kredensial lokal salin contoh menjadi .streamlit/secrets.toml (jangan commit). Python 3.11 disarankan.

Warna mengikuti tema biru malam referensi, tanpa ilustrasi 3D khusus. PDF BW tetap mempertahankan warna asli; grayscale diatur pada mesin cetak. Pilihan halaman manual memakai nomor buku dengan offset Romawi. Kalkulasi manual jumlah halaman tidak dapat menentukan pasangan fisik duplex; masukkan jumlah sesuai rencana produksi.

Diskon khusus hanya tersedia untuk admin dan menggantikan diskon isi otomatis pada pesanan aktif. Diskon finishing tetap mengikuti tabel. Nota berupa estimasi TXT, bukan bukti pembayaran. Riwayat admin menyimpan harga sebelum/sesudah, email, waktu, dan alasan.

Sebelum produksi: uji login Google dengan akun admin/non-admin, koneksi database, persistensi setelah reboot, PDF produksi nyata, serta kesesuaian tarif. Kredensial layanan tidak tersedia pada saat paket disiapkan sehingga koneksi nyata harus diuji setelah pemasangan.
