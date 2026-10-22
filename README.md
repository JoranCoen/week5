# Website Provisioner

De app maakt BIND-zones, Apache-vhosts, self-signed HTTPS-certificaten, statische
websites, todo-websites en een WordPress-basis aan. MySQL wordt gebruikt voor
websites die een database nodig hebben.

> **Waarschuwing:** echte modus wijzigt `/var/named`, `/etc/named.conf`,
> `/var/www/html`, Apache-configuratie, certificaten en MySQL. Test eerst met
> `PROVISIONER_DRY_RUN=1`.

## 1. Repository clonen

```bash
sudo dnf install -y git
cd ~
git clone https://github.com/JoranCoen/week5.git week5
cd week5
```

Voor een bestaande clone:

```bash
cd ~/week5
git pull --ff-only
```

## 2. Systeemsoftware installeren

```bash
sudo dnf install -y \
  python3 python3-pip git 7zip tar \
  bind bind-utils httpd openssl \
  mysql-server mysql \
  php php-cli php-fpm php-mysqlnd
```

Controleer:

```bash
python3 --version
7z
tar --version
named-checkconf -v
named-checkzone -v
apachectl -v
mysql --version
openssl version
```

Backups worden gemaakt als `tar`-archief en daarna met 7-Zip gecomprimeerd naar
`.tar.7z`. De app ondersteunt zowel `7zz` als `7z`.

## 3. Services starten

```bash
sudo systemctl enable --now mysqld
sudo systemctl enable --now named
sudo systemctl enable --now httpd
sudo systemctl enable --now php-fpm
```

Controleer:

```bash
systemctl --no-pager --full status mysqld named httpd php-fpm
```

Test MySQL:

```bash
sudo mysql
```

Sluit af met `exit;`. Gebruik de MySQL-configuratie uit de cursusomgeving en
zet geen echte wachtwoorden in Git.

## 4. Python virtualenv en dependencies

```bash
cd ~/week5
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import textual, mysql.connector; print('Python dependencies OK')"
```

In een nieuwe shell:

```bash
cd ~/week5
source .venv/bin/activate
```

## 5. `.env` instellen

De app leest alleen het projectbestand `.env`. Shellvariabelen overschrijven
deze configuratie niet.

```bash
cp .env.example .env
chmod 600 .env
vi .env
```

Gebruik op de server bijvoorbeeld:

```dotenv
PROVISIONER_DRY_RUN=0
PROVISIONER_BACKUP_ROOT=/var/backups/website-provisioner
PROVISIONER_ZONE_ROOT=/var/named
PROVISIONER_NAMED_CONF=/etc/named.conf
PROVISIONER_DOCUMENT_ROOT=/var/www/html
PROVISIONER_VHOST_ROOT=/etc/httpd/conf.d
PROVISIONER_CERTIFICATE_ROOT=/etc/pki/tls
PROVISIONER_SERVER_IP=192.168.1.1
PROVISIONER_NAMESERVER=ns1.sil.
PROVISIONER_NAMESERVER_IP=192.168.1.1
PROVISIONER_BIND_USER=named
PROVISIONER_BIND_GROUP=named
PROVISIONER_APACHE_USER=apache
PROVISIONER_APACHE_GROUP=apache
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_ADMIN_USER=root
MYSQL_ADMIN_PASSWORD=<MYSQL-ADMIN-WACHTWOORD>
MYSQL_DATABASE_PREFIX=site_
MYSQL_USER_PREFIX=site_
```

Vervang `192.168.1.1` door het echte IP-adres van de server. Controleer de
effectieve niet-geheime instellingen:

```bash
python - <<'PY'
from src.config import AppConfig
config = AppConfig.from_environment()
print("dry_run:", config.dry_run)
print("server_ip:", config.server_ip)
print("nameserver_ip:", config.nameserver_ip)
print("document_root:", config.document_root)
PY
```

## 6. Mappen, rechten en SELinux

```bash
sudo mkdir -p \
  /var/backups/website-provisioner \
  /var/www/html \
  /var/named \
  /etc/httpd/conf.d \
  /etc/pki/tls/certs \
  /etc/pki/tls/private

sudo chown root:named /var/named
sudo chmod 0750 /var/named
sudo chown root:root /var/backups/website-provisioner
sudo chmod 0750 /var/backups/website-provisioner
sudo restorecon -RFv /var/named /var/www/html /etc/httpd/conf.d
```

De app zet nieuwe zonefiles op `named:named`, modus `0640`, en voert
`restorecon` uit. Schakel SELinux niet uit:

```bash
getenforce
ls -Zd /var/named /var/www/html /etc/httpd/conf.d
```

## 7. Eerst veilig testen met dry-run

Pas `.env` tijdelijk aan:

```dotenv
PROVISIONER_DRY_RUN=1
PROVISIONER_BACKUP_ROOT=/tmp/provisioner-backups
PROVISIONER_ZONE_ROOT=/tmp/provisioner-zones
PROVISIONER_NAMED_CONF=/tmp/named.conf
PROVISIONER_DOCUMENT_ROOT=/tmp/provisioner-www
PROVISIONER_VHOST_ROOT=/tmp/provisioner-vhosts
PROVISIONER_CERTIFICATE_ROOT=/tmp/provisioner-certs
```

Start:

```bash
PYTHONPATH=. python -m src.main
```

Dry-run herlaadt geen echte services en wijzigt geen echte
systeemconfiguratie.

## 8. Tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m compileall -q src tests
git diff --check
```

Een backup kan gecontroleerd worden met:

```bash
7z t /var/backups/website-provisioner/<backup>.tar.7z
```

## 9. Echte provisioning starten

Zet eerst in `.env`:

```dotenv
PROVISIONER_DRY_RUN=0
```

Start als root vanuit de repositoryroot:

```bash
cd ~/week5
source .venv/bin/activate
sudo env PYTHONPATH="$PWD" "$PWD/.venv/bin/python" -m src.main
```

`sudo` is nodig voor `/var/named`, `/etc/named.conf`,
`/etc/httpd/conf.d` en de certificaatmappen.

In de TUI:

1. Geef `test5` of `test5.sil` in.
2. Kies HTTPS indien nodig.
3. Kies MySQL indien nodig.
4. Kies static, todo of WordPress.
5. Klik op **Website aanmaken**.
6. Gebruik `Ctrl+Q` om af te sluiten.

Todo en WordPress vereisen een MySQL-database. Bestaat de website al, dan
wordt ze niet overschreven: de app maakt eerst een `.tar.7z`-backup en stopt.

## 10. WordPress

Bij een nieuwe WordPress-site downloadt de app automatisch de actuele officiële
release van:

```text
http://wordpress.org/latest.zip
```

De ZIP wordt tijdelijk opgeslagen, gecontroleerd en uitgepakt. De tijdelijke
bestanden worden na de provisioning verwijderd.

## 11. DNS controleren

```bash
sudo named-checkconf
sudo named-checkzone test5.sil /var/named/db.test5.sil
sudo grep -A5 -B1 'zone "test5.sil"' /etc/named.conf
sudo systemctl reload named
dig @192.168.1.1 test5.sil A
nslookup test5.sil 192.168.1.1
```

Als directe DNS-query werkt maar gewone `nslookup test5.sil` niet, gebruikt de
client een andere resolver. Controleer:

```bash
cat /etc/resolv.conf
resolvectl status
```

## 12. Apache en HTTPS controleren

```bash
sudo apachectl configtest
sudo systemctl reload httpd
curl -I http://test5.sil
curl -k -I https://test5.sil
```

Self-signed certificaten geven normaal een browserwaarschuwing.

## 13. Problemen oplossen

### BIND `Permission denied`

```bash
sudo chown root:named /var/named
sudo chmod 0750 /var/named
sudo chown named:named /var/named/db.<domein>.sil
sudo chmod 0640 /var/named/db.<domein>.sil
sudo restorecon -RFv /var/named
sudo named-checkzone <domein>.sil /var/named/db.<domein>.sil
sudo systemctl reload named
sudo journalctl -u named -n 50 --no-pager
```

### Zone bevat nog `127.0.0.1`

Controleer `.env`:

```bash
grep -E 'PROVISIONER_(DRY_RUN|SERVER_IP|NAMESERVER)' .env
```

Bestaande zones worden niet overschreven. Pas een oude zone gecontroleerd aan:

```bash
sudo sed -i 's/127\.0\.0\.1/192.168.1.1/g' /var/named/db.<domein>.sil
sudo named-checkzone <domein>.sil /var/named/db.<domein>.sil
sudo restorecon -v /var/named/db.<domein>.sil
sudo systemctl reload named
```

### `named.conf` krijgt geen zone-entry

Controleer:

```bash
grep '^PROVISIONER_DRY_RUN' .env
```

Voor echte provisioning moet dit zijn:

```text
PROVISIONER_DRY_RUN=0
```

## 14. Demo-checklist

Test vóór de controle:

- Backup van `www.klant3.sil`.
- Nieuwe statische HTTPS-site `www.secure<initialen>.sil`.
- Nieuwe todo-site `www.todo<initialen>.sil`.
- Nieuwe WordPress-site `www.wp<initialen>.sil`.

Controleer telkens DNS, Apache, documentroot, HTTPS en MySQL waar van
toepassing.
