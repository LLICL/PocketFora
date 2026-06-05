CREATE TABLE IF NOT EXISTS categorias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    icono       TEXT    DEFAULT '📁',
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS transacciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio        TEXT    NOT NULL,
    fecha           TEXT    NOT NULL,
    total           REAL    NOT NULL,
    moneda          TEXT    DEFAULT 'PEN',
    detalle         TEXT,
    tipo_documento  TEXT,
    serie_numero    TEXT,
    ruc             TEXT,
    categoria_id    INTEGER,
    qr_raw          TEXT,
    created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

CREATE TABLE IF NOT EXISTS productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaccion_id  INTEGER NOT NULL,
    descripcion     TEXT    NOT NULL,
    cantidad        REAL    DEFAULT 1,
    precio_unitario REAL    DEFAULT 0,
    subtotal        REAL    DEFAULT 0,
    FOREIGN KEY (transaccion_id) REFERENCES transacciones(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transacciones_fecha ON transacciones(fecha);
CREATE INDEX IF NOT EXISTS idx_transacciones_categoria ON transacciones(categoria_id);

INSERT OR IGNORE INTO categorias (nombre, icono) VALUES
    ('Alimentación',    '🍽️'),
    ('Transporte',      '🚌'),
    ('Salud',           '💊'),
    ('Educación',       '📚'),
    ('Vivienda',        '🏠'),
    ('Servicios',       '💡'),
    ('Entretenimiento', '🎮'),
    ('Ropa',            '👕'),
    ('Tecnología',      '💻'),
    ('Otros',           '📁');
