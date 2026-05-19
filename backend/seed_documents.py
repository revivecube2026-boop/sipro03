"""Default document templates (Bahasa Indonesia formal). Seeded once on startup."""
import uuid
from datetime import datetime, timezone

from deps import db, logger


SPK_CONTENT = """# SURAT PEMESANAN UNIT (SPK)

Pada hari ini, {{today}}, kami yang bertanda tangan di bawah ini:

**Pembeli:**
Nama: **{{customer.name}}**
NIK: {{customer.nik}}
Alamat: {{customer.address}}, {{customer.city}}
Telepon: {{customer.phone}}

dengan ini menyatakan **memesan unit properti** dengan rincian sebagai berikut:

## RINCIAN UNIT

- Proyek: **{{project.name}}**
- Blok/Nomor: **{{unit.label}}**
- Tipe: {{unit.unit_type}}
- Luas Bangunan: {{unit.floor_area}} m²
- Luas Tanah: {{unit.land_area}} m²
- Harga Jual: **{{deal.price_idr}}** (_{{deal.price_words}}_)
- Metode Pembayaran: {{deal.payment_method}}

## KETENTUAN PEMESANAN

1. Pemesan setuju membayar **uang tanda jadi (booking fee)** sesuai ketentuan pengembang.
2. Pemesanan ini berlaku **paling lama 7 (tujuh) hari kalender** sejak ditandatangani. Apabila dalam jangka waktu tersebut pemesan tidak melanjutkan ke tahap PPJB, maka pemesanan akan dibatalkan dan booking fee dapat dipotong sesuai kebijakan pengembang.
3. Apabila pemesanan ini diteruskan ke PPJB, maka uang tanda jadi akan diperhitungkan sebagai bagian dari Down Payment (DP).
4. Spesifikasi unit, harga, dan ketentuan lain akan dituangkan secara lengkap dalam **Perjanjian Pengikatan Jual Beli (PPJB)** yang akan ditandatangani kemudian.

Demikian Surat Pemesanan ini dibuat dengan sebenar-benarnya untuk dipergunakan sebagaimana mestinya.
"""


PPJB_CONTENT = """# PERJANJIAN PENGIKATAN JUAL BELI

Pada hari ini, **{{today}}**, di **{{project.location}}**, kami yang bertanda tangan di bawah ini:

**I. PIHAK PERTAMA (Penjual):**
PT. {{project.name}} Developer
yang dalam hal ini diwakili oleh manajemen perusahaan, selanjutnya disebut sebagai **PIHAK PERTAMA**.

**II. PIHAK KEDUA (Pembeli):**
Nama: **{{customer.name}}**
NIK: {{customer.nik}}
NPWP: {{customer.npwp}}
Tempat/Tgl Lahir: {{customer.birthplace}}, {{customer.birthdate.date_id}}
Status: {{customer.marital_status}}
Pekerjaan: {{customer.occupation}}
Alamat: {{customer.address}}, {{customer.city}}, {{customer.province}}
Telepon: {{customer.phone}}

Nama Pasangan: {{customer.spouse_name}}
NIK Pasangan: {{customer.spouse_nik}}

selanjutnya disebut sebagai **PIHAK KEDUA**.

PIHAK PERTAMA dan PIHAK KEDUA selanjutnya secara bersama-sama disebut sebagai **PARA PIHAK**, dengan ini sepakat untuk mengikatkan diri dalam Perjanjian Pengikatan Jual Beli (PPJB) atas unit properti dengan ketentuan-ketentuan sebagai berikut:

## PASAL 1 - OBJEK PERJANJIAN

PIHAK PERTAMA dengan ini berjanji menjual, dan PIHAK KEDUA dengan ini berjanji membeli, sebuah unit properti berikut tanah dengan rincian:

- Proyek: **{{project.name}}**
- Lokasi: {{project.location}}
- Blok/Nomor Unit: **{{unit.label}}**
- Tipe Unit: {{unit.unit_type}}
- Luas Bangunan: {{unit.floor_area}} m²
- Luas Tanah: {{unit.land_area}} m²

## PASAL 2 - HARGA DAN CARA PEMBAYARAN

1. Harga jual unit disepakati sebesar **{{deal.price_idr}}** (_{{deal.price_words}}_).
2. Metode pembayaran: **{{deal.payment_method}}**.
3. Tata cara dan jadwal pembayaran diatur dalam **Lampiran Jadwal Pembayaran** yang merupakan bagian tidak terpisahkan dari Perjanjian ini.
4. Apabila PIHAK KEDUA terlambat melakukan pembayaran sesuai jadwal, akan dikenakan denda sesuai ketentuan pengembang.

## PASAL 3 - SERAH TERIMA

1. PIHAK PERTAMA berkewajiban menyerahkan unit kepada PIHAK KEDUA dalam kondisi siap huni sesuai spesifikasi.
2. Serah terima dilakukan setelah PIHAK KEDUA menyelesaikan seluruh kewajiban pembayaran.
3. Serah terima akan dituangkan dalam **Berita Acara Serah Terima (BAST)** yang ditandatangani PARA PIHAK.

## PASAL 4 - AKTA JUAL BELI

Setelah PIHAK KEDUA menyelesaikan seluruh kewajiban pembayaran dan dokumen-dokumen lengkap, PARA PIHAK akan melaksanakan **Akta Jual Beli (AJB)** di hadapan Pejabat Pembuat Akta Tanah (PPAT) yang ditunjuk.

## PASAL 5 - AHLI WARIS

Apabila PIHAK KEDUA berhalangan tetap, hak dan kewajiban dari Perjanjian ini beralih kepada ahli waris yang ditunjuk:
- Nama Ahli Waris: {{customer.heir_name}}
- Hubungan: {{customer.heir_relation}}
- Telepon: {{customer.heir_phone}}

## PASAL 6 - KETENTUAN LAIN

1. Hal-hal yang belum diatur dalam Perjanjian ini akan diatur kemudian secara musyawarah oleh PARA PIHAK.
2. Apabila terjadi perselisihan, PARA PIHAK sepakat untuk menyelesaikan secara musyawarah; apabila tidak tercapai, akan diselesaikan melalui Pengadilan Negeri yang berwenang.

Perjanjian ini dibuat dalam rangkap 2 (dua) bermaterai cukup, masing-masing pihak menerima 1 (satu) eksemplar yang mempunyai kekuatan hukum yang sama.
"""


AJB_CONTENT = """# AKTA JUAL BELI

Nomor: {{deal.id}}

Pada hari ini, **{{today}}**, di hadapan saya, _Pejabat Pembuat Akta Tanah (PPAT)_ yang nama, gelar, dan wilayah kerjanya disebutkan pada akhir akta ini, telah hadir:

**1. Penjual:**
PT. {{project.name}} Developer, berkedudukan di {{project.location}}, dalam hal ini diwakili oleh kuasa yang sah.

**2. Pembeli:**
Nama: **{{customer.name}}**
NIK: {{customer.nik}}
Alamat: {{customer.address}}, {{customer.city}}

Para penghadap yang saya, PPAT, kenal/diperkenalkan kepada saya, menerangkan bahwa:

## PASAL 1

PENJUAL dengan ini menjual dan menyerahkan kepada PEMBELI, dan PEMBELI dengan ini membeli dan menerima dari PENJUAL, sebuah unit berikut tanahnya dengan rincian:

- Proyek: **{{project.name}}**
- Blok/Nomor: **{{unit.label}}**
- Luas Tanah: {{unit.land_area}} m²
- Luas Bangunan: {{unit.floor_area}} m²

## PASAL 2 - HARGA

Jual beli ini dilakukan dengan harga sebesar **{{deal.price_idr}}** (_{{deal.price_words}}_) yang telah dibayar lunas oleh PEMBELI kepada PENJUAL sebelum penandatanganan Akta ini, dan Akta ini sekaligus berlaku sebagai kuitansi penerimaan.

## PASAL 3 - PENYERAHAN HAK

Sejak ditandatanganinya Akta ini, hak atas tanah dan bangunan tersebut beralih sepenuhnya dari PENJUAL kepada PEMBELI.

## PASAL 4 - PAJAK DAN BIAYA

1. Pajak Penghasilan (PPh) atas pengalihan menjadi tanggungan PENJUAL.
2. Bea Perolehan Hak atas Tanah dan Bangunan (BPHTB) menjadi tanggungan PEMBELI.
3. Biaya pembuatan Akta dan balik nama menjadi tanggungan PEMBELI.

Akta ini dibuat dalam rangkap 2 (dua) bermaterai cukup. Asli untuk arsip PPAT, salinan untuk PEMBELI.
"""


BAST_CONTENT = """# BERITA ACARA SERAH TERIMA UNIT

Pada hari ini, **{{today}}**, kami yang bertanda tangan di bawah ini:

**Pihak yang Menyerahkan:**
PT. {{project.name}} Developer
Selanjutnya disebut **PIHAK PERTAMA**.

**Pihak yang Menerima:**
Nama: **{{customer.name}}**
NIK: {{customer.nik}}
Alamat: {{customer.address}}, {{customer.city}}
Telepon: {{customer.phone}}
Selanjutnya disebut **PIHAK KEDUA**.

dengan ini menyatakan bahwa PIHAK PERTAMA telah **menyerahkan** dan PIHAK KEDUA telah **menerima** unit dengan rincian sebagai berikut:

## RINCIAN UNIT

- Proyek: **{{project.name}}**
- Blok/Nomor Unit: **{{unit.label}}**
- Tipe Unit: {{unit.unit_type}}
- Luas Bangunan: {{unit.floor_area}} m²
- Luas Tanah: {{unit.land_area}} m²
- Kondisi: **Siap huni**, sesuai spesifikasi PPJB

## KELENGKAPAN YANG DISERAHKAN

- Kunci utama unit
- Kunci pintu kamar & ruang
- Sertifikat garansi peralatan (jika ada)
- Buku panduan / dokumen teknis bangunan
- IMB / PBG (jika sudah terbit)

## CATATAN SERAH TERIMA

Apabila terdapat catatan atau temuan saat serah terima, akan dicantumkan dalam lampiran terpisah dan menjadi tanggung jawab perbaikan PIHAK PERTAMA sesuai masa garansi.

## PERNYATAAN

PIHAK KEDUA dengan ini menyatakan bahwa unit telah diterima dalam kondisi baik dan sesuai dengan spesifikasi yang telah disepakati dalam PPJB. Sejak penandatanganan Berita Acara ini, **risiko, biaya pemeliharaan, listrik, air, IPL, dan kewajiban lainnya** beralih sepenuhnya kepada PIHAK KEDUA.

Demikian Berita Acara Serah Terima ini dibuat dalam rangkap 2 (dua), masing-masing pihak menerima 1 (satu) eksemplar yang mempunyai kekuatan hukum yang sama.
"""


DEFAULT_TEMPLATES = [
    {
        "code": "SPK",
        "name": "Surat Pemesanan Unit (SPK)",
        "description": "Dokumen tanda jadi pemesanan unit, sebelum PPJB.",
        "content": SPK_CONTENT,
        "variables": ["customer.name", "customer.nik", "customer.address", "customer.city", "customer.phone",
                      "project.name", "unit.label", "unit.unit_type", "unit.floor_area", "unit.land_area",
                      "deal.price_idr", "deal.price_words", "deal.payment_method", "today"],
    },
    {
        "code": "PPJB",
        "name": "Perjanjian Pengikatan Jual Beli (PPJB)",
        "description": "Perjanjian utama jual beli unit sebelum AJB.",
        "content": PPJB_CONTENT,
        "variables": ["customer.name", "customer.nik", "customer.npwp", "customer.birthplace", "customer.birthdate.date_id",
                      "customer.marital_status", "customer.occupation", "customer.address", "customer.city", "customer.province",
                      "customer.phone", "customer.spouse_name", "customer.spouse_nik",
                      "customer.heir_name", "customer.heir_relation", "customer.heir_phone",
                      "project.name", "project.location", "unit.label", "unit.unit_type", "unit.floor_area", "unit.land_area",
                      "deal.price_idr", "deal.price_words", "deal.payment_method", "today"],
    },
    {
        "code": "AJB",
        "name": "Akta Jual Beli (AJB)",
        "description": "Akta resmi pengalihan hak — ditandatangani di hadapan PPAT.",
        "content": AJB_CONTENT,
        "variables": ["customer.name", "customer.nik", "customer.address", "customer.city",
                      "project.name", "project.location", "unit.label", "unit.land_area", "unit.floor_area",
                      "deal.id", "deal.price_idr", "deal.price_words", "today"],
    },
    {
        "code": "BAST",
        "name": "Berita Acara Serah Terima (BAST)",
        "description": "Berita acara serah terima unit ke pembeli.",
        "content": BAST_CONTENT,
        "variables": ["customer.name", "customer.nik", "customer.address", "customer.city", "customer.phone",
                      "project.name", "unit.label", "unit.unit_type", "unit.floor_area", "unit.land_area", "today"],
    },
]


async def seed_default_templates():
    for tpl in DEFAULT_TEMPLATES:
        existing = await db.document_templates.find_one({"code": tpl["code"]}, {"_id": 0, "id": 1})
        if existing:
            continue
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            **tpl,
            "is_active": True,
            "created_by": "system",
            "created_at": now,
            "updated_at": now,
        }
        await db.document_templates.insert_one(doc)
        logger.info(f"Seeded default document template: {tpl['code']}")
