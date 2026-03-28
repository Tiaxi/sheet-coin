from sheet_coin.config import Settings


def test_settings_defaults():
    s = Settings(auth_username="user", auth_password="pass")
    assert s.auth_username == "user"
    assert s.auth_password == "pass"
    assert s.port == 19877
    assert s.polling_interval == 45
    assert s.api_timeout == 60
    assert s.log_level == "INFO"


def test_settings_custom_values():
    s = Settings(
        auth_username="u",
        auth_password="p",
        port=8080,
        polling_interval=30,
        api_timeout=120,
        log_level="DEBUG",
    )
    assert s.port == 8080
    assert s.polling_interval == 30
    assert s.api_timeout == 120
    assert s.log_level == "DEBUG"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SHEET_COIN_AUTH_USERNAME", "envuser")
    monkeypatch.setenv("SHEET_COIN_AUTH_PASSWORD", "envpass")
    monkeypatch.setenv("SHEET_COIN_PORT", "9999")
    s = Settings()
    assert s.auth_username == "envuser"
    assert s.auth_password == "envpass"
    assert s.port == 9999
