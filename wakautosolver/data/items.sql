
PRAGMA page_size=4096;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS ah_finite_exclusions;
CREATE TABLE ah_finite_exclusions (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS archmonster_items;
CREATE TABLE archmonster_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS blueprints;
CREATE TABLE blueprints (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS horde_items;
CREATE TABLE horde_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS item_names;
CREATE TABLE item_names (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    en TEXT,
    fr TEXT,
    pt TEXT,
    es TEXT,
    PRIMARY KEY(item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS item_type_names;
CREATE TABLE item_type_names (
    item_type INTEGER NOT NULL REFERENCES item_types(item_type),
    t_en TEXT,
    t_fr TEXT,
    t_pt TEXT,
    t_es TEXT,
    PRIMARY KEY(item_type)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS item_types;
CREATE TABLE item_types (
    item_type INTEGER NOT NULL PRIMARY KEY,
    position TEXT,
    disables_offhand INTEGER DEFAULT FALSE
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS items;
CREATE TABLE items (
    item_id INTEGER PRIMARY KEY NOT NULL,
    item_lv INTEGER NOT NULL,
    item_rarity INTEGER NOT NULL,
    item_type INTEGER NOT NULL,
    hp INTEGER NOT NULL DEFAULT 0,
    ap INTEGER DEFAULT 0,
    mp INTEGER DEFAULT 0,
    wp INTEGER DEFAULT 0,
    ra INTEGER DEFAULT 0,
    control INTEGER DEFAULT 0,
    block INTEGER DEFAULT 0,
    critical_hit INTEGER DEFAULT 0,
    dodge INTEGER DEFAULT 0,
    lock INTEGER DEFAULT 0,
    force_of_will INTEGER DEFAULT 0,
    rear_mastery INTEGER DEFAULT 0,
    healing_mastery INTEGER DEFAULT 0,
    melee_mastery INTEGER DEFAULT 0,
    distance_mastery INTEGER DEFAULT 0,
    berserk_mastery INTEGER DEFAULT 0,
    critical_mastery INTEGER DEFAULT 0,
    fire_mastery INTEGER DEFAULT 0,
    earth_mastery INTEGER DEFAULT 0,
    water_mastery INTEGER DEFAULT 0,
    air_mastery INTEGER DEFAULT 0,
    mastery_1_element INTEGER DEFAULT 0,
    mastery_2_elements INTEGER DEFAULT 0,
    mastery_3_elements INTEGER DEFAULT 0,
    elemental_mastery INTEGER DEFAULT 0,
    resistance_1_element INTEGER DEFAULT 0,
    resistance_2_elements INTEGER DEFAULT 0,
    resistance_3_elements INTEGER DEFAULT 0,
    fire_resistance INTEGER DEFAULT 0,
    earth_resistance INTEGER DEFAULT 0,
    water_resistance INTEGER DEFAULT 0,
    air_resistance INTEGER DEFAULT 0,
    elemental_resistance INTEGER DEFAULT 0,
    rear_resistance INTEGER DEFAULT 0,
    critical_resistance INTEGER DEFAULT 0,
    armor_given INTEGER DEFAULT 0,
    armor_received INTEGER DEFAULT 0
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS legacy_items;
CREATE TABLE legacy_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS pvp_items;
CREATE TABLE pvp_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS recipes;
CREATE TABLE recipes (
    item_id INTEGER PRIMARY KEY NOT NULL,
    is_upgrade INTEGER NOT NULL DEFAULT FALSE,
    upgrade_of INTEGER NOT NULL DEFAULT 0
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS ub_items;
CREATE TABLE ub_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

DROP TABLE IF EXISTS unobtainable_items;
CREATE TABLE unobtainable_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

COMMIT TRANSACTION;
