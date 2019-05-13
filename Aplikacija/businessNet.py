#!/usr/bin/env python3

import sqlite3
import bottle
import hashlib # računanje kriptografski hash za gesla
from datetime import datetime

######################################################################
# Konfiguracija

# Vklopi debug, da se bodo predloge same osvežile in da bomo dobivali
# lepa sporočila o napakah.
bottle.debug(True)

# Datoteka, v kateri je baza
baza_datoteka = "bussinesNet.sqlite"

# Mapa s statičnimi datotekami
static_dir = "./static"

# Skrivnost za kodiranje cookijev
secret = "to skrivnost je zelo tezko uganiti 1094107c907cw982982c42"


######################################################################
# Pomožne funkcije

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
    username = bottle.request.get_cookie('uporabnisko_ime', secret=secret)
    # Preverimo, ali ta uporabnik obstaja
    if uporabnisko_ime is not None:
        c = baza.cursor()
        c.execute("SELECT uporabnisko_ime, ime FROM uporabnik WHERE uporabnisko_ime=?",
                  [uporabnisko_ime])
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

def projekt(limit=10):
    """Vrni dano število projektov (privzeto 10). Rezultat je seznam, katerega
       elementi so oblike [(+manager tega projketa), ime, status, datum_zacetka, datum_konca, budget, komentarji],
       pri čemer so komentarji seznam elementov oblike [id, ime_avtorja, vsebina], 
       urejeni po času objave.
    """
    c = baza.cursor()
    c.execute(
    """SELECT ime, status, datum_zacetka, datum_konca, budget, komentarji
       FROM projekt JOIN uporabnik ON .avtor = uporabnik.username
       ORDER BY cas DESC
       LIMIT ?
    """, [limit])
    # Rezultat predelamo v nabor.
    traci = tuple(c)
    # Nabor id-jev tračev, ki jih bomo vrnili
    tids = (trac[0] for trac in traci)
    # Logično bi bilo, da bi zdaj za vsak trač naredili en SELECT za
    # komentarje tega trača. Vendar je drago delati veliko število
    # SELECTOV, zato se raje potrudimo in napišemo en sam SELECT.
    c.execute(
    """SELECT trac.id, username, ime, komentar.vsebina
       FROM
         (komentar JOIN trac ON komentar.trac = trac.id)
          JOIN uporabnik ON uporabnik.username = komentar.avtor
       WHERE 
         trac.id IN (SELECT id FROM trac ORDER BY cas DESC LIMIT ?)
       ORDER BY
         komentar.cas""", [limit])
    # Rezultat poizvedbe ima nerodno obliko, pretvorimo ga v slovar,
    # ki id trača preslika v seznam pripadajočih komentarjev.
    # Najprej pripravimo slovar, ki vse id-je tračev slika v prazne sezname.
    komentar = { tid : [] for tid in tids }
    # Sedaj prenesemo rezultate poizvedbe v slovar
    for (tid, username, ime, vsebina) in c:
        komentar[tid].append((username, ime, vsebina))
    c.close()
    # Vrnemo nabor, kot je opisano v dokumentaciji funkcije:
    return ((tid, u, i, pretty_date(c), v, komentar[tid])
            for (tid, u, i, c, v) in traci)

######################################################################
# Funkcije, ki obdelajo zahteve odjemalcev.

@bottle.route("/static/<filename:path>") #dekorator:popravlja funkcijo. ce pride get request na streznik, se klice ta 
#funkcija in vrne rezultat
def static(filename):
    """Splošna funkcija, ki servira vse statične datoteke iz naslova
       /static/..."""
return bottle.static_file(filename, root=static_dir)

@bottle.route("/")
def main():
    """Glavna stran."""
    # Iz cookieja dobimo uporabnika (ali ga preusmerimo na login, če
    # nima cookija)
    (username, ime) = get_user()
    # Morebitno sporočilo za uporabnika
    sporocilo = get_sporocilo()
    # Seznam zadnjih 10 tračev
    ts = traci()
    # Vrnemo predlogo za glavno stran
    return bottle.template("main.html",
                           ime=ime,
                           username=username,
                           traci=ts,
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
    # Izračunamo hash gesla, ki ga bomo spravili
    password = password_hash(bottle.request.forms.password)
    # Preverimo, ali se je uporabnik pravilno prijavil
    c = baza.cursor()
    c.execute("SELECT 1 FROM uporabnik WHERE username=? AND password=?",
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
                           napaka=None)

@bottle.post("/register/")
def register_post():
    """Registriraj novega uporabnika."""
    username = bottle.request.forms.username
    ime = bottle.request.forms.ime
    password1 = bottle.request.forms.password1
    password2 = bottle.request.forms.password2
    # Ali uporabnik že obstaja?
    c = baza.cursor()
    c.execute("SELECT 1 FROM uporabnik WHERE username=?", [username])
    if c.fetchone():
        # Uporabnik že obstaja
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               napaka='To uporabniško ime je že zavzeto')
    elif not password1 == password2:
        # Geslo se ne ujemata
        return bottle.template("register.html",
                               username=username,
                               ime=ime,
                               napaka='Gesli se ne ujemata')
    else:
        # Vse je v redu, vstavi novega uporabnika v bazo
        password = password_hash(password1)
        c.execute("INSERT INTO uporabnik (username, ime, password) VALUES (?, ?, ?)",
                  (username, ime, password))
        # Daj uporabniku cookie
        bottle.response.set_cookie('username', username, path='/', secret=secret)
        bottle.redirect("/")

@bottle.post("/trac/new/")
def new_trac():
    """Ustvari nov trač."""
    # Kdo je avtor trača?
    (username, ime) = get_user()
    # Vsebina trača
    trac = bottle.request.forms.trac
    c = baza.cursor()
    c.execute("INSERT INTO trac (avtor, vsebina) VALUES (?,?)",
              [username, trac])
    # Presumerimo na glavno stran
    return bottle.redirect("/")

@bottle.route("/user/<username>/")
def user_wall(username, sporocila=[]):
    """Prikaži stran uporabnika"""
    # Kdo je prijavljeni uporabnik? (Ni nujno isti kot username.)
    (username_login, ime_login) = get_user()
    # Ime uporabnika (hkrati preverimo, ali uporabnik sploh obstaja)
    c = baza.cursor()
    c.execute("SELECT ime FROM uporabnik WHERE username=?", [username])
    (ime,) = c.fetchone()
    # Koliko tracev je napisal ta uporabnik?
    c.execute("SELECT COUNT(*) FROM trac WHERE avtor=?", [username])
    (t,) = c.fetchone()
    # Koliko komentarjev je napisal ta uporabnik?
    c.execute("SELECT COUNT(*) FROM komentar WHERE avtor=?", [username])
    (k,) = c.fetchone()
    # Prikažemo predlogo
    return bottle.template("user.html",
                           uporabnik_ime=ime,
                           uporabnik=username,
                           username=username_login,
                           ime=ime_login,
                           trac_count=t,
                           komentar_count=k,
                           sporocila=sporocila)
    
@bottle.post("/user/<username>/")
def user_change(username):
    """Obdelaj formo za spreminjanje podatkov o uporabniku."""
    # Kdo je prijavljen?
    (username, ime) = get_user()
    # Novo ime
    ime_new = bottle.request.forms.ime
    # Staro geslo (je obvezno)
    password1 = password_hash(bottle.request.forms.password1)
    # Preverimo staro geslo
    c = baza.cursor()
    c.execute ("SELECT 1 FROM uporabnik WHERE username=? AND password=?",
               [username, password1])
    # Pokazali bomo eno ali več sporočil, ki jih naberemo v seznam
    sporocila = []
    if c.fetchone():
        # Geslo je ok
        # Ali je treba spremeniti ime?
        if ime_new != ime:
            c.execute("UPDATE uporabnik SET ime=? WHERE username=?", [ime_new, username])
            sporocila.append(("alert-success", "Spreminili ste si ime."))
        # Ali je treba spremeniti geslo?
        password2 = bottle.request.forms.password2
        password3 = bottle.request.forms.password3
        if password2 or password3:
            # Preverimo, ali se gesli ujemata
            if password2 == password3:
                # Vstavimo v bazo novo geslo
                password2 = password_hash(password2)
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

@bottle.post("/komentar/<tid:int>/")
def komentar(tid):
    """Vnesi nov komentar."""
    (username, ime) = get_user()
    komentar = bottle.request.forms.komentar
    baza.execute("INSERT INTO komentar (vsebina, trac, avtor) VALUES (?, ?, ?)",
                 [komentar, tid, username])
    bottle.redirect("/#trac-{0}".format(tid))

@bottle.route("/trac/<tid:int>/delete/")
def komentar_delete(tid):
    """Zbriši komentar."""
    (username, ime) = get_user()
    # DELETE napišemo tako, da deluje samo, če je avtor komentarja prijavljeni uporabnik
    r = baza.execute("DELETE FROM trac WHERE id=? AND avtor=?", [tid, username]).rowcount;
    if not r == 1:
        return "Vi ste hacker."
    else:
        set_sporocilo('alert-success', "Vaš komentar je IZBRISAN.")
        return bottle.redirect("/")



######################################################################
# Glavni program

# priklopimo se na bazo
baza = sqlite3.connect(baza_datoteka, isolation_level=None)

# poženemo strežnik na portu 8080, glej http://localhost:8080/
bottle.run(host='localhost', port=8080, reloader=True)
