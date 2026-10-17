# NovaStore PWA

Catálogo de productos construido con HTML, CSS y JavaScript, con una API local opcional en Python estándar (sin dependencias externas).

## Iniciar la aplicación y el servidor

Para habilitar la API, el Service Worker y la sincronización, abre una terminal en esta carpeta y ejecuta:

```powershell
python server.py
```

Abre `http://127.0.0.1:8000`. El servidor entrega la aplicación y la API en el mismo origen. Los productos enviados se conservan en `server-data/products.json`, creado al guardar el primer producto en el servidor.

La interfaz también puede abrirse con Live Server. En ese caso el catálogo, los favoritos, el carrito y las reseñas funcionan localmente, pero la API de Python no estará disponible; usa `server.py` para probar el envío al servidor. No abras el HTML con doble clic (`file://`): el navegador restringe el manifest y el Service Worker.

## Responsabilidades de cliente y servidor

- **Cliente (`index.html`, `style.css`, `app.js`)**: muestra la pantalla inicial y el catálogo, filtra productos, gestiona favoritos, carrito y reseñas, valida los formularios, persiste datos locales con `localStorage` y conserva en una cola los productos aún no enviados. La cola se reintenta al recuperar la conexión o mediante **Enviar pendientes**.
- **Servidor (`server.py`)**: sirve los archivos estáticos, valida los productos recibidos por HTTP, evita duplicados por identificador y persiste los productos sincronizados en `server-data/products.json`.
- **API**: `GET /api/products` devuelve `{ "products": [...] }`; `POST /api/products` recibe un producto JSON y devuelve `{ "product": ... }`. El Service Worker no cachea esta API, de modo que una respuesta guardada no suplante los datos del servidor.
- **Modo sin conexión**: el Service Worker cachea el App Shell y recursos esenciales. Los cambios del formulario se guardan primero en el navegador y quedan pendientes hasta recuperar la conexión; la app también ofrece un reintento manual. El backend no requiere sincronización en segundo plano.

## Pruebas

### Resultados de las pruebas

| Prueba | Resultado | Evidencia |
| --- | --- | --- |
| La pantalla inicial y la pantalla principal se presentan correctamente. | Aprobada | En navegador, título `NovaStore | Catálogo de productos`, encabezado de inicio y sección `Catálogo de productos` visibles. |
| Los datos se muestran en la interfaz. | Aprobada | El catálogo mostró los seis productos iniciales y el contador `6 productos`. |
| Los datos locales permanecen después de recargar. | Aprobada | Se guardó el ID de un favorito en `localStorage`, se recargó la app y la interfaz mostró `1 favorito`. La clave de prueba se eliminó al terminar. |
| Los recursos cacheados permiten abrir sin conexión. | Aprobada | Con el Service Worker activo y la caché `novastore-cache-v5`, se recargó offline y la portada, el catálogo y los seis productos siguieron disponibles. |
| Los pendientes se envían al recuperar conectividad. | Aprobada con reintento manual | La prueba de navegador anterior registró un producto offline, lo conservó tras recargar y, al volver online, se envió mediante **Enviar pendientes**; el endpoint confirmó el registro. |
| Los reintentos no duplican registros. | Aprobada en API | La prueba automatizada envió dos veces el mismo ID con valores distintos y `GET /api/products` devolvió un solo producto con el valor actualizado. |
| El servidor rechaza datos inválidos. | Aprobada | Dos pruebas cubren datos incompletos/inválidos y un precio fuera del rango finito. |

```powershell
python -m unittest discover -s tests -v
```

Resultado de la última ejecución: **4 pruebas aprobadas**. Casos cubiertos: catálogo vacío, registro persistente, reemplazo idempotente del mismo identificador y rechazo de datos inválidos.

### Cómo repetir la prueba offline y sincronización

1. Inicia `python server.py`, abre `http://127.0.0.1:8000` y espera a que cargue el catálogo una vez.
2. En las herramientas de desarrollo del navegador, abre **Network** y selecciona **Offline**.
3. En **Agregar un producto**, registra uno nuevo. Debe aparecer en el catálogo y aumentar el contador de pendientes; el mensaje informa que quedó guardado sin conexión.
4. Recarga la página todavía sin conexión: el App Shell y el producto local deben seguir disponibles.
5. Vuelve a **Online**. La app reintenta automáticamente; también puedes pulsar **Enviar pendientes**.
6. Comprueba que el contador regrese a cero, recarga y verifica que el producto siga visible. En otra terminal, inspecciona `server-data/products.json` para confirmar que el servidor recibió el producto.

### Limitaciones y errores encontrados

- La sincronización automática se dispara al recuperar la conexión, pero no tiene Background Sync. Una simulación de red produjo `Failed to fetch` durante la transición online; el producto quedó en la cola y el reintento manual lo envió correctamente. Se agregó una breve espera antes del reintento automático, pero ese camino automático todavía debe repetirse en un navegador/red real.
- El servidor es local y de demostración: no tiene autenticación, no es multiusuario y persiste en un archivo JSON, no en una base de datos. Para probar la API se debe ejecutar `server.py`; Live Server por sí solo no proporciona los endpoints.
- Favoritos, carrito y reseñas se guardan solo en el navegador. El backend sincroniza productos, no los demás módulos.
- El almacenamiento local depende del navegador y del origen, y puede eliminarse desde sus ajustes. Si no hay servidor disponible, los registros permanecen pendientes hasta un reintento posterior.
- Error corregido en las pruebas HTTP: `http.client` intentaba codificar el JSON con emojis como Latin-1. El cuerpo ahora se codifica explícitamente como UTF-8.
- Errores de persistencia, respuestas inválidas y fallos HTTP dejan los registros en la cola y se notifican; el Service Worker no guarda respuestas de `/api/` en caché.

Comprobaciones complementarias: `node --check app.js`, `node --check service-worker.js` y el parseo de `manifest.json` finalizaron sin errores.

## Archivos principales

- `index.html`: pantalla inicial, catálogo y módulos de la interfaz.
- `style.css`: estilos adaptables y diseño funcional sin recursos externos requeridos.
- `app.js`: comportamiento de la vista, persistencia local y sincronización `fetch()`.
- `manifest.json`: configuración instalable de la PWA.
- `service-worker.js`: App Shell y Cache API.
- `server.py`: servidor HTTP y endpoints de la API.
- `tests/test_server.py`: pruebas automatizadas del backend.
- `icons/icon.svg`: icono de la aplicación.
