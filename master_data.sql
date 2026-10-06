CREATE TABLE IF NOT EXISTS master_kelompok (
    kode_kelompok TEXT PRIMARY KEY CHECK (btrim(kode_kelompok) <> ''),
    nama_kelompok TEXT NOT NULL CHECK (btrim(nama_kelompok) <> '')
);

CREATE TABLE IF NOT EXISTS master_jenis (
    kode_kelompok TEXT NOT NULL CHECK (btrim(kode_kelompok) <> ''),
    kode_jenis TEXT NOT NULL CHECK (btrim(kode_jenis) <> ''),
    nama_jenis TEXT NOT NULL CHECK (btrim(nama_jenis) <> ''),
    PRIMARY KEY (kode_kelompok, kode_jenis),
    FOREIGN KEY (kode_kelompok)
        REFERENCES master_kelompok (kode_kelompok)
);

CREATE TABLE IF NOT EXISTS master_objek (
    kode_kelompok TEXT NOT NULL CHECK (btrim(kode_kelompok) <> ''),
    kode_jenis TEXT NOT NULL CHECK (btrim(kode_jenis) <> ''),
    kode_objek TEXT NOT NULL CHECK (btrim(kode_objek) <> ''),
    nama_objek TEXT NOT NULL CHECK (btrim(nama_objek) <> ''),
    PRIMARY KEY (kode_kelompok, kode_jenis, kode_objek),
    FOREIGN KEY (kode_kelompok, kode_jenis)
        REFERENCES master_jenis (kode_kelompok, kode_jenis)
);

CREATE TABLE IF NOT EXISTS master_rincian_objek (
    kode_kelompok TEXT NOT NULL CHECK (btrim(kode_kelompok) <> ''),
    kode_jenis TEXT NOT NULL CHECK (btrim(kode_jenis) <> ''),
    kode_objek TEXT NOT NULL CHECK (btrim(kode_objek) <> ''),
    kode_rincian_objek TEXT NOT NULL
        CHECK (btrim(kode_rincian_objek) <> ''),
    nama_rincian_objek TEXT NOT NULL
        CHECK (btrim(nama_rincian_objek) <> ''),
    PRIMARY KEY (
        kode_kelompok,
        kode_jenis,
        kode_objek,
        kode_rincian_objek
    ),
    FOREIGN KEY (kode_kelompok, kode_jenis, kode_objek)
        REFERENCES master_objek (kode_kelompok, kode_jenis, kode_objek)
);

CREATE TABLE IF NOT EXISTS master_sub_rincian_objek (
    kode_kelompok TEXT NOT NULL CHECK (btrim(kode_kelompok) <> ''),
    kode_jenis TEXT NOT NULL CHECK (btrim(kode_jenis) <> ''),
    kode_objek TEXT NOT NULL CHECK (btrim(kode_objek) <> ''),
    kode_rincian_objek TEXT NOT NULL
        CHECK (btrim(kode_rincian_objek) <> ''),
    kode_sub_rincian_objek TEXT NOT NULL
        CHECK (btrim(kode_sub_rincian_objek) <> ''),
    nama_sub_rincian_objek TEXT NOT NULL
        CHECK (btrim(nama_sub_rincian_objek) <> ''),
    PRIMARY KEY (
        kode_kelompok,
        kode_jenis,
        kode_objek,
        kode_rincian_objek,
        kode_sub_rincian_objek
    ),
    FOREIGN KEY (
        kode_kelompok,
        kode_jenis,
        kode_objek,
        kode_rincian_objek
    ) REFERENCES master_rincian_objek (
        kode_kelompok,
        kode_jenis,
        kode_objek,
        kode_rincian_objek
    )
);
