import logging
import os

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# --- Pydantic Model per Output Strutturato ---

class TelemetryAdvice(BaseModel):
    """Risposta strutturata del consulente AI."""
    advice: str = Field(description="Consiglio breve in italiano per il conducente")
    alert_level: str = Field(description="Uno tra: INFO, WARN, CRITICAL")


# --- Singleton LLM Client ---

_llm = None

def _get_llm():
    """Lazy singleton: crea il client LLM una sola volta per processo."""
    global _llm
    if _llm is None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("⚠️ GOOGLE_API_KEY non configurata. AI Advisor in modalità fallback.")
            return None
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=api_key,
            temperature=0.3,
        )
        logger.info("✅ Gemini 2.5 Flash Lite inizializzato via LangChain")
    return _llm


# --- Prompt Template ---

SYSTEM_PROMPT = """Sei un consulente AI per flotte di veicoli (EcoFleet AI Advisor).
Analizza i dati telemetrici e fornisci un consiglio breve e actionable in italiano al conducente.

Regole per alert_level:
- INFO: guida normale, ottimale, nessun problema
- WARN: comportamento da correggere (RPM troppo alti, sosta con motore acceso, carburante basso)
- CRITICAL: situazione pericolosa (velocità molto elevata, carburante quasi vuoto)"""


# --- Fallback Rule-Based ---

def _fallback_advice(speed: float, rpm: int, fuel_level: float) -> TelemetryAdvice:
    """Logica rule-based usata come fallback se Gemini non è disponibile."""
    if speed > 130:
        return TelemetryAdvice(
            advice="Stai superando i limiti. Rallenta per sicurezza e consumi.",
            alert_level="CRITICAL"
        )
    if fuel_level < 5:
        return TelemetryAdvice(
            advice="Carburante quasi esaurito! Fermati al primo distributore.",
            alert_level="CRITICAL"
        )
    if rpm > 3000:
        return TelemetryAdvice(
            advice="Giri troppo alti! Cambia marcia per risparmiare carburante.",
            alert_level="WARN"
        )
    if speed < 10 and rpm > 1000:
        return TelemetryAdvice(
            advice="Sei fermo o quasi. Spegni il motore se la sosta è lunga.",
            alert_level="WARN"
        )
    return TelemetryAdvice(
        advice="Guida ottimale. Continua così!",
        alert_level="INFO"
    )


# --- Entry Point ---

def get_ai_advice(speed: float, rpm: int, fuel_level: float) -> TelemetryAdvice:
    """Genera un consiglio AI sui dati telemetrici. Fallback a regole se Gemini non disponibile."""
    llm = _get_llm()
    if llm is None:
        return _fallback_advice(speed, rpm, fuel_level)

    try:
        structured_llm = llm.with_structured_output(TelemetryAdvice)
        user_message = (
            f"Dati telemetrici:\n"
            f"- Velocità: {speed} km/h\n"
            f"- RPM: {rpm}\n"
            f"- Livello carburante: {fuel_level}%"
        )
        result = structured_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])
        logger.info(f"🤖 Gemini advice: {result.advice} [{result.alert_level}]")
        return result

    except Exception as e:
        logger.error(f"❌ Gemini call failed, using fallback: {e}")
        return _fallback_advice(speed, rpm, fuel_level)
