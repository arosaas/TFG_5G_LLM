from nicegui import ui, app, run
import time
import datetime
import logging
from llm_utils import get_llm_provider, get_model_name

# Importamos tus módulos locales
import configuraciones
import modulos_ia
from generar_configuraciones import parsear_respuesta, exportar
from utilidades import sim_cos

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/5g_config_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- ESTADO GLOBAL DE LA APLICACIÓN ---
estado = {
    "llm_provider": None,
    "model_gen": None,
    "model_emb": None,
    "cache": None,
    "bd": [],
    "listo": False
}
historial_chat = []

# Referencias globales para comunicar los elementos de la interfaz entre funciones
area_chat = None
input_texto = None

# --- FUNCIONES DE BACKEND (Ejecutadas en hilos secundarios) ---
def inicializacion_pesada():
    """Ejecuta toda la carga de CAG y RAG en un hilo secundario sin congelar la web."""
    logger.info("Starting heavy initialization in background thread")

    # Initialize LLM provider using utility functions
    llm_provider = get_llm_provider()
    model_gen = get_model_name("gen")
    model_emb = get_model_name("emb")

    logger.debug("LLM provider initialized")
    cache = modulos_ia.cargar_cag(configuraciones.RUTAS_CAG, llm_provider, model_gen)
    logger.debug("CAG cache created")
    bd = modulos_ia.cargar_bd(configuraciones.BD_LOCAL)
    logger.debug(f"Loaded vector database with {len(bd)} entries")
    docs = modulos_ia.extraer_documentos(configuraciones.RUTAS_RAG)
    logger.debug(f"Extracted {len(docs)} document chunks")
    bd = modulos_ia.vectorizar_pendientes(bd, docs, llm_provider)
    logger.info(f"Initialization complete: {len(bd)} vectors in database")
    return llm_provider, model_gen, model_emb, cache, bd

def consultar_llm(user_input, bd, llm_provider, model_gen, model_emb, cache):
    """Realiza la búsqueda RAG y llama a la API de LLM."""
    logger.info(f"Processing LLM query: '{user_input[:50]}...'")
    top_docs = modulos_ia.buscar_rag(user_input, bd, llm_provider)
    logger.debug(f"RAG search returned {len(top_docs)} documents")
    contexto_rag = "--- TEORÍA RECUPERADA (RAG) ---\n"

    for doc in top_docs:
        contexto_rag += f"\n[Fuente: {doc['nombre']}]\n{doc['texto']}\n"

    prompt_final = (
        f"Petición del usuario:\n{user_input}\n\n"
        f"{contexto_rag}\n\n"
        "Genera ahora los tres archivos siguiendo estrictamente "
        "las reglas del system prompt."
    )
    logger.debug(f"Final prompt length: {len(prompt_final)} chars")

    config_generation = types.GenerateContentConfig(
        temperature=0.1,
        cached_content=cache.name
    )

    logger.info("Sending request to LLM API")
    response = llm_provider.generate_content(
        model=model_gen,
        contents=prompt_final,
        config=config_generation,
    )

    logger.info("Received response from LLM API")
    return response.text

# --- COMPONENTES DE INTERFAZ Y LÓGICA DE EVENTOS ---

@ui.refreshable
def contenedor_mensajes():
    """Dibuja los mensajes del chat reactivamente iterando sobre historial_chat"""
    for msg in historial_chat:
        ui.chat_message(
            text=msg['texto'],
            name=msg['nombre'],
            sent=msg['sent'],
            avatar='https://robohash.org/5g' if not msg['sent'] else None
        )

async def enviar_mensaje(e):
    global area_chat, input_texto

    texto = e.sender.value
    if not texto or not estado["listo"]:
        logger.warning("Attempted to send message but system not ready or empty text")
        return

    logger.info(f"User message received: '{texto[:50]}...'")

    # Limpiar el input de texto inmediatamente en la pantalla
    e.sender.value = ''

    # Añadir mensaje del usuario a la lista e indicar actualización en el componente
    historial_chat.append({'nombre': 'Tú', 'texto': texto, 'sent': True})
    contenedor_mensajes.refresh()

    # Mostrar un indicador visual animado ("pensando...") dentro de la zona de chat
    with area_chat:
        spinner = ui.spinner('dots', size='lg', color='primary')

    try:
        start = datetime.datetime.now()
        logger.info("Starting LLM query processing in background thread")
        # run.io_bound evita que la petición a Gemini congele la pestaña web
        texto_raw = await run.io_bound(consultar_llm, texto, estado["bd"],
                                       estado["llm_provider"], estado["model_gen"],
                                       estado["model_emb"], estado["cache"])

        # Parsear e invocar tus validadores automáticos sobre las secciones generadas
        logger.debug("Parsing LLM response")
        bloques, error = parsear_respuesta(texto_raw)

        if error:
            logger.warning(f"LLM response validation failed: {error}")
            respuesta_bot = f"❌ **Error de validación:**\n{error}"
        else:
            timestamp = int(time.time())
            logger.info(f"Exporting generated configurations with timestamp {timestamp}")
            exportar(bloques, timestamp)
            end = datetime.datetime.now()
            tiempo = (end - start).total_seconds()

            respuesta_bot = f"✅ **Configuraciones generadas y exportadas con éxito** (Tiempo: {tiempo:.2f}s).\n\n"
            if bloques.get("notes"):
                logger.debug("Including model notes in response")
                respuesta_bot += f"**Notas del experto:**\n{bloques['notes']}"

            logger.info(f"Configuration generation successful in {tiempo:.2f}s")

    except Exception as exc:
        logger.error(f"Exception in LLM query processing: {exc}")
        respuesta_bot = f"⚠️ **Excepción en la API de LLM:** {exc}"

    finally:
        # Eliminar la animación de carga, añadir respuesta final y auto-scrollear abajo
        spinner.delete()
        historial_chat.append({'nombre': 'Asistente 5G', 'texto': respuesta_bot, 'sent': False})
        contenedor_mensajes.refresh()
        area_chat.scroll_to(percent=100)

# --- CONSTRUCCIÓN DE LA PÁGINA (LAYOUT) ---

@ui.page('/')
async def pagina_principal():
    global area_chat, input_texto

    ui.page_title('Asistente O-RAN 5G')

    # Barra superior (Header)
    with ui.header(elevated=True).classes('bg-blue-900 items-center justify-between'):
        ui.label('🤖 Generador de Despliegues 5G (srsRAN / OAI)').classes('text-xl font-bold')
        ui.icon('cell_tower', size='md')

    # Caja central del Chatbot (Ancho máximo responsivo de Tailwind CSS)
    with ui.column().classes('w-full max-w-3xl mx-auto h-[80vh] no-wrap'):
        # Zona con scroll para ver el historial
        area_chat = ui.scroll_area().classes('w-full h-full p-4 border rounded bg-gray-50 shadow-inner')
        with area_chat:
            contenedor_mensajes()

        # Input y Botón de enviar en la parte inferior
        with ui.row().classes('w-full items-center no-wrap mt-2'):
            input_texto = ui.input(placeholder='El motor se está inicializando...') \
                .classes('w-full flex-grow') \
                .props('rounded outlined') \
                .on('keydown.enter', enviar_mensaje)

            # Si el motor ya se cargó globalmente, mantenemos el campo habilitado
            if estado["listo"]:
                input_texto.enable()
                input_texto.placeholder = "Escribe tu petición sobre configuraciones 5G..."
            else:
                input_texto.disable()

            ui.button(icon='send', on_click=lambda: enviar_mensaje(types.SimpleNamespace(sender=input_texto))) \
                .props('round color="primary"')

    # Función interna acoplada de forma segura al ciclo de conexión del navegador del cliente
    async def disparar_carga():
        if estado["listo"]:
            logger.debug("Initialization already complete, skipping")
            return  # Si la base vectorial y la caché ya existen en memoria, saltamos el proceso

        logger.info("Starting initialization via client connect event")
        notificacion = ui.notification('Inicializando Motores CAG/RAG (puede tardar un poco)...', timeout=0, spinner=True)
        try:
            # Mandamos la inicialización (PDFs, Embeddings, subida de Prompt) a ejecutarse asíncronamente
            logger.info("Running heavy initialization in background thread")
            llm_provider, model_gen, model_emb, cache, bd = await run.io_bound(inicializacion_pesada)
            estado.update({"llm_provider": llm_provider, "model_gen": model_gen, "model_emb": model_emb,
                          "cache": cache, "bd": bd, "listo": True})
            logger.info("Initialization completed successfully")
            notificacion.dismiss()
            ui.notify('Motor 5G listo para operar', type='positive', position='top')

            if input_texto:
                input_texto.enable()
                input_texto.placeholder = "Escribe tu petición sobre configuraciones 5G..."
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            notificacion.dismiss()
            ui.notify(f'Error en inicialización: {e}', type='negative')

    # Vinculamos la carga pesada al evento on_connect del cliente web (así ui.notification sabe dónde dibujarse)
    ui.context.client.on_connect(disparar_carga)

# --- INICIO DEL SERVIDOR WEB ---
logger.info("Starting NiceGUI web server on port 8080")
ui.run(title='Experto 5G', port=8080)