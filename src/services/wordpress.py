"""Download and safely unpack the current WordPress release."""

from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

WORDPRESS_DOWNLOAD_URL = "https://wordpress.org/latest.zip"


def download_wordpress(destination: Path) -> Path:
    """Download WordPress and return the directory containing its files."""
    archive = destination / "wordpress.zip"
    extracted = destination / "extracted"
    request = Request(WORDPRESS_DOWNLOAD_URL, headers={"User-Agent": "website-provisioner/1.0"})
    with urlopen(request, timeout=60) as response, archive.open("wb") as output:
        output.write(response.read())
    extracted.mkdir()
    with ZipFile(archive) as wordpress_zip:
        root = extracted.resolve()
        for member in wordpress_zip.infolist():
            target = (extracted / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError("Ongeldige WordPress-zip: pad buiten extractiemap.")
        wordpress_zip.extractall(extracted)
    wordpress_root = extracted / "wordpress"
    if not wordpress_root.is_dir():
        raise ValueError("Ongeldige WordPress-download: map wordpress ontbreekt.")
    return wordpress_root
