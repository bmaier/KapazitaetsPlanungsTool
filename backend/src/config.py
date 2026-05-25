"""
Konfiguration für den BorderCapControl Backend.
Alle Werte werden aus Umgebungsvariablen gelesen (12-Factor-App-Prinzip).
Kein Hardcoding von Credentials im Produktionscode.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Defaults entsprechen den docker-compose.yml-Werten für lokale Entwicklung.
    # In Staging/Produktion MÜSSEN alle Werte via Umgebungsvariablen gesetzt werden.
    database_url: str = (
        "postgresql+asyncpg://bordercap:bordercap_dev@postgres:5432/bordercap"
    )
    keycloak_url: str = "http://keycloak:8080"
    # Public URL wie der Browser Keycloak sieht — für iss-Validierung im JWT.
    # Unterscheidet sich in Docker-Setups von keycloak_url (internes Netz).
    keycloak_public_url: str = ""
    keycloak_realm: str = "bordercapcontrol"
    keycloak_client_id: str = "bordercapcontrol-frontend"
    task_cleanup_days: int = 30

    model_config = {"env_file": ".env"}


settings = Settings()
