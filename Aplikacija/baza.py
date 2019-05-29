#import auth

# odkomentiraj, če želiš poganjati z uporabniškim imenom javnost
import auth_public as auth

auth.db = "sem2019_anamario"
# auth.db = "sem2019_%s" % auth.user

# uvozimo psycopg2
import psycopg2, psycopg2.extensions, psycopg2.extras
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki
import csv
conn = psycopg2.connect(database=auth.db, host=auth.host, user=auth.user, password=auth.password)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 

def ustvari_tabelo_oddelki():
    cur.execute("""
        CREATE TABLE oddelki (
        id INTEGER PRIMARY KEY,
        oddelek TEXT NOT NULL
        );
    """)
    conn.commit()

def ustvari_tabelo_projekt():
    cur.execute("""
        CREATE TABLE projekt (
        id INTEGER PRIMARY KEY,
        ime TEXT NOT NULL,
        status TEXT NOT NULL,
        datum_zacetka DATE NOT NULL,
        datum_konca DATE NOT NULL,
        budget FLOAT
        );
    """)
    conn.commit()

def ustvari_tabelo_zaposleni():
    cur.execute("""
        CREATE TABLE zaposleni (
        emso TEXT PRIMARY KEY,
        ime TEXT NOT NULL,
        priimek TEXT NOT NULL,
        datum_rojstva DATE NOT NULL,
        delovna_doba INTEGER NOT NULL,
        kraj TEXT NOT NULL,
        stopnja_izobrazbe INTEGER NOT NULL,
        v_oddelku INTEGER NOT NULL REFERENCES oddelki (id)
            ON DELETE CASCADE 
            ON UPDATE CASCADE,
        na_projektu INTEGER REFERENCES projekt (id)
            ON DELETE CASCADE 
            ON UPDATE CASCADE
        );
    """)
    conn.commit()

def ustvari_tabelo_uporabnik():
    cur.execute("""
        CREATE TABLE uporabnik (
        uporabnisko_ime TEXT PRIMARY KEY,
        geslo TEXT NOT NULL,
        ime TEXT NOT NULL
        );
    """)
    conn.commit()


def ustvari_tabelo_sporocila():
    cur.execute("""
        CREATE TABLE sporocila (
        id INTEGER,
        cas TIMESTAMP DEFAULT now(),
        sporocilo TEXT, 
        posiljatelj TEXT NOT NULL REFERENCES uporabnik (uporabnisko_ime),
        prejemnik TEXT NOT NULL REFERENCES uporabnik (uporabnisko_ime),
        PRIMARY KEY (posiljatelj, prejemnik, id)
        );
    """)
    conn.commit()

def ustvari_tabelo_komentarji():
    cur.execute("""
        CREATE TABLE komentarji (
        id INTEGER PRIMARY KEY,
        cas TIMESTAMP DEFAULT now(),
        komentar TEXT,
        projekt INTEGER NOT NULL REFERENCES projekt (id),
        avtor TEXT REFERENCES uporabnik (uporabnisko_ime)
        );
    """)
    conn.commit()



def pobrisi_tabelo_oddelki():
    cur.execute("""
        DROP TABLE oddelki;
    """)
    conn.commit()

def pobrisi_tabelo_projekt():
    cur.execute("""
        DROP TABLE projekt;
    """)
    conn.commit()

def pobrisi_tabelo_zaposleni():
    cur.execute("""
        DROP TABLE zaposleni;
    """)
    conn.commit()

def pobrisi_tabelo_uporabnik():
    cur.execute("""
        DROP TABLE uporabnik;
    """)
    conn.commit()

def pobrisi_tabelo_sporocila():
    cur.execute("""
        DROP TABLE sporocila;
    """)
    conn.commit()

def pobrisi_tabelo_komentarji():
    cur.execute("""
        DROP TABLE komentarji;
    """)
    conn.commit()

'''
def test():
    cur.execute("select * from zaposleni")
    print(cur.fetchall())

test()
'''

