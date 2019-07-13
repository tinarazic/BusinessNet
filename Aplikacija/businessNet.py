#!/usr/bin/env python3

import sqlite3
import bottle
from bottle import *
import hashlib # računanje kriptografski hash za gesla
from datetime import datetime
import auth_public as auth 
import psycopg2, psycopg2.extensions, psycopg2.extras

bottle.TEMPLATE_PATH.insert(0,"./views")

######################################################################
# Konfiguracija

# Vklopi debug, da se bodo predloge same osvežile in da bomo dobivali
# lepa sporočila o napakah.
debug(True)

# Datoteka, v kateri je baza
baza_datoteka = "bussinesNet.sqlite"

# Mapa s statičnimi datotekami
static_dir = "./static"


# Skrivnost za kodiranje cookijev
secret = "to skrivnost je zelo tezko uganiti 1094107c907cw982982c42"



######################################################################
# Pomožne funkcije

def password_md5(s):
    """Vrni MD5 hash danega UTF-8 niza. Gesla vedno spravimo v bazo
       kodirana s to funkcijo."""
    h = hashlib.md5()
    h.update(s.encode('utf-8'))
    return h.hexdigest()

def password_hash(s):
    """Vrni SHA-512 hash danega UTF-8 niza. Gesla vedno spravimo v bazo
       kodirana s to funkcijo."""
    h = hashlib.sha512()
    h.update(s.encode('utf-8'))
    return h.hexdigest()

# Funkcija, ki v cookie spravi sporocilo
#ce jih ne bi bilo, streznik ne bi vedel, kaj je v prejsnje ze naredil
def set_sporocilo(tip, vsebina):
    bottle.response.set_cookie('message', (tip, vsebina), path='/', secret=secret)

# Funkcija, ki iz cookija dobi sporočilo, če je
def get_sporocilo():
    sporocilo = bottle.request.get_cookie('message', default=None, secret=secret)
    bottle.response.delete_cookie('message')
    return sporocilo

# To smo dobili na http://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
# in predelali v slovenščino. Da se še izboljšati, da bo pravilno delovala dvojina itd.

def get_user(auto_login = True):
    """Poglej cookie in ugotovi, kdo je prijavljeni uporabnik,
       vrni njegov username in ime. Če ni prijavljen, presumeri
       na stran za prijavo ali vrni None (advisno od auto_login).
    """
    # Dobimo username iz piškotka
    username = bottle.request.get_cookie('username', secret=secret)
    # Preverimo, ali ta uporabnik obstaja
    if username is not None:
        c = baza.cursor()
        c.execute("SELECT username, ime, emso FROM uporabnik WHERE username=%s",
                  [username])
        r = c.fetchone()
        c.close ()
        if r is not None:
            # uporabnik obstaja, vrnemo njegove podatke
            return r
    # Če pridemo do sem, uporabnik ni prijavljen, naredimo redirect
    if auto_login:
        bottle.redirect('/login/')
    else:
        return None




######################################################################
# Funkcije, ki obdelajo zahteve odjemalcev.

@bottle.route("/static/<filename:path>")
def static(filename):
    """Splošna funkcija, ki servira vse statične datoteke iz naslova
       /static/..."""
    return bottle.static_file(filename, root='static')

@bottle.route("/")
def index():
    """Glavna stran."""
    # Iz cookieja dobimo uporabnika (ali ga preusmerimo na login, če
    # nima cookija)
    (username, ime, emso) = get_user()
    # Morebitno sporočilo za uporabnika
    sporocila = get_sporocilo()
    # Seznam projektov userja
    ts = projekti_glavna()
    budget = denar()
    # Vrnemo predlogo za glavno stran
    return bottle.template("index.html",
                           ime=ime,
                           username=username,
                           projekti_glavna=ts,
                           denar=budget,
                           sporocila=None)


@bottle.get("/login/")
def login_get():
    """Serviraj formo za login."""
    return bottle.template("login.html",
                           napaka=None,
                           username=None)


@bottle.get("/logout/")
def logout():
    """Pobriši cookie in preusmeri na login."""
    bottle.response.delete_cookie('username')
    bottle.redirect('/login/')


@bottle.post("/login/")
def login_post():
    """Obdelaj izpolnjeno formo za prijavo"""
    # Uporabniško ime, ki ga je uporabnik vpisal v formo
    username = bottle.request.forms.username
    # Izračunamo MD5 has gesla, ki ga bomo spravili
    password = password_md5(bottle.request.forms.password)
    # Preverimo, ali se je uporabnik pravilno prijavil
    c = baza.cursor()
    c.execute("SELECT 1 FROM uporabnik WHERE username=%s AND password=%s",
              [username, password])
    if c.fetchone() is None:
        # Username in geslo se ne ujemata
        return bottle.template("login.html",
                               napaka="Nepravilna prijava",
                               username=username)
    else:
        # Vse je v redu, nastavimo cookie in preusmerimo na glavno stran
        bottle.response.set_cookie('username', username, path='/', secret=secret)
        bottle.redirect("/")


@bottle.get("/register/")
def login_get():
    """Prikaži formo za registracijo."""
    return bottle.template("register.html", 
                           username=None,
                           ime=None,
                           emso=None,
                           napaka=None)


@bottle.post("/register/")
def register_post():
    """Registriraj novega uporabnika."""
    username = bottle.request.forms.username
    ime = bottle.request.forms.ime
    emso = bottle.request.forms.emso
    password1 = bottle.request.forms.password1
    password2 = bottle.request.forms.password2
    # Ali uporabnik že obstaja?
    c = baza.cursor()
    c.execute("SELECT emso FROM zaposleni")
    emsi = []
    for e in tuple(c):
        emsi += e

    c.execute("SELECT 1 FROM uporabnik WHERE username=%s", [username])
    if c.fetchone():
        # Uporabnik že obstaja
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               emso=emso,
                               napaka='To uporabniško ime je že zavzeto.')

    elif not password1 == password2:
        # Geslo se ne ujemata
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               emso=emso,
                               napaka='Gesli se ne ujemata.')

    elif emso not in emsi:
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               emso=emso,
                               napaka='Emšo ni med prijavljenimi.')

    else:
        # Vse je v redu, vstavi novega uporabnika v bazo
        password = password_md5(password1)
        c.execute("INSERT INTO uporabnik (username, ime, password, emso) VALUES (%s, %s, %s, %s)",
                  (username, ime, password, emso))
        # Daj uporabniku cookie
        baza.commit()
        bottle.response.set_cookie('username', username, path='/', secret=secret)
        bottle.redirect("/")


def zaposleni(imes, priimek, oddelek):
    c = baza.cursor()
    c.execute(
        '''WITH C1 AS(
            SELECT *
            FROM zaposleni JOIN oddelki ON zaposleni.v_oddelku = oddelki.id
            )
            SELECT  c1.emso, c1.ime, priimek, datum_rojstva, delovna_doba, kraj, stopnja_izobrazbe, oddelek, username, uporabnik.ime FROM
            C1 LEFT JOIN uporabnik ON C1.emso = uporabnik.emso
            WHERE C1.ime LIKE %s
            and priimek LIKE %s
            and oddelek LIKE %s ''', (imes, priimek, oddelek))
    c.close()
    sodelavci = tuple(c)
    return sodelavci


@bottle.get("/zaposleni/")
def zaposleni_get():
    """Serviraj formo za zaposlene."""
    (username, ime, emso) = get_user()
    return bottle.template("zaposleni.html",
                            username=username,
                            ime=ime,
                            imes=None,
                            priimek=None,
                            oddelek=None)


@bottle.post("/zaposleni/")
def zaposleni_post():
    """Poišči sodelavca."""
    (username, ime, emso) = get_user()
    imes = bottle.request.forms.imes
    priimek = bottle.request.forms.priimek
    oddelek = bottle.request.forms.oddelek
    sodelavci = zaposleni(imes, priimek, oddelek)
    return bottle.template("sodelavci.html",
                            username=username,
                            ime=ime,
                            sodelavci=sodelavci)
    

@bottle.get("/sodelavci/")
def sodelavci_get():
    "Vsi sodelavci"
    (username, ime, emso) = get_user()
    return bottle.template("sodelavci.html",
                            username=username,
                            ime=ime)


@bottle.get('/user/')
def user_get():
    (username, ime, emso) = get_user()
    ts = projekti_glavna()
    c = baza.cursor()
    c.execute(
    '''WITH C1 AS(
            SELECT *
            FROM zaposleni JOIN oddelki ON zaposleni.v_oddelku = oddelki.id
            )
            SELECT  c1.emso, c1.ime, priimek, datum_rojstva, delovna_doba, kraj, stopnja_izobrazbe, oddelek, username, uporabnik.ime FROM
            C1 LEFT JOIN uporabnik ON C1.emso = uporabnik.emso
            WHERE username=%s ''', [username])    
    podatki = tuple(c)
    c.close()
    return bottle.template('user.html', username=username, ime=ime, podatki=podatki, projekti_glavna=ts)


@bottle.get('/izziv/')
def izziv_get():
    (username, ime, emso) = get_user()
    return bottle.template('izziv.html', username=username, ime=ime)


@bottle.get("/igra/")
def igra_get():
    (username, ime, emso) = get_user()
    return bottle.template("igra.html",
                            username=username,
                            ime=ime)


def projekti_glavna():
    c = baza.cursor()
    (username, ime, emso)= get_user()
    c.execute(
        '''WITH C1 AS (
           SELECT * FROM projekt JOIN delavci ON 
           projekt.id=delavci.projekt_id)
           SELECT * FROM C1 JOIN uporabnik ON   
           c1.emso=uporabnik.emso 
           WHERE username=%s
           ORDER BY narejeno ASC ''', [username])
    projekti_glavna = tuple(c)
    c.close()
    return projekti_glavna


def denar():
    c = baza.cursor()
    (username, ime, emso)= get_user()
    c.execute(
        '''SELECT SUM(BUDGET) as budget_total, SUM(PORABLJENO) as porabljeno_total
            FROM projekt''')
    denar = tuple(c)
    c.close()
    return denar


def komentarji(projekt_id):
    """Vrne komntarje pod danim projektom"""
    c = baza.cursor()
    c.execute(
    """SELECT DISTINCT cas, komentar.vsebina, komentar.avtor
        FROM komentar
        WHERE komentar.projekt_id = %s
        ORDER BY cas desc
        LIMIT 7""", [projekt_id])
    koment = tuple(c)
    c.close()
    return koment


def nov_projekt():
    """Doda nov projekt."""
    (username, ime, emso) = get_user()
    id_proo = bottle.request.forms.proo_id
    ime_proj = bottle.request.forms.ime_proj
    datum_zac = bottle.request.forms.datum_zac
    datum_kon = bottle.request.forms.dat_kon
    status = bottle.request.forms.status
    budget = bottle.request.forms.bud
    porabljeno = bottle.request.forms.por
    narejeno = bottle.request.forms.nar
    opis = bottle.request.forms.opis
    c = baza.cursor()
    c.execute("""INSERT INTO projekt (ime, datum_zacetka, datum_konca, status, budget, porabljeno, narejeno, vsebina)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
              [ime_proj, datum_zac, datum_kon, status, budget, porabljeno, narejeno, opis])
    max_id, = c.fetchone()
    c.execute("INSERT INTO delavci (projekt_id, emso) VALUES (%s, %s)",
              [max_id, emso])
    if username != 'direktor':
        c.execute("INSERT INTO delavci (projekt_id, emso) VALUES (%s, '19902208505124')",
                  [max_id])
    baza.commit()
    c.close()


@bottle.get("/projekti/")
def projekti_get():
     """Vrne projekte uporabnika in komentarje pod projekti
     """
     (username, ime, emso) = get_user()
     c = baza.cursor()
     c.execute("""SELECT username FROM uporabnik""")
     users = tuple(c)
     useerss = []
     for user in users:
         useerss += user
     c.execute(
     """SELECT DISTINCT projekt.id, projekt.ime, status, datum_zacetka, datum_konca, budget, porabljeno, narejeno, vsebina, delavci.emso
        FROM (projekt INNER JOIN delavci ON projekt.id = delavci.projekt_id)
        INNER JOIN uporabnik ON delavci.emso = uporabnik.emso
        WHERE username = %s
        ORDER BY datum_konca desc
     """, [username])
     projekti = tuple(c)
     kom = {}
     useers = {}
     for (i, ime, stat, zac, kon, b, por, nar, v, em) in projekti:
         c.execute("""SELECT username FROM uporabnik JOIN delavci ON uporabnik.emso=delavci.emso
                      WHERE projekt_id=%s""", [i])
         na_projektu = tuple(c)
         ze_na_projektu = []
         #usernami tistih, ki so že na projeku id=i
         for z in na_projektu:
             ze_na_projektu += z
         mozni = []
         for user in useerss:
            if user not in ze_na_projektu:
                mozni.append(user)
         useers[i] = mozni
         if komentarji(i):
             kom[i] = komentarji(i)
         else:
             kom[i] = ()
     statusi = ['aktiven', 'končan']
     c.close()
     return bottle.template("projekti.html", username=username, ime=ime, projekti=projekti, kom=kom, statusi=statusi, useers=useers)


@bottle.post("/projekti/")
def nov_komentar_projekt():
    """Doda nov komentar ali delavca k projektu ali doda nov projekt."""
    (username, ime, emso) = get_user()
    # Vsebina komentarja
    if bottle.request.forms.komm:
        komentar_1 = bottle.request.forms.komm
        pro_id = bottle.request.forms.proo_id
        c = baza.cursor()
        c.execute("INSERT INTO komentar (avtor, vsebina, projekt_id) VALUES (%s, %s, %s)",
                  [username, komentar_1, pro_id])
    elif bottle.request.forms.user:
        delavec = bottle.request.forms.user
        pro_id = bottle.request.forms.proo_id
        c = baza.cursor()
        c.execute("SELECT emso FROM uporabnik WHERE username=%s",
                  [delavec])
        dela = tuple(c)
        delavec_emso = []
        for d in dela:
            delavec_emso += d
        c.execute("INSERT INTO delavci (projekt_id, emso) VALUES (%s, %s)",
                  [pro_id, delavec_emso[0]])
    elif bottle.request.forms.naar:
        naar = bottle.request.forms.naar
        poor = bottle.request.forms.poor
        pro_id = bottle.request.forms.proo_id
        c = baza.cursor()
        c.execute("UPDATE projekt SET porabljeno=%s, narejeno=%s WHERE id=%s",
                  [poor, naar, pro_id])
    else:
        nov_projekt()
    baza.commit()
    c.close()
    return bottle.redirect("/projekti/")


@bottle.get("/sporocila/")
def sporocila_get():
     """Vrne sporočila uporabnika in možnosti za prejemnike novega sporočila
     """
     (username, ime, emso) = get_user()
     c = baza.cursor()
     c.execute(
     """SELECT DISTINCT cas, prejemnik, posiljatelj, sporocilo
        FROM sporocila
        WHERE (prejemnik = %s OR posiljatelj = %s)
        ORDER BY cas desc
        LIMIT 10""", [username, username])
     sporocila = tuple(c)
     c.close()
     pogovori = []
     for (cas, prejemnik, posiljatelj, sporocilo) in sporocila:
         if (prejemnik != username) and (prejemnik not in pogovori):
             pogovori.append(prejemnik)
         elif (posiljatelj != username) and (posiljatelj not in pogovori):
             pogovori.append(posiljatelj)
     c = baza.cursor()
     c.execute("""SELECT username FROM uporabnik""")
     users = tuple(c)
     useers = []
     for user in users:
         useers += user
     c.close()
     return bottle.template("sporocila.html", username=username, sporocila=sporocila, pogovori=pogovori, useers=useers)


@bottle.post("/sporocila/")
def sporocila_post():
    """Vnese novo sporočilo v bazo."""
    (username, ime, emso) = get_user()
    user = bottle.request.forms.user
    spor = bottle.request.forms.spor
    c = baza.cursor()
    c.execute("INSERT INTO sporocila (sporocilo, posiljatelj, prejemnik) VALUES (%s, %s, %s)",
              [spor, username, user])
    baza.commit()
    c.close()
    return bottle.redirect("/sporocila/")


@bottle.get("/spremeni-geslo/")
def user_wall():
    """Prikaži stran uporabnika"""
    (username_login, ime_login, emso_login) = get_user()
    return bottle.template("spremeni-geslo.html",
                           username=username_login,
                           napaka=None)

    
@bottle.post("/spremeni-geslo/")
def user_change():
    """Obdelaj formo za spreminjanje podatkov o uporabniku."""
    # Kdo je prijavljen?
    (username, ime, emso) = get_user()
    password1 = password_md5(bottle.request.forms.password1)
    # Preverimo staro geslo
    c = baza.cursor()
    c.execute("SELECT 1 FROM uporabnik WHERE username=%s AND password=%s AND emso=%s",
               [username, password1, emso])
    if c.fetchone():
        # Geslo je ok
        # Ali je treba spremeniti geslo?
        password2 = bottle.request.forms.password2
        password3 = bottle.request.forms.password3
        if password2 or password3:
            # Preverimo, ali se gesli ujemata
            if password2 == password3:
                # Vstavimo v bazo novo geslo
                password2 = password_md5(password2)
                c.execute("UPDATE uporabnik SET password=%s WHERE (username = %s AND emso= %s)", [password2, username, emso])
                baza.commit()
                return bottle.redirect("/")

            else:
                bottle.template("spremeni-geslo.html", username=username, napaka='Gesli se ne ujemata')
    else:
        # Geslo ni ok
        bottle.template("spremeni-geslo.html", username=username, napaka='Napačno staro geslo')

    c.close()


 
######################################################################
# Glavni program

# priklopimo se na bazo
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki
baza = psycopg2.connect(database=auth.db, host=auth.host, user=auth.user, password=auth.password)
#baza.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT) # onemogočimo transakcije
cur = baza.cursor(cursor_factory=psycopg2.extras.DictCursor) 
# poženemo strežnik na portu 8080, glej http://localhost:8080/
run(host='localhost', port=8080)

