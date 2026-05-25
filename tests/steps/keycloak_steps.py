"""
Behave Step-Definitionen für Keycloak Realm-Konfiguration.
Nutzt die Keycloak Admin REST API mit Basic Auth.
"""
import os
import requests
from behave import given, when, then

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin_dev")
TARGET_REALM = os.environ.get("KEYCLOAK_REALM", "bordercapcontrol")


def _get_admin_token(base_url: str, username: str, password: str) -> str:
    """Holt einen Admin-Access-Token über den master-Realm."""
    token_url = f"{base_url}/realms/master/protocol/openid-connect/token"
    resp = requests.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        },
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Keycloak Admin-Token konnte nicht geholt werden: "
        f"HTTP {resp.status_code} — {resp.text[:300]}"
    )
    return resp.json()["access_token"]


def _admin_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

@given("Keycloak läuft auf {url}")
def step_keycloak_running(context, url):
    """Prüft, dass Keycloak erreichbar ist und holt einen Admin-Token."""
    context.keycloak_base_url = url.strip()
    try:
        health_url = f"{context.keycloak_base_url}/health/ready"
        resp = requests.get(health_url, timeout=15)
        assert resp.status_code == 200, (
            f"Keycloak Health-Check fehlgeschlagen: HTTP {resp.status_code}"
        )
    except requests.exceptions.ConnectionError as exc:
        raise AssertionError(
            f"Keycloak unter {context.keycloak_base_url} nicht erreichbar. "
            "Bitte 'make dev' ausführen."
        ) from exc
    context.admin_token = _get_admin_token(
        context.keycloak_base_url,
        KEYCLOAK_ADMIN_USER,
        KEYCLOAK_ADMIN_PASSWORD,
    )


# ---------------------------------------------------------------------------
# Realm-Prüfung
# ---------------------------------------------------------------------------

@when("ich die Keycloak Admin-API abfrage")
def step_query_keycloak_admin(context):
    """Ruft die Liste aller Realms ab."""
    url = f"{context.keycloak_base_url}/admin/realms"
    resp = requests.get(url, headers=_admin_headers(context.admin_token), timeout=15)
    assert resp.status_code == 200, (
        f"Admin-API Realms-Endpoint fehlgeschlagen: HTTP {resp.status_code}"
    )
    context.realms = resp.json()


@then('existiert der Realm "{realm_name}"')
def step_realm_exists(context, realm_name):
    realm_names = [r.get("realm") for r in context.realms]
    assert realm_name in realm_names, (
        f"Realm '{realm_name}' nicht gefunden. "
        f"Vorhandene Realms: {realm_names}"
    )


# ---------------------------------------------------------------------------
# Rollen-Prüfung
# ---------------------------------------------------------------------------

@when("ich die Realm-Rollen abfrage")
def step_query_realm_roles(context):
    """Ruft alle Realm-Rollen für bordercapcontrol ab."""
    url = f"{context.keycloak_base_url}/admin/realms/{TARGET_REALM}/roles"
    resp = requests.get(url, headers=_admin_headers(context.admin_token), timeout=15)
    assert resp.status_code == 200, (
        f"Realm-Rollen-Endpoint fehlgeschlagen: HTTP {resp.status_code} — {resp.text[:300]}"
    )
    context.realm_roles = resp.json()


@then('existiert die Rolle "{role_name}"')
def step_role_exists(context, role_name):
    role_names = [r.get("name") for r in context.realm_roles]
    assert role_name in role_names, (
        f"Rolle '{role_name}' nicht gefunden im Realm '{TARGET_REALM}'. "
        f"Vorhandene Rollen: {role_names}"
    )


# ---------------------------------------------------------------------------
# Client-Prüfung (PKCE)
# ---------------------------------------------------------------------------

@when('ich den Client "{client_id}" abfrage')
def step_query_client(context, client_id):
    """Sucht den Client anhand der clientId."""
    url = (
        f"{context.keycloak_base_url}/admin/realms/{TARGET_REALM}/clients"
        f"?clientId={client_id}"
    )
    resp = requests.get(url, headers=_admin_headers(context.admin_token), timeout=15)
    assert resp.status_code == 200, (
        f"Client-Endpoint fehlgeschlagen: HTTP {resp.status_code}"
    )
    clients = resp.json()
    assert len(clients) > 0, (
        f"Client '{client_id}' nicht im Realm '{TARGET_REALM}' gefunden."
    )
    context.client_data = clients[0]


@then("ist der Client ein Public Client")
def step_client_is_public(context):
    is_public = context.client_data.get("publicClient", False)
    assert is_public is True, (
        f"Client ist kein Public Client. 'publicClient' = {is_public}. "
        f"Client-Konfiguration: {context.client_data}"
    )


@then("unterstützt der Client PKCE")
def step_client_supports_pkce(context):
    """
    PKCE ist in Keycloak über den Attribute-Key 'pkce.code.challenge.method' konfiguriert.
    Bei Public Clients ist PKCE implizit verfügbar; ein explizit gesetzter Wert ist optional.
    Wir prüfen, dass der Client ein Public Client ist (PKCE-Voraussetzung) und dass
    kein explizites Deaktivieren gesetzt ist.
    """
    attributes = context.client_data.get("attributes", {})
    pkce_method = attributes.get("pkce.code.challenge.method", "S256")
    is_public = context.client_data.get("publicClient", False)
    assert is_public is True, (
        "PKCE erfordert einen Public Client. 'publicClient' ist False."
    )
    # Nur S256 ist sicher — "plain" bietet keinen Sicherheitsvorteil
    assert pkce_method in ("S256", ""), (
        f"Ungültige PKCE-Methode: '{pkce_method}'. Nur S256 (oder Keycloak-Default '') erlaubt."
    )
