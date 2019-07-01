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

# def password_hash(s):
#     """Vrni SHA-512 hash danega UTF-8 niza. Gesla vedno spravimo v bazo
#        kodirana s to funkcijo."""
#     h = hashlib.sha512()
#     h.update(s.encode('utf-8'))
#     return h.hexdigest()

# Funkcija, ki v cookie spravi sporocilo
#ce jih ne bi bilo, streznik ne bi vedel, kaj je v prejsnje ze naredil
def set_sporocilo(tip, vsebina):
    response.set_cookie('message', (tip, vsebina), path='/', secret=secret)

# Funkcija, ki iz cookija dobi sporočilo, če je
def get_sporocilo():
    sporocilo = request.get_cookie('message', default=None, secret=secret)
    response.delete_cookie('message')
    return sporocilo

# To smo dobili na http://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
# in predelali v slovenščino. Da se še izboljšati, da bo pravilno delovala dvojina itd.
def pretty_date(time):
    """
    Predelaj čas (v formatu Unix epoch) v opis časa, na primer
    'pred 4 minutami', 'včeraj', 'pred 3 tedni' ipd.
    """

    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time 
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "zdaj"
        if second_diff < 60:
            return "pred " + str(second_diff) + " sekundami"
        if second_diff < 120:
            return  "pred minutko"
        if second_diff < 3600:
            return "pred " + str( second_diff // 60 ) + " minutami"
        if second_diff < 7200:
            return "pred eno uro"
        if second_diff < 86400:
            return "pred " + str( second_diff // 3600 ) + " urami"
    if day_diff == 1:
        return "včeraj"
    if day_diff < 7:
        return "pred " + str(day_diff) + " dnevi"
    if day_diff < 31:
        return "pred " + str(day_diff//7) + " tedni"
    if day_diff < 365:
        return "pred " + str(day_diff//30) + " meseci"
    return "pred " + str(day_diff//365) + " leti"

def get_user(auto_login = True):
    """Poglej cookie in ugotovi, kdo je prijavljeni uporabnik,
       vrni njegov username in ime. Če ni prijavljen, presumeri
       na stran za prijavo ali vrni None (advisno od auto_login).
    """
    # Dobimo username iz piškotka
    username = request.get_cookie('username', secret=secret)
    # Preverimo, ali ta uporabnik obstaja
    if username is not None:
        c = baza.cursor()
        c.execute("SELECT username, ime FROM uporabnik WHERE username=%s",
                  [username])
        r = c.fetchone()
        c.close ()
        if r is not None:
            # uporabnik obstaja, vrnemo njegove podatke
            return r
    # Če pridemo do sem, uporabnik ni prijavljen, naredimo redirect
    if auto_login:
        redirect('/login/')
    else:
        return None




######################################################################
# Funkcije, ki obdelajo zahteve odjemalcev.

@bottle.route("/static/<filename:path>")
def static(filename):
    """Splošna funkcija, ki servira vse statične datoteke iz naslova
       /static/..."""
    return static_file(filename, root='static')

@bottle.route("/")
def index():
    """Glavna stran."""
    # Iz cookieja dobimo uporabnika (ali ga preusmerimo na login, če
    # nima cookija)
    (username, ime) = get_user()
    # Morebitno sporočilo za uporabnika
    sporocilo = get_sporocilo()
    # Seznam zadnjih 10 tračev
    # ts = projekti()
    # Vrnemo predlogo za glavno stran
    return bottle.template("index.html",
                           ime=ime,
                           username=username,
                        #    projekti=ts,
                           sporocilo=sporocilo)

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
    c.execute("SELECT 1 FROM uporabnik WHERE username=%s", [username])
    if c.fetchone():
        # Uporabnik že obstaja
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               emso=emso,
                               napaka='To uporabniško ime je že zavzeto')
    elif not password1 == password2:
        # Geslo se ne ujemata
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               emso=emso,
                               napaka='Gesli se ne ujemata')
    else:
        # Vse je v redu, vstavi novega uporabnika v bazo
        password = password_md5(password1)
        c.execute("INSERT INTO uporabnik (username, ime, password, emso) VALUES (%s, %s, %s, %s)",
                  (username, ime, password, emso))
        # Daj uporabniku cookie
        bottle.response.set_cookie('username', username, path='/', secret=secret)
        bottle.redirect("/")


def zaposleni(imes, priimek, delovna_doba, stopnja_izobrazbe, oddelek):
    c = baza.cursor()
    c.execute(
        ''' SELECT ime, priimek, delovna_doba, stopnja_izobrazbe, oddelek
        FROM zaposleni JOIN oddelki ON zaposleni.v_oddelku = oddelki.id 
        WHERE (ime, priimek, delovna_doba, stopnja_izobrazbe, oddelek) 
        = (%s, %s, %s, %s, %s) ''', [imes, priimek, delovna_doba, stopnja_izobrazbe, oddelek])
    sodelavci = tuple(c)
    return sodelavci

@bottle.get("/zaposleni/")
def zaposleni_get():
    """Serviraj formo za zaposlene."""
    (username, ime) = get_user()
    return bottle.template("zaposleni.html",
                            username=username,
                            ime=ime,
                            sodelavec=None,
                            imes=None,
                            priimek=None,
                            delovna_doba=None,
                            stopnja_izobrazbe=None,
                            oddelek=None)

@bottle.post("/zaposleni/")
def zaposleni_post():
    """Poišči sodelavca."""
    (username, ime) = get_user()
    imes = bottle.request.forms.imes
    priimek = bottle.request.forms.priimek
    delovna_doba = bottle.request.forms.delovna_doba
    stopnja_izobrazbe = bottle.request.forms.stopnja_izobrazbe
    oddelek = bottle.request.forms.oddelek
    sodelavci = zaposleni(imes, priimek, delovna_doba, stopnja_izobrazbe, oddelek)
    return bottle.template("sodelavci.html",
                            username=username,
                            ime=ime,
                            sodelavci=sodelavci)
    

@bottle.get("/sodelavci/")
def sodelavci_get():
    "Vsi sodelavci"
    (username, ime) = get_user()
    return bottle.template("sodelavci.html",
                            username=username,
                            ime=ime)

@bottle.get('/user/')
def user():
    (username, ime) = get_user()
    c = baza.cursor()
    c.execute('''SELECT zaposleni.ime, priimek, datum_rojstva, delovna_doba, kraj, stopnja_izobrazbe FROM zaposleni JOIN uporabnik ON 
    uporabnik.emso=zaposleni.emso WHERE username=%s ''', [username])
    podatki = tuple(c)
    return template('user.html', username=username, ime=ime, podatki=podatki)

@bottle.get('/izziv/')
def user():
    (username, ime) = get_user()
    return template('izziv.html', username=username, ime=ime)

############################################################################################################################
@bottle.route("/user/<username>/")
def user_wall(username, sporocila=[]):
    """Prikaži stran uporabnika"""
    # Kdo je prijavljeni uporabnik? (Ni nujno isti kot username.)
    (username_login, ime_login) = get_user()
    # Ime uporabnika (hkrati preverimo, ali uporabnik sploh obstaja)
    c = baza.cursor()
    c.execute("SELECT ime FROM uporabnik WHERE username=%s", [username])
    (ime,) = c.fetchone()
    # # Koliko tracev je napisal ta uporabnik?
    # c.execute("SELECT COUNT(*) FROM trac WHERE avtor=%s", [username])
    # (t,) = c.fetchone()
    # # Koliko komentarjev je napisal ta uporabnik?
    # c.execute("SELECT COUNT(*) FROM komentar WHERE avtor=%s", [username])
    # (k,) = c.fetchone()
    # Prikažemo predlogo
    return bottle.template("user.html",
                           uporabnik_ime=ime,
                           uporabnik=username,
                           username=username_login,
                           ime=ime_login,
                        #    trac_count=t,
                        #    komentar_count=k,
                           sporocila=sporocila)
    
@bottle.post("/user/<username>/")
def user_change(username):
    """Obdelaj formo za spreminjanje podatkov o uporabniku."""
    # Kdo je prijavljen?
    (username, ime) = get_user()
    # Novo ime
    ime_new = bottle.request.forms.ime
    # Staro geslo (je obvezno)
    password1 = password_md5(bottle.request.forms.password1)
    # Preverimo staro geslo
    c = baza.cursor()
    c.execute ("SELECT 1 FROM uporabnik WHERE username=%s AND password=%s",
               [username, password1])
    # Pokazali bomo eno ali več sporočil, ki jih naberemo v seznam
    sporocila = []
    if c.fetchone():
        # Geslo je ok
        # Ali je treba spremeniti ime?
        if ime_new != ime:
            c.execute("UPDATE uporabnik SET ime=%s WHERE username=%s", [ime_new, username])
            sporocila.append(("alert-success", "Spreminili ste si ime."))
        # Ali je treba spremeniti geslo?
        password2 = bottle.request.forms.password2
        password3 = bottle.request.forms.password3
        if password2 or password3:
            # Preverimo, ali se gesli ujemata
            if password2 == password3:
                # Vstavimo v bazo novo geslo
                password2 = password_md5(password2)
                c.execute ("UPDATE uporabnik SET password=? WHERE username = ?", [password2, username])
                sporocila.append(("alert-success", "Spremenili ste geslo."))
            else:
                sporocila.append(("alert-danger", "Gesli se ne ujemata"))
    else:
        # Geslo ni ok
        sporocila.append(("alert-danger", "Napačno staro geslo"))
    c.close ()
    # Prikažemo stran z uporabnikom, z danimi sporočili. Kot vidimo,
    # lahko kar pokličemo funkcijo, ki servira tako stran
    return user_wall(username, sporocila=sporocila)


# def projekti(limit=10):
#     """Vrni dano število projektov (privzeto 10). Rezultat je seznam, katerega
#        elementi so oblike [id, ime, status, datum_zacetka, datum_konca, budget, porabljeno, narejeno, vsebina],
#        pri čemer so komentarji seznam elementov oblike [id, cas, vsebina, projekt, avtor],
#        urejeni po času objave.
#     """
#     c = baza.cursor()
#     c.execute(
#     """SELECT id, ime, status, datum_zacetka, datum_konca, budget, porabljeno, narejeno, vsebina, ime, priimek
#        FROM projekt JOIN zaposleni ON projekt.id = zaposleni.na_projektu
#        ORDER BY datum_konca desc
#        LIMIT %s
#     """, [limit])
#     # Rezultat predelamo v nabor.
#     projekti = tuple(c)
#     # Nabor id-jev projektov, ki jih bomo vrnili
#     tids = (projekt[0] for projekt in projekti)
#     # Logično bi bilo, da bi zdaj za vsak projekt naredili en SELECT za
#     # komentarje tega projekta. Vendar je drago delati veliko število
#     # SELECTOV, zato se raje potrudimo in napišemo en sam SELECT.
#     c.execute(
#     """SELECT projekt.id, username, projekt.ime, komentar.vsebina
#        FROM
#          (komentar JOIN projekt ON komentar.projekt = projekt.id)
#           JOIN uporabnik ON uporabnik.username = komentar.avtor
#        WHERE 
#          projekt.id IN (SELECT id FROM projekt ORDER BY cas DESC LIMIT %s)
#        ORDER BY
#          komentar.cas""", [limit])
#     # Rezultat poizvedbe ima nerodno obliko, pretvorimo ga v slovar,
#     # ki id trača preslika v seznam pripadajočih komentarjev.
#     # Najprej pripravimo slovar, ki vse id-je tračev slika v prazne sezname.
#     komentar = { tid : [] for tid in tids }
#     # Sedaj prenesemo rezultate poizvedbe v slovar
#     for (tid, username, ime, vsebina) in c:
#         komentar[tid].append((username, ime, vsebina))
#     c.close()
#     # Vrnemo nabor, kot je opisano v dokumentaciji funkcije:
#     return ((tid, u, i, pretty_date(c), v, komentar[tid])
#             for (tid, u, i, c, v) in projekti)

   
# @get('/index/')
# def index():
#     cur.execute("SELECT * FROM zaposleni")
#     return template('zaposleni.html', zaposleni=cur)



######################################################################
# Glavni program

# priklopimo se na bazo
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE) # se znebimo problemov s šumniki
baza = psycopg2.connect(database=auth.db, host=auth.host, user=auth.user, password=auth.password)
baza.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT) # onemogočimo transakcije
cur = baza.cursor(cursor_factory=psycopg2.extras.DictCursor) 
# poženemo strežnik na portu 8080, glej http://localhost:8080/
run(host='localhost', port=8080)

