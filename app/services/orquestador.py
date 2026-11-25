import json

from pydantic import ValidationError

from app.schemas.chat import ChatSalida, HerramientaUsada
from app.schemas.prestamo import PrestamoEntrada
from app.services.modelo import predecir

NOMBRE_TOOL = "calcular_riesgo_impago"
MAX_VUELTAS = 4

SISTEMA = (
    "Eres un asistente de riesgo de un banco. Cuando tengas todos los datos de una solicitud de "
    "prestamo, llama a la herramienta calcular_riesgo_impago. Si falta algun dato, pidelo. "
    "Nunca inventes valores. Responde en espanol y de forma breve."
)


def leer_argumentos(texto):
    """YA HECHO: convierte el texto JSON de la tool en dict ({} si no es JSON valido)."""
    try:
        datos = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return {}
    if isinstance(datos, dict):
        return datos
    return {}


def definir_tool():
    return {
        "type": "function",
        "function": {
            "name": NOMBRE_TOOL,
            "description": "Calcula la probabilidad de impago de un prestamo y la decision "
            "(aprobar, revisar o rechazar) a partir de los datos de la solicitud.",
            "parameters": PrestamoEntrada.model_json_schema(),
        },
    }


def ejecutar_tool(nombre, argumentos_json):
    if nombre != NOMBRE_TOOL:
        return {"ok": False, "error": "Herramienta desconocida: " + str(nombre)}
    argumentos = leer_argumentos(argumentos_json)
    if not argumentos:
        return {"ok": False, "error": "Argumentos vacios o JSON invalido"}
    try:
        entrada = PrestamoEntrada(**argumentos)
    except ValidationError as e:
        errores = [
            ".".join(str(x) for x in err["loc"]) + ": " + err["msg"]
            for err in e.errors()
        ]
        return {"ok": False, "error": "; ".join(errores)}
    salida = predecir(entrada)
    return {"ok": True, **salida.model_dump()}


def responder(mensajes, llm):
    historial = [{"role": "system", "content": SISTEMA}]
    for m in mensajes:
        historial.append({"role": m.role, "content": m.content})
    herramientas = [definir_tool()]
    usada = None

    for _ in range(MAX_VUELTAS):
        respuesta = llm.completar(historial, herramientas)
        llamadas = respuesta.get("tool_calls")
        if not llamadas:
            return ChatSalida(
                respuesta=respuesta.get("content") or "", herramienta=usada
            )

        historial.append(respuesta)
        for llamada in llamadas:
            funcion = llamada["function"]
            resultado = ejecutar_tool(funcion["name"], funcion["arguments"])
            usada = HerramientaUsada(
                nombre=funcion["name"],
                argumentos=leer_argumentos(funcion["arguments"]),
                resultado=resultado,
            )
            historial.append(
                {
                    "role": "tool",
                    "tool_call_id": llamada["id"],
                    "content": json.dumps(resultado),
                }
            )

    return ChatSalida(
        respuesta="No he podido completar el calculo con los datos proporcionados. "
        "Revisa los datos e intentalo de nuevo.",
        herramienta=usada,
    )
