--
-- File generated with SQLiteStudio v3.1.1 on sexta mar 10 16:22:34 2017
--
-- Text encoding used: UTF-8
--
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;

-- Table: clients
DROP TABLE IF EXISTS clients;

CREATE TABLE clients (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK,
  controller                 REFERENCES controllers (id)
                             NOT NULL,
  ipv4                       REFERENCES clients_ipv4s (id),
  ipv6                       REFERENCES clients_ipv6s (id),
  name                       REFERENCES names (id),
  registration_date DATETIME DEFAULT (CAST (strftime('%s', 'now') AS INTEGER) ),
  CONSTRAINT client_unique_id UNIQUE (
    id ASC,
    controller COLLATE BINARY ASC
  )
  ON CONFLICT ROLLBACK
)
WITHOUT ROWID;


-- Table: clients_ipv4s
DROP TABLE IF EXISTS clients_ipv4s;

CREATE TABLE clients_ipv4s (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
  address           INTEGER  NOT NULL
                             CONSTRAINT ipv4_address UNIQUE ON CONFLICT ROLLBACK,
  registration_date DATETIME DEFAULT (CAST (strftime('%s', 'now') AS INTEGER) )
);



-- Table: clients_ipv6s
DROP TABLE IF EXISTS clients_ipv6s;

CREATE TABLE clients_ipv6s (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
  address           BLOB     NOT NULL
                             COLLATE 'BINARY'
                             CONSTRAINT ipv6_address UNIQUE ON CONFLICT ROLLBACK,
  registration_date DATETIME DEFAULT (CAST (strftime('%s', 'now') AS INTEGER) )
);



-- Table: configurations
DROP TABLE IF EXISTS configurations;

CREATE TABLE configurations (
  creation_date    DATETIME DEFAULT (CAST (strftime('%s', 'now') AS 'INTEGER') ),
  ipv4_network     TEXT,
  ipv6_network     TEXT,
  ipv4_service     REFERENCES clients_ipv4s (id),
  ipv6_service     REFERENCES clients_ipv6s (id),
  mac_service      TEXT NOT NULL
);




-- Table: controllers
DROP TABLE IF EXISTS controllers;

CREATE TABLE controllers (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
  name                       REFERENCES names (id)
                             UNIQUE
                             NOT NULL,
  ipv4                       REFERENCES controllers_ipv4s (id),
  ipv6                       REFERENCES controllers_ipv6s (id),
  uuid              BLOB     CONSTRAINT unique_uuid UNIQUE ON CONFLICT ROLLBACK
                             NOT NULL,
  registration_date DATETIME DEFAULT ( (CAST (strftime('%s', 'now') AS 'INTEGER') ) ),
  CONSTRAINT ipv4_ipv6_both_null CHECK (NOT ( (controllers.ipv4 IS NULL) AND
                                              (controllers.ipv6 IS NULL) ) )
);


-- Table: controllers_ipv4s
DROP TABLE IF EXISTS controllers_ipv4s;

CREATE TABLE controllers_ipv4s (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
  address           INTEGER  NOT NULL,
  port              INTEGER  NOT NULL,
  registration_date DATETIME NOT NULL
                             DEFAULT (CAST (strftime('%s', 'now') AS 'INTEGER') ),
  CONSTRAINT ipv4_info_unique UNIQUE (
    address ASC,
    port ASC
  )
  ON CONFLICT ROLLBACK
);


-- Table: controllers_ipv6s
DROP TABLE IF EXISTS controllers_ipv6s;

CREATE TABLE controllers_ipv6s (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
  address           BLOB     NOT NULL,
  port              INTEGER  NOT NULL,
  registration_date DATETIME NOT NULL
                             DEFAULT (CAST (strftime('%s', 'now') AS 'INTEGER') ),
  CONSTRAINT ipv6_info_unique UNIQUE (
    address ASC,
    port ASC
  )
  ON CONFLICT ROLLBACK
);


-- Table: names
DROP TABLE IF EXISTS names;

CREATE TABLE names (
  id                INTEGER  PRIMARY KEY ASC ON CONFLICT ROLLBACK AUTOINCREMENT,
  name              TEXT     CONSTRAINT unique_name UNIQUE ON CONFLICT ROLLBACK
                             CONSTRAINT name_not_null NOT NULL,
  registration_date DATETIME DEFAULT (CAST (strftime('%s', 'now') AS 'INTEGER') )
                             NOT NULL
);


-- Trigger: delete_client
DROP TRIGGER IF EXISTS delete_client;
CREATE TRIGGER delete_client
        BEFORE DELETE
            ON clients
      FOR EACH ROW
BEGIN
  DELETE FROM clients_ipv4s
        WHERE clients_ipv4s.id == old.ipv4;
  DELETE FROM clients_ipv6s
        WHERE clients_ipv6s.id == old.ipv6;
  DELETE FROM names
        WHERE names.id == old.name;
END;


-- Trigger: delete_controllers
DROP TRIGGER IF EXISTS delete_controllers;
CREATE TRIGGER delete_controllers
        BEFORE DELETE
            ON controllers
      FOR EACH ROW
BEGIN
  DELETE FROM clients
        WHERE clients.controller == old.id;
  DELETE FROM controllers_ipv4s
        WHERE controllers_ipv4s.id == old.ipv4;
  DELETE FROM controllers_ipv6s
        WHERE controllers_ipv6s.id == old.ipv6;
  DELETE FROM names
        WHERE names.id == old.name;
END;



-- Trigger: table_row_limit
DROP TRIGGER IF EXISTS table_row_limit;
CREATE TRIGGER table_row_limit
        BEFORE DELETE
            ON configurations
      FOR EACH ROW
BEGIN
  SELECT creation_date,
         CASE WHEN count(creation_date) != 0 THEN RAISE(ABORT, "There can be only one row in configuration table.") END;
END;


CREATE TRIGGER configurations_update
  BEFORE UPDATE OF creation_date, ipv4_network, ipv6_network  ON configurations FOR EACH ROW
BEGIN
  SELECT RAISE (ABORT, 'Updates for table configurations are Forbidden.');
END;


-- View: controllers_view
DROP VIEW IF EXISTS controllers_view;
CREATE VIEW controllers_view AS
  SELECT controllers.uuid AS uuid,
         controllers_ipv4s.address AS ipv4,
         controllers_ipv4s.port AS ipv4_port,
         controllers_ipv6s.address AS ipv6,
         controllers_ipv6s.port AS ipv6_port,
         controllers_ipv6s.registration_date AS registration_date,
         names.name
    FROM controllers
         LEFT JOIN
         controllers_ipv4s ON controllers_ipv4s.id == controllers.ipv4
         LEFT JOIN
         controllers_ipv6s ON controllers_ipv6s.id == controllers.ipv6
         LEFT JOIN
         names ON names.id == controllers.name;


COMMIT TRANSACTION;
PRAGMA foreign_keys = on;


-- View: clients_view
DROP VIEW IF EXISTS clients_view;
CREATE VIEW clients_view AS
  SELECT clients.id AS id,
         clients_ipv4s.address AS ipv4,
         clients_ipv6s.address AS ipv6,
         names.name AS name,
         controllers.uuid AS controller,
         clients.registration_date AS registration_date
    FROM clients
         LEFT JOIN
         controllers ON controllers.id == clients.controller
         LEFT JOIN
         clients_ipv4s ON clients_ipv4s.id == clients.ipv4
         LEFT JOIN
         clients_ipv6s ON clients_ipv6s.id == clients.ipv6
         LEFT JOIN
         names ON names.id == clients.name;
