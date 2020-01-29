-- TODO: allow arbitrary CRS
-- TODO: allow arbitrary column AND table names

-- basic network setup
-- alternatively use ogr2ogr

-- note that sqlite only recognises 5 basic column affinities (TEXT, NUMERIC, INTEGER, REAL, BLOB); more specific declarations are ignored
-- the 'INTEGER PRIMARY KEY' column is always 64-bit signed integer, AND an alias for 'ROWID'.

-- Note that manually editing the ogc_fid will corrupt the spatial index. Therefore, we leave the
-- ogc_fid alone, and have a separate link_id and node_id, for network editors who have specific
-- requirements.

-- it is recommended to use the listed edit widgets in QGIS;
#
CREATE TABLE 'links' (
  ogc_fid INTEGER PRIMARY KEY, -- Hidden widget
  link_id INTEGER UNIQUE NOT NULL, -- Text edit widget with 'Not null' constraint
  a_node INTEGER, -- Text edit widget, with 'editable' unchecked
  b_node INTEGER, -- Text edit widget, with 'editable' unchecked
  direction INTEGER, -- Range widget, 'Editable', min=0, max=2, step=1, default=0
  capacity_ab REAL,
  capacity_ba REAL,
  speed_ab REAL,
  speed_ba REAL,
  'length' REAL
);
#
SELECT AddGeometryColumn( 'links', 'geometry', '4326', 'LINESTRING', 'XY' );
#
SELECT CreateSpatialIndex( 'links' , 'geometry' );
#
CREATE INDEX links_a_node_idx ON links (a_node);
#
CREATE INDEX links_b_node_idx ON links (b_node);
#
-- it is recommended to use the listed edit widgets in QGIS
#
CREATE TABLE 'nodes' (
  ogc_fid INTEGER PRIMARY KEY, -- Hidden widget
  node_id INTEGER UNIQUE NOT NULL -- Text edit widget with 'Not null' constraint
);
#
SELECT AddGeometryColumn( 'nodes', 'geometry', DEFAULT_CRS, 'POINT', 'XY' );
#
SELECT CreateSpatialIndex( 'nodes' , 'geometry' );
#