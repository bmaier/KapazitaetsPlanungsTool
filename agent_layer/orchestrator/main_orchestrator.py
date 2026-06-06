import os
from ..agents.facility_agent import FacilityAgent
from ..agents.transfer_agent import TransferAgent
from ..agents.inbox_agent import InboxAgent

class MockOrchestratorAgent:
    """
    Der klassische, deterministische Mock-Orchestrator für Demos (ohne KI Kosten).
    Delegiert Anfragen an die spezialisierten Sub-Agenten (A2A Protocol).
    """
    
    def __init__(self):
        self.agents = {
            "facility": FacilityAgent(),
            "transfer": TransferAgent(),
            "inbox": InboxAgent(),
        }
        
    async def handle_message(self, message: str) -> dict:
        """
        Mock-Routing-Logik basierend auf Keyword-Matching.
        """
        msg_lower = message.lower()

        if any(w in msg_lower for w in ["suche", "verleg", "person"]):
            return await self.agents["transfer"].process_intent(message)

        if any(w in msg_lower for w in ["auslastung", "kapazität", "raum", "bett", "label", "sperr", "belegung"]):
            return await self.agents["facility"].process_intent(message)
            
        if any(w in msg_lower for w in ["postkorb", "aufgabe", "genehmig"]):
            return await self.agents["inbox"].process_intent(message)
            
        return {
            "text": "Ich bin der BorderCap Orchestrator. Wie kann ich helfen? (Frag z.B. nach 'Auslastung')"
        }

class GenAIOrchestratorAgent:
    """
    Der echte, LLM-gesteuerte Orchestrator (Zukunftsausbau).
    Nutzt Google ADK, Gemini/OpenAI und echten Context Injection.
    """
    async def handle_message(self, message: str) -> dict:
        return {
            "text": "Der echte LLM-Modus (GenAIOrchestratorAgent) ist noch nicht angebunden. Bitte wechsle zurück in den Mock-Modus (AGENT_MODE=mock)."
        }

# --- Strategy Pattern / Factory ---
AGENT_MODE = os.getenv("AGENT_MODE", "mock")

if AGENT_MODE == "real":
    orchestrator = GenAIOrchestratorAgent()
else:
    orchestrator = MockOrchestratorAgent()
