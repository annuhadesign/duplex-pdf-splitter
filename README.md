# Litnus Studio Cetak

Unggah isi folder ini ke root repositori GitHub akun yang terhubung ke Streamlit. Entrypoint: app.py. Jangan mengunggah kredensial asli.

1. Buat database PostgreSQL eksternal dan salin connection string dengan SSL.
2. Buat OAuth client Google tipe Web. Tambahkan authorized redirect URI: https://NAMA-APP.streamlit.app/oauth2callback. Sesuaikan audience/testing users pada Google OAuth.
3. Buka Settings > Secrets pada aplikasi Streamlit. Salin secrets.example.toml dan ganti semua placeholder. Isi admin_emails dengan email Google admin yang tepat. Jangan commit secrets.toml ke GitHub.
4. Jalankan aplikasi. Tabel harga dan riwayat dibuat otomatis; user database membutuhkan izin membuat tabel. Tarif awal mengikuti kode lama.
5. Admin login lewat menu Admin. Ubah tarif, lihat simulasi, isi alasan, lalu simpan. Semua sesi membaca tarif terbaru saat rerun. Simpan ditolak jika versi telah berubah oleh admin lain.

Tanpa database, aplikasi menyediakan pratinjau memakai tarif bawaan; admin tidak bisa menyimpan. Saat database gagal diakses, kalkulasi dihentikan agar tidak menggunakan tarif lama secara diam-diam.

Lokal: pip install -r requirements.txt lalu streamlit run app.py. Untuk kredensial lokal salin contoh menjadi .streamlit/secrets.toml (jangan commit). Python 3.11 disarankan.

PDF BW tetap mempertahankan warna asli; grayscale diatur pada mesin cetak. Pilihan halaman manual memakai nomor buku dengan offset Romawi. Kalkulasi manual jumlah halaman tidak dapat menentukan pasangan fisik duplex; masukkan jumlah sesuai rencana produksi.

Diskon khusus hanya tersedia untuk admin dan menggantikan diskon isi otomatis pada pesanan aktif. Diskon finishing tetap mengikuti tabel. Nota berupa estimasi TXT, bukan bukti pembayaran. Riwayat admin menyimpan harga sebelum/sesudah, email, waktu, dan alasan.

Sebelum produksi: uji login Google dengan akun admin/non-admin, koneksi database, persistensi setelah reboot, PDF produksi nyata, serta kesesuaian tarif. Kredensial layanan tidak tersedia pada saat paket disiapkan sehingga koneksi nyata harus diuji setelah pemasangan.

## Pembaruan v1.1.0

Ekstrak ZIP di komputer. Jika aplikasi sudah terpasang, unggah app.py dan README.md ke halaman utama repositori GitHub. Kemudian buka folder .streamlit di GitHub dan unggah config.toml dari folder .streamlit hasil ekstrak. Commit ke main. Pengaturan Secrets yang sudah ada tetap dipakai. Untuk pemasangan baru, unggah semua isi ZIP dengan struktur folder yang sama.

Sidebar menyediakan Kalkulator Cepat, Deteksi Warna PDF, Pilah Halaman PDF, dan Admin Tarif. Ketiga alat produksi dapat dipakai tanpa login. Login Google dan daftar admin tetap mengikuti Secrets. Petunjuk per menu tersedia melalui tombol ⓘ.

Setiap menu menyimpan draf sendiri selama sesi Streamlit aktif. Draf dan unggahan tidak ditulis ke Neon. Sesi baru, tab baru, penyegaran browser, dan proses masuk/keluar dapat mereset draf. Tarif tersimpan di Neon dan dipakai bersama. Tema terang menggunakan mint dan teal. Tema gelap tersedia lewat menu Theme Streamlit. Bilah judul PWA dikendalikan browser.

Sesudah deploy, masukkan judul dan jumlah halaman di Kalkulator Cepat. Pindah ke Pilah Halaman PDF, masukkan preliminaries dan unggah PDF, lalu kembali ke kedua menu untuk mengecek drafnya. Cek unduhan nota dan masuk ke Admin Tarif dengan akun Google yang sudah terdaftar. Uji juga satu jendela privat untuk memastikan akses tamu dapat menghitung dan halaman tarif meminta login.
