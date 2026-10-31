# TelegramCaller

Fuente única de la arquitectura. Cada pieza aparece aquí una vez, con una sola responsabilidad. `AGENTS.md` no repite este mapa.

## Estado

Servicio FastAPI que registra cuentas personales de Telegram, autentica con OTP/2FA, mantiene sesiones Telethon vivas y envía mensajes con una cuenta conectada. Fuera de alcance: grupos, scripts, workers y dashboard.

## Arranque

`create_app` en `telegram_engine.main` carga `Settings`, crea el esquema SQLAlchemy, instancia los adaptadores y restaura sesiones válidas sin pedir OTP de nuevo.

Composición concreta:

- `SqlAccountStore` implementa `AccountStore`
- `TelethonGateway` implementa `TelegramGateway`
- `EncryptedSessionStore` implementa `SessionVault`
- `AccountService` recibe esos tres puertos
- FastAPI inyecta el servicio en `api` y exige `X-API-Key`

## Arquitectura

```text
api  →  accounts.AccountService  →  AccountStore | TelegramGateway | SessionVault
                                         ↑                ↑                 ↑
                                 SqlAccountStore   TelethonGateway  EncryptedSessionStore
```

## Responsabilidades

| Pieza | Responsabilidad | Depende de |
| --- | --- | --- |
| `core.config.Settings` | Leer configuración de entorno | — |
| `core.exceptions` | Errores de dominio del módulo de cuentas | — |
| `core.security` | Validar la API key interna | `Settings` |
| `accounts.models` | Tipos de cuenta, estado y reporte de conexión | — |
| `accounts.ports` | Contratos de persistencia, Telegram y sesiones | `accounts.models` |
| `accounts.AccountService` | Login, OTP, 2FA, listado, check, restore y envío de mensajes | `AccountStore`, `TelegramGateway`, `SessionVault` |
| `api.accounts` | HTTP OpenAPI de cuentas | `AccountService` |
| `api.messages` | HTTP `POST /send` | `AccountService` |
| `api.errors` | Mapeo de errores de dominio a HTTP | `core.exceptions` |
| `api.schemas` | Contratos JSON públicos (sin sesiones ni secretos) | — |
| `api.deps` | Cablear API key y servicio al router | `core.security`, `AccountService` |
| `database.models.AccountRow` | Tabla `accounts` y referencia a sesión | — |
| `database.SqlAccountStore` | Persistencia SQLite de cuentas | `AccountStore` |
| `telegram.TelethonGateway` | Cliente Telethon vivo por cuenta (OTP, 2FA, inspect, restore, send_message) | `TelegramGateway`, Telethon |
| `sessions.EncryptedSessionStore` | Archivos de sesión cifrados fuera del repo | `SessionVault`, Fernet |
| `main.create_app` | Componer adaptadores, restaurar sesiones y montar FastAPI | piezas de arriba |

Al agregar, mover o eliminar una pieza, actualiza esta tabla en el mismo cambio. Una fila por pieza. La columna de responsabilidad cabe en una frase y nombra una sola razón de cambio.
