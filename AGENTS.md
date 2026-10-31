# AGENTS.md

Instrucciones para agentes que trabajen en este repositorio. La arquitectura vive solo en `Project.md`.

## Antes de cambiar código

1. Leer `Project.md` y ubicar qué pieza es dueña del comportamiento que vas a tocar.
2. Reutilizar esa pieza. Si ninguna cubre el caso, extender el diseño y actualizar `Project.md` en el mismo cambio.
3. Nombrar módulos, clases, funciones y variables en inglés.

## DRY

Una regla, un tipo o un flujo de datos tiene un solo lugar.

- No copies lógica, validaciones ni mapeos entre módulos. Extrae la pieza compartida y haz que ambos la usen.
- No dupliques la arquitectura en este archivo, en comentarios ni en otros docs. Si cambia un módulo o su responsabilidad, actualiza `Project.md`.
- No crees un helper, DTO o cliente nuevo si ya existe uno que cumple el contrato.

```text
Mal:  CallerService y NotifierService parsean el mismo payload por separado.
Bien: un solo parser; ambos servicios lo reciben ya interpretado.
```

## SOLID

- **S — Una responsabilidad.** Cada módulo de `Project.md` cambia por una sola razón. Si una clase valida, persiste y llama a Telegram, divídela.
- **O — Abierta a extensión.** Un caso nuevo (otro transporte, otro formato) entra como una implementación nueva, sin reescribir el flujo que ya funciona.
- **L — Sustitución.** Toda implementación de una interfaz cumple el contrato de quien la usa: mismos errores, mismos vacíos, mismos efectos. No endurezcas precondiciones ni debilites resultados.
- **I — Interfaces pequeñas.** Quien llama depende solo de los métodos que usa. No pases un cliente completo si el consumidor solo envía un mensaje.
- **D — Depender de abstracciones.** El dominio recibe puertos (interfaces). Los clientes concretos de Telegram, almacenamiento o HTTP se conectan en el borde (composición / arranque).

```text
Mal:  el caso de uso instancia TelegramClient y conoce el JSON de la API.
Bien: el caso de uso depende de MessageSender; el arranque inyecta TelegramMessageSender.
```

## README

`README.md` es la guía de arranque y uso. No copies ahí la arquitectura de `Project.md`.

Actualízalo en el mismo cambio cuando varíe cómo se levanta el servicio, qué variables de entorno hace falta, o cómo se llaman los endpoints públicos. Un operador debe poder arrancar y usar el servicio solo con ese archivo.

## Al cerrar un cambio de estructura

Actualiza en `Project.md`, en el mismo cambio:

- la pieza nueva, movida o eliminada
- su responsabilidad en una frase
- de qué abstracción depende y qué implementación concreta vive en el borde

No dejes la arquitectura solo en el código.
