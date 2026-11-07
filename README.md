# TelegramCaller

Servicio FastAPI para registrar cuentas personales de Telegram, autenticarlas con OTP (y 2FA si aplica) y mantener las sesiones Telethon activas. La arquitectura está en `Project.md`.

## Requisitos

- Python 3.11+ o Docker
- `api_id` y `api_hash` de [my.telegram.org](https://my.telegram.org)

## Configuración

Copia `.env.example` a `.env` y completa:

| Variable | Uso |
| --- | --- |
| `PORT` | Puerto HTTP del servicio (por defecto `8000`) |
| `DATABASE_URL` | SQLite async, p. ej. `sqlite+aiosqlite:///./data/telegram_engine.db` |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | Credenciales de la app Telegram |
| `SESSION_STORE_PATH` | Directorio privado para sesiones cifradas (fuera de git) |
| `SESSION_ENCRYPTION_KEY` | Clave Fernet |
| `INTERNAL_API_KEY` | Valor de `X-API-Key` en todas las rutas |
| `INCOMING_WEBHOOK_URL` | POST JSON cada vez que una cuenta recibe un mensaje. Vacío = no notificar. |

Generar la clave de cifrado:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Arranque con Docker

```bash
docker compose up --build
```

La API queda en `http://localhost:8000`. OpenAPI interactivo: `http://localhost:8000/docs`. Spec estática: `swagger.json` (regenerar con `python scripts/export_openapi.py`). SQLite y las sesiones viven en el volumen `appdata`.

## Arranque local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m telegram_engine
```

El archivo SQLite se crea en `data/telegram_engine.db` si no existe.

## Uso

Todas las peticiones llevan `X-API-Key`.

1. Pedir OTP

```bash
curl -X POST http://localhost:8000/accounts/login ^
  -H "X-API-Key: TU_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"phone_number\": \"+15551234567\"}"
```

Respuesta: `account_id`, `status` (`pending_otp`) y `message`.

2. Verificar OTP

```bash
curl -X POST http://localhost:8000/accounts/verify-otp ^
  -H "X-API-Key: TU_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"account_id\": \"UUID\", \"otp\": \"12345\"}"
```

Si Telegram pide 2FA, el cuerpo incluye `status: pending_2fa`. Completar con:

```bash
curl -X POST http://localhost:8000/accounts/verify-2fa ^
  -H "X-API-Key: TU_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"account_id\": \"UUID\", \"password\": \"TU_2FA\"}"
```

3. Estado real de una cuenta

```bash
curl http://localhost:8000/accounts/UUID/check -H "X-API-Key: TU_KEY"
```

4. Listar cuentas (sin sesiones ni secretos)

```bash
curl http://localhost:8000/accounts -H "X-API-Key: TU_KEY"
```

5. Eliminar una cuenta (cierra el cliente, borra la sesión y el registro)

```bash
curl -X DELETE http://localhost:8000/accounts/UUID -H "X-API-Key: TU_KEY"
```

6. Enviar un mensaje con una cuenta `connected`

```bash
curl -X POST http://localhost:8000/send ^
  -H "X-API-Key: TU_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"account\": \"UUID\", \"to\": \"username\", \"message\": \"hola\"}"
```

Al reiniciar el servicio se restauran las sesiones válidas; no se vuelve a pedir OTP si la sesión sigue vigente.

Cuando una cuenta `connected` recibe un mensaje, el servicio hace POST a `INCOMING_WEBHOOK_URL`:

```json
{
  "account_id": "UUID",
  "message": "texto",
  "from": "username"
}
```

`from` es el username de Telegram o, si no hay, el id numérico.

## Pruebas

```bash
python -m pytest tests --ignore=tests/integration
```

Las pruebas contra Telegram real están en `tests/integration` y solo corren con `TELEGRAM_LIVE_TESTS=1`.
