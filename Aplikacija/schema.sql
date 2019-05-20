CREATE TABLE IF NOT EXISTS zaposleni (
 emso TEXT PRIMARY KEY,
 ime TEXT NOT NULL,
 priimek TEXT NOT NULL,
 datum_rojstva DATE NOT NULL,
 delovna_doba INTEGER NOT NULL,
 kraj TEXT NOT NULL,
 stopnja_izobrazbe INTEGER NOT NULL,
 v_oddelku TEXT NOT NULL REFERENCES oddelki (oddelek)
  	ON DELETE CASCADE 
	ON UPDATE CASCADE,
 na_projektu TEXT REFERENCES projekt (ime)
	ON DELETE CASCADE 
	ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS oddelki (
 id INTEGER PRIMARY KEY,
 oddelek TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projekt (
 id INTEGER PRIMARY KEY,
 ime TEXT NOT NULL,
 status TEXT NOT NULL,
 datum_zacetka DATE NOT NULL,
 datum_konca DATE NOT NULL,
 budget FLOAT
);

CREATE TABLE IF NOT EXISTS sporocila (
 id INTEGER,
 cas TIMESTAMP DEFAULT now(),
 sporocilo TEXT, 
 posiljatelj TEXT NOT NULL REFERENCES uporabnik (uporabnisko_ime),
 prejemnik TEXT NOT NULL REFERENCES uporabnik (uporabnisko_ime),
 PRIMARY KEY (posiljatelj, prejemnik, id)
);

CREATE TABLE IF NOT EXISTS komentarji (
 id INTEGER PRIMARY KEY,
 cas TIMESTAMP now(),
 komentar TEXT,
 projekt INTEGER id,
 avtor TEXT REFERENCES uporabnik (uporabnisko_ime)
);

CREATE TABLE IF NOT EXISTS uporabnik (
  uporabnisko_ime TEXT PRIMARY KEY,
  geslo TEXT NOT NULL,
  ime TEXT NOT NULL
);



/* Grant za javnost*/
GRANT CONNECT ON DATABASE sem2019_anamario TO javnost;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO javnost;
GRANT SELECT, UPDATE, INSERT ON ALL TABLES IN SCHEMA public TO javnost;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO javnost;

GRANT ALL ON DATABASE sem2019_anamario TO tinar;
GRANT ALL ON SCHEMA public TO tinar;
GRANT ALL ON ALL TABLES IN SCHEMA public TO tinar;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO tinar;

