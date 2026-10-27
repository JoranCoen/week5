"""Textual user interface for the provisioning workflow."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from src.config import AppConfig
from src.models import ProvisionRequest, WebsiteType
from src.services.provisioner import ExistingSiteError, provision
from src.services.validation import normalise_domain


class ProvisioningApp(App[None]):
    """Collect, confirm and execute one provisioning request."""

    TITLE = "Website Provisioner"
    SUB_TITLE = "Linux week 5  |  MySQL  •  Apache  •  BIND"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [("ctrl+q", "quit", "Afsluiten")]
    CSS = """
    Screen {
        align: center middle;
        background: #101827;
    }
    #form {
        width: 82;
        height: 1fr;
        padding: 0 4;
        overflow-y: auto;
        background: #101827;
    }
    #intro {
        height: 1;
        margin-bottom: 1;
        color: #91a4bd;
    }
    .section-title {
        color: #55d6c2;
        text-style: bold;
    }
    .field-label {
        color: #d9e2f0;
    }
    Input {
        width: 100%;
        height: 3;
        margin-bottom: 1;
        background: #182438;
        border: tall #2b405c;
        color: #f2f6fc;
    }
    Select {
        width: 100%;
        height: 3;
        margin-bottom: 1;
        background: #182438;
        color: #f2f6fc;
    }
    Select > SelectCurrent {
        height: 3;
        padding: 0 1;
        border: tall #2b405c;
        background: #182438;
        color: #f2f6fc;
    }
    Select > SelectCurrent Static#label {
        color: #f2f6fc;
        background: transparent;
    }
    Select > SelectCurrent .arrow {
        color: #55d6c2;
        background: transparent;
    }
    #status {
        width: 100%;
        height: 2;
        margin: 0;
        color: #d9e2f0;
    }
    #actions {
        dock: bottom;
        width: 100%;
        height: 4;
        align: center middle;
        background: #101827;
    }
    .toggle {
        width: 100%;
        height: 3;
        margin-bottom: 1;
        text-align: left;
        background: #182438;
        border: tall #2b405c;
        color: #d9e2f0;
    }
    .toggle:hover {
        background: #21334d;
        border: tall #55d6c2;
    }
    .toggle:focus {
        border: tall #f4bd62;
    }
    #provision {
        width: 100%;
        height: 3;
        background: #55d6c2;
        color: #101827;
        text-style: bold;
    }
    #provision:hover {
        background: #7ce7d6;
    }
    #provision.request-valid {
        background: #55d6c2;
        color: #101827;
    }
    Footer {
        background: #101827;
        color: #91a4bd;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig.from_environment()
        self.use_https = False
        self.has_database = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="form"):
            yield Static(
                "Maak een nieuwe website aan op de Linux-server.",
                id="intro",
            )
            yield Label("1. Website", classes="section-title")
            yield Label("Domein", classes="field-label")
            yield Input(placeholder="test5 of test5.sil", id="domain")

            yield Label("2. Beveiliging en data", classes="section-title")
            yield Label("HTTPS", classes="field-label")
            yield Button(
                "[red]✗[/]  HTTPS uit  — geen certificaat",
                id="https-toggle",
                classes="toggle",
            )
            yield Label("MySQL-database", classes="field-label")
            yield Button(
                "[red]✗[/]  Database uit  — geen MySQL-database",
                id="database-toggle",
                classes="toggle",
            )
            yield Label("MySQL-wachtwoord", classes="field-label")
            yield Input(
                placeholder="Wachtwoord voor de nieuwe MySQL-gebruiker",
                password=True,
                id="database-password",
            )

            yield Label("3. Inhoud", classes="section-title")
            yield Label("Type website", classes="field-label")
            yield Select(
                [(website_type.value, website_type) for website_type in WebsiteType],
                value=WebsiteType.STATIC,
                id="website-type",
            )
            yield Static(
                "",
                id="status",
            )
            with Horizontal(id="actions"):
                yield Button("Website aanmaken", variant="primary", id="provision")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "https-toggle":
            self.use_https = not self.use_https
            self._update_toggle(
                event.button,
                self.use_https,
                "HTTPS aan  — self-signed certificaat",
                "HTTPS uit  — geen certificaat",
            )
            return
        if event.button.id == "database-toggle":
            self.has_database = not self.has_database
            self._update_toggle(
                event.button,
                self.has_database,
                "Database aan  — MySQL-database aanmaken",
                "Database uit  — geen MySQL-database",
            )
            return
        if event.button.id != "provision":
            return
        try:
            request = self._request()
        except ValueError as error:
            self._reset_provision_button()
            self._status(str(error))
            return
        self._set_buttons(False)
        self._mark_request_valid()
        self._status(f"Bezig met {request.domain}...")
        try:
            result = provision(request, self.config)
        except ExistingSiteError as error:
            self._reset_provision_button()
            self._status(str(error))
        except PermissionError as error:
            self._reset_provision_button()
            self._status(f"Rechten ontbreken. {error}")
        except Exception as error:
            self._reset_provision_button()
            self._status(f"Niet uitgevoerd: {error}")
        else:
            database = (
                f" MySQL-database: {result.database.name}."
                if result.database
                else " Geen database."
            )
            self._status(
                f"Klaar: {result.domain}.{database}\nDocument root: {result.document_root}"
            )
            self._mark_provisioned()
        finally:
            self._set_buttons(True)

    def _request(self) -> ProvisionRequest:
        domain = normalise_domain(self.query_one("#domain", Input).value)
        website_type = self.query_one("#website-type", Select).value
        if not isinstance(website_type, WebsiteType):
            website_type = WebsiteType.STATIC
        if website_type is not WebsiteType.STATIC and not self.has_database:
            raise ValueError("Todo en WordPress vereisen een MySQL-database.")
        if website_type is WebsiteType.STATIC and self.has_database:
            raise ValueError("Kies voor een database een todo- of WordPress-website.")
        database_password = (
            self.query_one("#database-password", Input).value
            if self.has_database
            else None
        )
        if self.has_database and not database_password:
            raise ValueError("Vul het MySQL-wachtwoord in.")
        return ProvisionRequest(
            domain=domain,
            https=self.use_https,
            database=self.has_database,
            website_type=website_type,
            database_password=database_password,
        )

    def _status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _set_buttons(self, enabled: bool) -> None:
        self.query_one("#provision", Button).disabled = not enabled
        self.query_one("#https-toggle", Button).disabled = not enabled
        self.query_one("#database-toggle", Button).disabled = not enabled

    def _mark_request_valid(self) -> None:
        button = self.query_one("#provision", Button)
        button.label = "[green]✓[/]  Gegevens kloppen — bezig..."
        button.add_class("request-valid")

    def _reset_provision_button(self) -> None:
        button = self.query_one("#provision", Button)
        button.label = "Website aanmaken"
        button.remove_class("request-valid")

    def _mark_provisioned(self) -> None:
        button = self.query_one("#provision", Button)
        button.label = "[green]✓[/]  Website aangemaakt"
        button.add_class("request-valid")

    def _update_toggle(
        self,
        button: Button,
        selected: bool,
        enabled_text: str,
        disabled_text: str,
    ) -> None:
        icon = "[green]✓[/]" if selected else "[red]✗[/]"
        button.label = f"{icon}  {enabled_text if selected else disabled_text}"


def run() -> None:
    """Start the provisioning terminal interface."""
    ProvisioningApp().run()
