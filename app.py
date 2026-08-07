// =================================================================
// KONFIGURASI UTAMA SPREADSHEET & LIST DROPDOWN
// =================================================================

var SPREADSHEET_ID = "1TWvoAWkmXz7rus9YMIPuMoJSHmRSd_acMEWMmLGrL50";

var LIST_PJ = [
  "Nony", "Kelvin", "Ilyas", "Rian", "Noufal", "Hasan", "Dicky", "Aji", "Syafri", 
  "Edo", "Ulin", "Mila", "Audy", "Iqbal 3", "gusti", "Aqli", "Riski", "Azizah", 
  "Diyah", "Faiz", "Alvi", "Tomy", "Novi", "Adinda", "Ghoni", "Azizah 3", "Winda"
];

var LIST_MARKETING = [
  "FAIZ", "FEBI", "ALVI", "IQBAL", "ZULYA", "GUSTI", "KHOIR", "TOMY", "RIZPER", 
  "TIARA", "AQLI", "MILA", "DIYAH", "AISYAH", "AUDY", "TOMO", "PAK SAROMAD", 
  "IQBAL 4", "MUHAIMIN", "JACQ", "ULIN", "RIAN"
];

var LIST_UKURAN = ["UNESCO", "A5", "B5", "A4", "A6", "CUSTOM"];
var LIST_KERTAS = ["HVS 70", "HVS 80", "HVS 60", "BOOKPAPER", "ARTPAPER 120"];

// =================================================================
// FUNGSI UTAMA PROSES ORDERAN
// =================================================================

function prosesOrderanCetakBuku() {
  // 1. FILTER EMAIL (4 EMAIL)
  var searchQuery = 'in:inbox category:primary is:unread (' +
    'from:regulerlitnus@gmail.com OR ' +
    'from:nafalglobalnusantara@gmail.com OR ' +
    'from:cetakbukumu.id@gmail.com OR ' +
    'from:penerbitlitnus@gmail.com)';
  
  // 2. BUKA SPREADSHEET & AMBIL/BUAT SHEET BULANAN
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var timeZone = ss.getSpreadsheetTimeZone();
  var monthNames = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"];
  var now = new Date();
  var sheetName = monthNames[now.getMonth()];
  var sheet = getOrCreateMonthlySheet(ss, sheetName);
  
  // 3. CARI EMAIL
  var threads = GmailApp.search(searchQuery);
  
  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    var messages = thread.getMessages();
    var latestMessage = messages[messages.length - 1]; // EMAIL TERBARU
    
    var rawSubject = latestMessage.getSubject().trim();
    var body = latestMessage.getPlainBody();
    
    // A. DETEKSI JENIS CETAK & TANGGAL CETAK SEBELUMNYA
    var isReprint = messages.length > 1 || rawSubject.toLowerCase().indexOf("re:") === 0 || rawSubject.toLowerCase().indexOf("fwd:") === 0;
    var jenisCetak = isReprint ? "CETAK ULANG" : "BARU CETAK";
    
    var tglCetakSebelumnya = "";
    if (messages.length > 1) {
      var prevMessage = messages[messages.length - 2];
      var prevDate = prevMessage.getDate();
      tglCetakSebelumnya = Utilities.formatDate(prevDate, timeZone, "dd/MM/yyyy HH:mm");
    }
    
    // B. DETEKSI CLIENT (DI-UPDATE: MENGGUNAKAN MATCH 'LITNUS' UNTUK SEMUA EMAIL LITNUS)
    var senderEmail = latestMessage.getFrom().toLowerCase();
    var client = "UMUM";
    if (senderEmail.indexOf("litnus") !== -1) {
      client = "LITNUS";
    } else if (senderEmail.indexOf("nafalglobalnusantara@gmail.com") !== -1) {
      client = "NAFAL";
    } else if (senderEmail.indexOf("cetakbukumu.id@gmail.com") !== -1) {
      client = "UMUM";
    }
    
    // C. PARSING JUDUL & PENULIS
    var cleanSubject = rawSubject.replace(/^(fwd|re):\s*/i, "").trim();
    var judul = cleanSubject;
    var penulis = "";
    
    var matchPenulis = cleanSubject.match(/(.*?)(?:\s*-\s*|\s+)Penulis:\s*(.*)/i);
    if (matchPenulis) {
      judul = matchPenulis[1].trim();
      penulis = matchPenulis[2].trim();
    } else {
      var lastDashIndex = cleanSubject.lastIndexOf("-");
      if (lastDashIndex !== -1) {
        judul = cleanSubject.substring(0, lastDashIndex).trim();
        penulis = cleanSubject.substring(lastDashIndex + 1).trim();
      } else {
        var bodyPenulisMatch = body.match(/Penulis:\s*([^\n\r]+)/i);
        if (bodyPenulisMatch) {
          penulis = bodyPenulisMatch[1].trim();
        } else {
          var bodyMatch = body.match(/Naik\s+cetak\s+([^\-\n\r]+)(?:\s*-\s*([^\n\r]+))?/i);
          if (bodyMatch) {
            judul = bodyMatch[1] ? bodyMatch[1].trim() : judul;
            penulis = bodyMatch[2] ? bodyMatch[2].trim() : penulis;
          }
        }
      }
    }
    penulis = penulis.replace(/^Penulis:\s*/i, "").trim();
    
    // D. PARSING JUMLAH CETAK
    var jumlahCetak = "";
    var qtyMatch = body.match(/(\d[\d\.,]*)\s*(?:eks|ex|eksemplar)\b/i);
    if (qtyMatch) {
      var cleanQty = qtyMatch[1].replace(/[^\d]/g, '');
      jumlahCetak = parseInt(cleanQty, 10);
    }
    
    // E. PARSING UKURAN, KERTAS, COVER
    var ukuran = matchDropdownValue(body, LIST_UKURAN, "UNESCO");
    var kertas = matchDropdownValue(body, LIST_KERTAS, "HVS 70");
    
    var cover = "SOFT";
    if (/\b(hard\s*cover|hard|hc)\b/i.test(body)) {
      cover = "HARD";
    } else if (/\b(soft\s*cover|soft|sc)\b/i.test(body)) {
      cover = "SOFT";
    } else if (/staples/i.test(body)) {
      cover = "STAPLES";
    } else if (/dilipat/i.test(body)) {
      cover = "DILIPAT";
    }
    
    // F. PARSING ISI BW/FC
    var isiBwFc = "HITAM PUTIH";
    if (/warna\s*sebagian/i.test(body)) {
      isiBwFc = "WARNA SEBAGIAN";
    } else if (/full\s*(colour|color|warna)/i.test(body) || /\bwarna\b/i.test(body)) {
      isiBwFc = "FULL WARNA";
    }
    
    // G. PARSING PJ CETAK, MARKETING (KOLOM P), & CATATAN EXTRA
    var textToSearch = (cleanSubject + "\n" + body).replace(/iqbatul/gi, "IQBAL");
    var normalizedText = textToSearch.replace(/\//g, " - ");
    
    var pjCetak = "";
    var marketing = "";
    var catatanJudul = "";
    
    var segments = normalizedText.split("-");
    var pjIndex = -1;
    
    for (var s = 0; s < segments.length; s++) {
      var segText = segments[s].trim();
      var foundPJ = matchStrictFromList(segText, LIST_PJ);
      if (foundPJ !== "") {
        pjCetak = foundPJ;
        pjIndex = s;
        break;
      }
    }
    
    if (pjIndex !== -1 && pjIndex + 1 < segments.length) {
      var nextSegText = segments[pjIndex + 1].trim();
      var foundMkt = matchStrictFromList(nextSegText, LIST_MARKETING);
      if (foundMkt !== "") {
        marketing = foundMkt;
        if (pjIndex + 2 < segments.length) {
          var remaining = segments.slice(pjIndex + 2).join("-").trim();
          if (remaining !== "") catatanJudul = remaining;
        }
      } else {
        var remainingNoMkt = segments.slice(pjIndex + 1).join("-").trim();
        if (remainingNoMkt !== "") catatanJudul = remainingNoMkt;
      }
    } else if (pjIndex === -1) {
      pjCetak = matchStrictFromList(textToSearch, LIST_PJ);
    }
    
    // H. BACA LAMPIRAN PDF TERBARU (PEMERIKSAAN GANDA: LAMPIRAN EMAIL & LINK GOOGLE DRIVE)
    var jumlahHalaman = "";
    var foundLatestPdf = false;
    var catatanDrive = "";
    
    for (var m = messages.length - 1; m >= 0; m--) {
      var msg = messages[m];
      var msgBodyFull = msg.getBody() + "\n" + msg.getPlainBody();
      var attachments = msg.getAttachments();
      
      // H1. PROSES LAMPIRAN FISIK EMAIL
      var pdfAttachments = [];
      for (var a = 0; a < attachments.length; a++) {
        if (attachments[a].getName().toLowerCase().indexOf(".pdf") !== -1) {
          pdfAttachments.push(attachments[a]);
        }
      }
      
      if (pdfAttachments.length === 1) {
        var singlePdf = pdfAttachments[0];
        var pageCountSingle = getPdfPageCount(singlePdf.copyBlob());
        if (pageCountSingle) {
          jumlahHalaman = pageCountSingle;
          foundLatestPdf = true;
        }
      } else if (pdfAttachments.length > 1) {
        for (var k = pdfAttachments.length - 1; k >= 0; k--) {
          var pdfAtt = pdfAttachments[k];
          var fileName = pdfAtt.getName().toLowerCase();
          var isExcluded = /(cover|print\s*bl|\bbl\b|combine|gabungan)/i.test(fileName);
          
          if (!isExcluded) {
            var pageCountMulti = getPdfPageCount(pdfAtt.copyBlob());
            if (pageCountMulti) {
              jumlahHalaman = pageCountMulti;
              foundLatestPdf = true;
              break;
            }
          }
        }
      }

      // H2. PROSES LINK GOOGLE DRIVE (JIKA TIDAK ADA / GAGAL DARI LAMPIRAN FISIK)
      if (!foundLatestPdf) {
        var driveFileIds = extractDriveFileIds(msgBodyFull);
        var validDrivePdfs = [];

        for (var d = 0; d < driveFileIds.length; d++) {
          try {
            var driveFile = DriveApp.getFileById(driveFileIds[d]);
            if (driveFile.getMimeType() === MimeType.PDF) {
              validDrivePdfs.push(driveFile);
            }
          } catch (err) {
            Logger.log("Gagal Akses Drive ID (" + driveFileIds[d] + "): " + err.message);
            catatanDrive = "Link GDrive Terkunci / Butuh Akses";
          }
        }

        if (validDrivePdfs.length === 1) {
          var singleDrivePdf = validDrivePdfs[0];
          var pageCountDriveSingle = getPdfPageCount(singleDrivePdf.getBlob());
          if (pageCountDriveSingle) {
            jumlahHalaman = pageCountDriveSingle;
            foundLatestPdf = true;
          }
        } else if (validDrivePdfs.length > 1) {
          for (var dk = validDrivePdfs.length - 1; dk >= 0; dk--) {
            var driveAtt = validDrivePdfs[dk];
            var driveFileName = driveAtt.getName().toLowerCase();
            var isDriveExcluded = /(cover|print\s*bl|\bbl\b|combine|gabungan)/i.test(driveFileName);

            if (!isDriveExcluded) {
              var pageCountDriveMulti = getPdfPageCount(driveAtt.getBlob());
              if (pageCountDriveMulti) {
                jumlahHalaman = pageCountDriveMulti;
                foundLatestPdf = true;
                break;
              }
            }
          }
        }
      }
      
      if (foundLatestPdf) {
        break;
      }
    }
    
    var totalHlmCetak = "";
    if (jumlahHalaman !== "" && jumlahCetak !== "") {
      totalHlmCetak = jumlahHalaman * jumlahCetak;
    }
    
    var rawTanggalMasuk = latestMessage.getDate();
    var tanggalMasukFormatted = Utilities.formatDate(rawTanggalMasuk, timeZone, "dd/MM/yyyy HH:mm");

    // I. CARI BARIS KOSONG PERTAMA BERDASARKAN KOLOM C
    var targetRow = getNextRowInColumnC(sheet);
    var noUrut = targetRow - 1; // Nomor Urut Otomatis (Kolom B)

    // J. SUSUN DATA DARI KOLOM B SAMPAI P
    var rowData = [
      noUrut,                // Kolom B (NO)
      tanggalMasukFormatted, // Kolom C (TANGGAL MASUK)
      jenisCetak,            // Kolom D
      judul,                 // Kolom E
      penulis,               // Kolom F
      jumlahHalaman,         // Kolom G
      totalHlmCetak,         // Kolom H
      ukuran,                // Kolom I
      cover,                 // Kolom J
      kertas,                // Kolom K
      isiBwFc,               // Kolom L
      jumlahCetak,           // Kolom M
      client,                // Kolom N
      pjCetak,               // Kolom O
      marketing              // Kolom P
    ];

    // TULISKAN DATA MULAI KOLOM B (Kolom 2) SAMPAI KOLOM P
    sheet.getRange(targetRow, 2, 1, rowData.length).setValues([rowData]);

    // K. BERI BORDER DARI KOLOM B SAMPAI P
    sheet.getRange(targetRow, 2, 1, rowData.length).setBorder(true, true, true, true, true, true);

    // L. SISIPKAN CATATAN DAN FORMAT URGENT
    var cellJudul = sheet.getRange(targetRow, 5); // Kolom E (JUDUL)
    var listCatatan = [];
    
    if (tglCetakSebelumnya !== "") {
      listCatatan.push("Cetak Terakhir: " + tglCetakSebelumnya);
    }

    var hasAttachmentsInLatest = latestMessage.getAttachments().length > 0;
    var hasNewKeywords = /\b(file\s*baru|pakai\s*file\s*ini|revisi)\b/i.test(body);
    
    if (hasNewKeywords || hasAttachmentsInLatest) {
      listCatatan.push("Pakai File Baru, Cek Lampiran Email!");
    }

    if (catatanDrive !== "") {
      listCatatan.push(catatanDrive);
    }
    
    if (catatanJudul !== "") {
      listCatatan.push(catatanJudul);
    }
    
    if (listCatatan.length > 0) {
      cellJudul.setNote(listCatatan.join("\n"));
    }
    
    var isUrgent = /\burgent\b/i.test(rawSubject) || /\burgent\b/i.test(body);
    if (isUrgent) {
      cellJudul.setBackground("#8B0000").setFontColor("#FFFFFF");
    } else {
      cellJudul.setBackground(null).setFontColor("#000000");
    }
    
    // M. TANDAI EMAIL SEBAGAI SUDAH DIBACA
    thread.markRead();
  }
}

// =================================================================
// FUNGSI PENDUKUNG: ANALISIS HALAMAN & KALKULATOR PROFIT (KONDISIONAL)
// =================================================================

/**
 * Membuat tabel HTML Analisis Halaman yang menyembunyikan kolom secara otomatis
 * - Hlm BW disembunyikan jika kosong/0
 * - Hlm Warna disembunyikan jika kosong/0
 * - Efisiensi Oplos disembunyikan jika bukan cetak campuran (BW & Warna)
 */
function buatAnalisisHalaman(hlmBW, hlmWarna) {
  var numBW = parseInt(hlmBW, 10);
  var numWarna = parseInt(hlmWarna, 10);
  
  var hasBW = !isNaN(numBW) && numBW > 0;
  var hasWarna = !isNaN(numWarna) && numWarna > 0;
  var isCampuran = hasBW && hasWarna; // Hanya aktif jika ada BW DAN Warna

  // Jika keduanya kosong, kembalikan teks kosong
  if (!hasBW && !hasWarna) return "";

  var html = '<h3>📊 Analisis Halaman & Kalkulator Selisih Profit</h3>';
  html += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; text-align: center;">';
  
  // 1. HEADER TABEL DINAMIS
  html += '<tr style="background-color: #f2f2f2;">';
  if (hasBW) html += '<th>Total Halaman BW</th>';
  if (hasWarna) html += '<th>Total Halaman Warna</th>';
  if (isCampuran) html += '<th>Efisiensi Oplos</th>';
  html += '</tr>';

  // 2. BARIS DATA DINAMIS
  html += '<tr>';
  if (hasBW) html += '<td>' + numBW + ' Halaman</td>';
  if (hasWarna) html += '<td>' + numWarna + ' Halaman</td>';
  
  if (isCampuran) {
    var totalHalaman = numBW + numWarna;
    var persentaseWarna = ((numWarna / totalHalaman) * 100).toFixed(1);
    html += '<td>' + persentaseWarna + '% Warna</td>';
  }
  
  html += '</tr>';
  html += '</table>';

  return html;
}

// =================================================================
// FUNGSI PENDUKUNG OTOMASI & PDF PARSER
// =================================================================

/**
 * EKSTRAKSI ID FILE GOOGLE DRIVE DARI ISI PESAN EMAIL
 */
function extractDriveFileIds(text) {
  var fileIds = [];
  var regex = /(?:https?:\/\/)?(?:drive|docs)\.google\.com\/(?:file\/d\/|open\?id=|uc\?id=)?([a-zA-Z0-9_-]{25,})/g;
  var match;

  while ((match = regex.exec(text)) !== null) {
    var id = match[1];
    if (fileIds.indexOf(id) === -1) {
      fileIds.push(id);
    }
  }
  return fileIds;
}

/**
 * PRECISION MULTI-LAYER PDF PARSER
 */
function getPdfPageCount(blob) {
  try {
    var str = blob.getDataAsString('ISO-8859-1');
    
    // LEVEL 1: LINEARIZED PDF HEADER (/N <jumlah_halaman>)
    var linMatch = str.match(/\/Linearized\b[^\/]{0,500}?\/N\s+(\d+)/i);
    if (linMatch && linMatch[1]) {
      var linCount = parseInt(linMatch[1], 10);
      if (linCount > 0) return linCount;
    }

    // LEVEL 2: METADATA XML ADOBE XMP
    var xmpMatch = str.match(/xmpTPg:NPages\s*=\s*"(\d+)"/i) || 
                   str.match(/<xmpTPg:NPages>(\d+)<\/xmpTPg:NPages>/i) ||
                   str.match(/pdf:NumPages\s*=\s*"(\d+)"/i) ||
                   str.match(/<pdf:NumPages>(\d+)<\/pdf:NumPages>/i);
    if (xmpMatch && xmpMatch[1]) {
      var xmpCount = parseInt(xmpMatch[1], 10);
      if (xmpCount > 0) return xmpCount;
    }
    
    // LEVEL 3: STRICT ROOT CATALOG (/Type /Pages /Count N)
    var strictPagesMatch = str.match(/\/Type\s*\/Pages\b[\s\S]{0,500}?\/Count\s+(\d+)/gi);
    if (strictPagesMatch) {
      var maxPages = 0;
      for (var c = 0; c < strictPagesMatch.length; c++) {
        var m = strictPagesMatch[c].match(/\/Count\s+(\d+)/i);
        if (m && m[1]) {
          var p = parseInt(m[1], 10);
          if (p > maxPages) maxPages = p;
        }
      }
      if (maxPages > 0) return maxPages;
    }
    
    // LEVEL 4: FALLBACK REVERSE /Count DENGAN /Type /Pages
    var reverseMatch = str.match(/\/Count\s+(\d+)[\s\S]{0,500}?\/Type\s*\/Pages\b/gi);
    if (reverseMatch) {
      var maxRev = 0;
      for (var r = 0; r < reverseMatch.length; r++) {
        var rm = reverseMatch[r].match(/\/Count\s+(\d+)/i);
        if (rm && rm[1]) {
          var valRev = parseInt(rm[1], 10);
          if (valRev > maxRev) maxRev = valRev;
        }
      }
      if (maxRev > 0) return maxRev;
    }

    // LEVEL 5: FALLBACK HITUNG /Type /Page
    var pageMatches = str.match(/\/Type\s*\/Page\b/g);
    if (pageMatches && pageMatches.length > 0) {
      return pageMatches.length;
    }
    
  } catch (e) {
    Logger.log("Gagal membaca halaman PDF: " + e.toString());
  }
  return "";
}

function getNextRowInColumnC(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 1) return 2;
  
  var colCValues = sheet.getRange("C1:C" + lastRow).getValues();
  for (var i = colCValues.length - 1; i >= 0; i--) {
    if (colCValues[i][0] !== "" && colCValues[i][0] !== null) {
      return i + 2;
    }
  }
  return 2;
}

function matchStrictFromList(text, list) {
  for (var i = 0; i < list.length; i++) {
    var reg = new RegExp("\\b" + list[i].replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&') + "\\b", 'i');
    if (reg.test(text)) {
      return list[i];
    }
  }
  return "";
}

function matchDropdownValue(text, list, defaultValue) {
  for (var i = 0; i < list.length; i++) {
    var reg = new RegExp(list[i].replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'), 'i');
    if (reg.test(text)) {
      return list[i];
    }
  }
  return defaultValue;
}

function getOrCreateMonthlySheet(ss, sheetName) {
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    var headers = [
      "", "NO", "TANGGAL MASUK", "JENIS CETAK", "JUDUL", "NAMA PENULIS", 
      "JUMLAH HALAMAN", "TOTAL HLM CETAK", "UKURAN", "COVER", 
      "KERTAS", "ISI BW/FC", "JUMLAH CETAK", "CLIENT", 
      "PJ CETAK", "MARKETING"
    ];
    sheet.appendRow(headers);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#d9ead3");
    sheet.setFrozenRows(1);
  }
  return sheet;
}
