# CropSignal — MVP

Una PWA *offline-first* para vigilancia fitosanitaria comunitaria centrada en café arábica. El agricultor registra una foto y recibe un resultado de clasificación local en el teléfono; cuando recupera conectividad, solo se sincroniza un reporte anonimizado. El panel colectivo detecta concentraciones espacio-temporales y marca un posible brote.

> **Nota de seguridad:** el MVP incluye un clasificador real de cinco condiciones de hoja de café: Cercospora, sano/sin condición visible soportada, roya, minador y Phoma. Corre enteramente en el teléfono. Se entrenó como un pequeño prototipo con imágenes del dataset JMuBEN/JMuBEN2 recolectadas en Kirinyaga, Kenia; no es una validación independiente de campo ni sustituye a un extensionista agrícola.

## Arranque

Requiere Python 3.10+ (sin instalar paquetes):

```powershell
python server.py
```

Abre [http://localhost:8000](http://localhost:8000). Para ver el panel, visita [http://localhost:8000/dashboard.html](http://localhost:8000/dashboard.html).

## Demo sugerida

1. Abre la app una vez con conexión para precargar el modelo. Después puede funcionar sin red.
2. Pulsa **Try coffee-rust demo**. El modelo se ejecuta en el propio navegador y devuelve una señal de roya sobre una imagen real del conjunto de desarrollo.
3. Añade observaciones opcionales, guarda el resultado y comprueba que entra en la cola local; no se guarda la foto.
4. Selecciona **Kiswahili · pilot** y pulsa **Hear guidance**. Usa la voz instalada en el teléfono; el texto y la decisión siguen siendo locales.
5. Recupera conexión y pulsa **Sync now**. Abre el panel y pulsa **Load outbreak demo**: aparecerá un posible brote. El botón **Preview Kiswahili alert** crea un borrador para revisión humana, no envía mensajes automáticamente.

## Arquitectura

- `index.html`: PWA de agricultor; cámara, inferencia TF.js de café, ubicación aproximada, observaciones opcionales, guía en inglés/kiswahili piloto y cola en `localStorage`.
- `dashboard.html`: mapa en canvas, tablero de alertas y borrador de aviso para revisión por personal extensionista.
- `server.py`: API Python estándar y detector determinista de clusters (misma etiqueta, radio y ventana temporal).
- `model/`: modelo TF.js y pesos locales; `vendor/tf.min.js` es el runtime del navegador.
- `model-coffee-v1/`: modelo MobileNetV2 de cinco clases y pesos TF.js (~1,7 MB).
- `training/download_coffee_pilot.py`: descarga reanudable y validada de un subconjunto de desarrollo reproducible.
- `training/train_coffee_mvp.py`: entrenamiento del clasificador local.
- `sw.js`: precachea frontend, runtime y los pesos para ejecutar sin red tras la primera instalación.

## Voz de despliegue

La versión actual usa la voz que ya esté instalada en el dispositivo: no hace llamadas de red ni expone secretos. `training/generate_voice_prompts.py` genera unos pocos MP3 revisados previamente y los guarda dentro de la PWA cuando el workspace de ElevenLabs permita TTS. Esa será la ruta de despliegue: pulsar *Hear guidance* seguirá funcionando sin conectividad y sin una key en el teléfono.

La fuente de datos, el alcance y las limitaciones están en [COFFEE_MODEL_CARD.md](COFFEE_MODEL_CARD.md).

El modelo incluido, sus limitaciones y el proceso de reproducción están documentados en [COFFEE_MODEL_CARD.md](COFFEE_MODEL_CARD.md). Para ampliar el modelo, ejecutad `training/download_coffee_pilot.py`, `training/train_coffee_mvp.py` y `training/export_tfjs.py`; para producción, añadir imágenes de campo locales con consentimiento, deduplicación por finca, autenticación, cifrado, auditoría de datos y validación por extensionistas antes de enviar recomendaciones o notificaciones.
