# Roadmap — website provisioning TUI

## Doel

Een Python 3-script maakt vanuit één interactieve terminalinterface een nieuwe
website aan op de Linux-server. De gebruiker ziet functionele stappen (site
aanmaken, HTTPS instellen, database kiezen en type website kiezen) en geen
technische details tenzij een fout optreedt.

De demonstratie moet deze scenario's ondersteunen:

1. Backup van `www.klant3.sil`.
2. Nieuwe statische HTTPS-site `www.secure<initialen>.sil`.
3. Nieuwe todo-site met database `www.todo<initialen>.sil`.
4. Nieuwe WordPress-site met database `www.wp<initialen>.sil`.

## TUI-keuze

**Textual** is de aanbevolen keuze. Het levert formulieren, schermen,
keuzelijsten, validatie, toetsenbordnavigatie en nette foutmeldingen zonder
zelf ANSI-escapecodes te moeten beheren. Het past daardoor beter bij een
meer-staps flow dan `questionary`.

Alternatieven:

- `curses` is standaard beschikbaar, maar vereist veel handmatige layout- en
  redraw-logica en is minder onderhoudbaar.
- `questionary` is klein en eenvoudig, maar vooral geschikt voor lineaire
  vragen; een overzicht, bevestigingsscherm en voortgangsscherm kosten extra
  werk.
- `urwid` is volwassen, maar heeft voor dit beperkte formulierproces meer
  framework-oppervlak dan nodig.

Textual is daarom de beste balans voor dit project. De afhankelijkheden staan
in `requirements.txt`; de Python-standaardbibliotheek blijft de voorkeur voor
alle overige taken.

## Fasen

### 1. Server en configuratie inventariseren

- Controleer Rocky/RHEL-versie, Python 3.12+, SELinux-status en actieve services.
- Noteer de echte paden voor BIND-zonefiles, Apache vhosts, document roots,
  logs, certificaten en MySQL.
- De standaard Apache-documentroot van deze app is `/var/www/html`; pas
  `PROVISIONER_DOCUMENT_ROOT` alleen aan als de serverconfiguratie afwijkt.
- Leg deze paden vast in één configuratiemodule of `.env`-bestand; hardcode geen
  wachtwoorden of server-specifieke paden in de UI.
- Controleer dat BIND, Apache/httpd, PHP-FPM, MySQL en OpenSSL geïnstalleerd
  en gestart zijn.
- Maak een testplan met een niet-productiedomein en een herstelprocedure.

### 2. Projectstructuur en TUI

Aanbevolen structuur:

```text
src/
  main.py
  config.py
  models.py
  ui/
    app.py
    screens.py
  services/
    validation.py
    backup.py
    bind.py
    apache.py
    certificates.py
    database.py
    templates.py
templates/
  static/
  todo/
  wordpress/
```

- Gebruik functies en dataclasses voor de invoer en provisioning-configuratie.
- Gebruik constanten voor `sil`, standaardpaden, record-TTL's en servicenames.
- Valideer domeinen met een strikte allowlist: letters, cijfers, `-` en `.`;
  accepteer zowel `test5` als `test5.sil`, normaliseer naar één vorm en
  voorkom path traversal.
- Toon vóór uitvoering een bevestiging met domein, HTTPS, database en
  websitetype.
- Voeg een voortgangsscherm toe met duidelijke Nederlandse stappen.

### 3. Bestaande site en backup

- Zoek de site op via de genormaliseerde domeinnaam en controleer zone,
  document root en database afzonderlijk.
- Als de site bestaat, maak een timestamped backup van zonefile,
  HTML/PHP-bestanden en SQL-dump. Backup geen vhost of `named.conf`.
- Gebruik `pathlib`, `shutil`, `tarfile` en een database-driver; gebruik geen
  `os.system`. De basisimplementatie maakt een `.tar.7z`: eerst een tar-archief,
  daarna compressie met `7zz` (of `7z` op systemen waar dat de executable-naam
  is).
- De databasebackup kan via de MySQL-driver als SQL-export worden opgebouwd.
  Als de serverpolicy `mysqldump` vereist, voer dat gecontroleerd uit met
  `subprocess.run(..., check=True, shell=False)`.
- Stop daarna bewust en toon een duidelijke Nederlandstalige melding. Log geen
  databasewachtwoorden.

### 4. Nieuwe DNS- en webconfiguratie

- Maak een zonefile op basis van een template, inclusief SOA, NS, A en
  eventuele `www`-records.
- Voeg geen dubbele zone toe aan `named.conf`; wijzig configuratie atomair en
  valideer met `named-checkconf` en `named-checkzone`.
- Maak document root en logfile met correcte eigenaar, groep en permissies.
- Schrijf een Apache vhost voor HTTP of HTTPS. Gebruik templates en
  placeholder-substitutie, geen ongecontroleerde stringconcatenatie.
- Herlaad services alleen na validatie met `systemctl reload`; gebruik
  `subprocess.run` met vaste argumenten en controleer de returncode.

### 5. HTTPS

- Vraag HTTPS pas na de domeinvalidatie.
- Maak voor de labo-opdracht een self-signed certificaat zoals in de eerdere
  klantopdracht, of gebruik de voorgeschreven CA indien die op de cursusserver
  aanwezig is.
- Bewaar private keys buiten de webroot met `0600`-permissies.
- Test certificaat, vhost en bereikbaarheid; documenteer dat self-signed
  certificaten een browserwaarschuwing geven.

### 6. Website-inhoud en database

- Zonder database: kopieer de statische template en maak de site klaar.
- Met database: genereer een unieke databasenaam, gebruiker en sterk
  willekeurig wachtwoord. Gebruik parameterized queries, nooit
  gebruikersinvoer in SQL.
- Todo-site: kopieer PHP/CSS-bestanden, vul de databaseconfiguratie in buiten
  versiebeheer en laad het meegeleverde schema/seed-SQL.
- WordPress: plaats de voorgeschreven WordPress-bestanden en maak alleen de
  database en configuratiebasis aan; laat de eerste webinstallatie gebeuren
  via de browser zoals gevraagd.
- Beperk bestandseigenaarschap en schrijfpermissies volgens de Apache/PHP-FPM
  setup op de server.

### 7. Validatie en controle

Voer na elke actie controles uit en toon de uitkomst in de TUI:

- `named-checkconf` en `named-checkzone`.
- Apache-configtest (`apachectl configtest`).
- DNS-resolutie en HTTP(S)-status met `curl`.
- Test lokaal met `dig @127.0.0.1 test5.sil A` en daarna met
  `nslookup test5.sil`; de tweede gebruikt de resolver uit `/etc/resolv.conf`.
- HTTPS-certificaat en redirectgedrag.
- Databaseconnectie met de aangemaakte gebruiker.
- Statische pagina, todo-flow en WordPress-bestanden.
- Herhaal de backup van `www.klant3.sil` en controleer de inhoud van het
  backup-archief.

Maak vóór de Toledo-indiening een korte demo-checklist en test exact de vier
scenario's. Dien de code uiterlijk **9 november 2026 om 20:00** in via Toledo
en plan de demonstratie in week 6 of tijdens het labo in week 7.

## Installatie op Rocky/RHEL 10

```bash
sudo dnf install -y python3 python3-pip bind bind-utils httpd openssl \
  mysql-server mysql 7zip php php-fpm php-mysqlnd
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

De Python-app moet met de nodige beperkte rootrechten of via een gecontroleerd
bevoegd helperproces draaien. Voeg geen wachtwoorden, certificaten,
zonefiles, backups of gegenereerde websites aan Git toe.

Zonefiles moeten op Rocky/RHEL leesbaar zijn voor de `named`-service. De app
zet nieuwe zonefiles daarom op `named:named`, modus `0640`, en herstelt de
SELinux-context met `restorecon`.

Voor de standaard systeemlocaties moet de app als root worden gestart, omdat
`/var/named`, `/etc/named.conf`, `/etc/httpd/conf.d` en de certificaatmappen
niet schrijfbaar zijn voor een gewone gebruiker:

```bash
sudo --preserve-env=PROVISIONER_SERVER_IP,PROVISIONER_NAMESERVER,PROVISIONER_NAMESERVER_IP \
  env PYTHONPATH="$PWD" "$PWD/.venv/bin/python" -m src.main
```

De app leest uitsluitend het project-`.env`-bestand. Vul dit bestand volledig
in op basis van `.env.example`; shell-variabelen worden niet gebruikt:

```bash
set -a
source .env
set +a
sudo --preserve-env=PROVISIONER_SERVER_IP,PROVISIONER_NAMESERVER,PROVISIONER_NAMESERVER_IP,PROVISIONER_DRY_RUN \
  env PYTHONPATH="$PWD" "$PWD/.venv/bin/python" -m src.main
```

De app controleert deze schrijfrechten vooraf en stopt met een duidelijke
melding vóór er bestanden worden aangemaakt. Voor lokale tests kan
`PROVISIONER_DRY_RUN=1` met tijdelijke mappen worden gebruikt.

De huidige basisapp kan eerst veilig getest worden met de paden uit een
tijdelijke map:

```bash
PROVISIONER_DRY_RUN=1 \
PROVISIONER_BACKUP_ROOT=/tmp/provisioner-backups \
PROVISIONER_ZONE_ROOT=/tmp/provisioner-zones \
PROVISIONER_DOCUMENT_ROOT=/tmp/provisioner-www \
PROVISIONER_VHOST_ROOT=/tmp/provisioner-vhosts \
PROVISIONER_CERTIFICATE_ROOT=/tmp/provisioner-certs \
PYTHONPATH=. .venv/bin/python -m src.main
```

Voor WordPress downloadt de provisioner de actuele officiële release van
`http://wordpress.org/latest.zip` naar tijdelijke opslag en verwijdert die
bestanden na de
cursus toegestane WordPress-distributie. Zonder die instelling maakt de app
bewust een duidelijke installatienotitie in plaats van bestanden van een
onbekende bron te downloaden.
