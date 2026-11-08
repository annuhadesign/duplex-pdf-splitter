# Litnus PrintLab — paket identitas aplikasi

Pembaruan branding berdasarkan `app.py` v1.2.5 dari repositori
`annuhadesign/duplex-pdf-splitter`. Paket ini belum diunggah ke repositori atau diterbitkan.

## 1. Memasang logo dan favicon pada aplikasi Streamlit

Salin isi folder `streamlit/` ke root repositori yang sudah dipakai aplikasi.
Perubahan yang perlu diunggah: `app.py` dan seluruh folder `assets/`.
`engine.py`, `settings.py`, `requirements.txt`, serta `.streamlit/config.toml`
disertakan sebagai dependensi sumber, tanpa perubahan perilaku perhitungan.
Jangan menghapus Secrets pada pengaturan Streamlit Cloud.

Setelah deployment selesai, muat ulang aplikasi. Judul tab menjadi
**Litnus PrintLab**, favicon menggunakan **LP**, dan logo sidebar memakai
wordmark yang sudah dipilih. Halaman masuk menggunakan sidebar yang sama.
Aturan scroll dan layout mobile v1.2.5 dipertahankan.

**Mengunggah folder ini saja tidak mengganti ikon instalasi bawaan Streamlit.**
`page_icon` mengatur favicon halaman, bukan manifest instalasi platform.

## 2. Paket instalasi PWA dengan identitas sendiri

Folder `pwa/` berisi halaman pembungkus, manifest, service worker, dan ikon.
Terbitkan seluruh isinya pada hosting statis HTTPS, misalnya GitHub Pages,
setelah menentukan alamat instalasinya. Path relatif mendukung hosting dalam subfolder.
Untuk GitHub Pages berbasis folder, isi `pwa/` dapat ditempatkan pada folder
`docs/` di repositori, kemudian pilih sumber Pages dari branch dan folder tersebut.
Jangan mengunggah Secrets atau berkas database ke hosting statis.

Halaman pembungkus membuka aplikasi publik yang sudah ada:
`https://litnus-printlab.streamlit.app/?embed=true`.
Instal aplikasi dari **alamat pembungkus yang baru**, bukan dari alamat
`streamlit.app`. Dialog instalasi mengambil nama Litnus PrintLab dan ikon LP
dari manifest pembungkus. Ikon berukuran 192 dan 512 piksel; versi maskable
memakai latar penuh dengan monogram di area tengah.

Jika aplikasi lama sudah terpasang, hapus instalasi lama lalu instal dari
alamat pembungkus setelah nama dan ikon yang benar terlihat pada dialog.
Paket ini tidak secara otomatis mengganti identitas instalasi lama.

## Batasan yang perlu diketahui

- Aplikasi Streamlit tetap memerlukan internet. Service worker hanya menyimpan
  antarmuka pembungkus publik, bukan PDF, sesi, kredensial, atau hasil penghitungan.
- Login Google, cookie, dan kebijakan iframe dapat membatasi akses melalui
  pembungkus. Tombol **Buka langsung** membuka aplikasi pada tab terpisah untuk
  akses penuh. Sesi login tab tersebut belum tentu terbagi dengan iframe.
- Browser menentukan apakah tombol instalasi tersedia. Tombol di halaman
  hanya muncul ketika browser mengirim event instalasi; menu browser juga
  dapat digunakan. Tidak ada janji dukungan offline untuk pengolahan PDF.
- Tampilan browser, login Google, dan dialog instalasi pada hosting tujuan
  masih perlu diuji setelah deployment. Paket belum dinyatakan lolos uji
  instalasi end-to-end.

## Isi aset

- `wordmark.png`: logo lengkap transparan.
- `icon-32.png`, `icon-192.png`, `icon-512.png`: ikon LP.
- `favicon.ico`: ukuran 16, 32, dan 48 piksel dalam satu berkas.
- `apple-touch-icon.png`: 180 piksel.
- `icon-maskable-512.png`: ikon berlatar penuh untuk pemotongan bentuk OS.

## Referensi teknis

- https://docs.streamlit.io/develop/api-reference/configuration/st.set_page_config
- https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest
- https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Define_app_icons
