# from google_antigravity import Agent
from ..skills.location_analyzer import LocationAnalyzerSkill
from ..skills.capacity_manager import CapacityManagerSkill
from ..skills.bed_status import BedStatusSkill

class FacilityAgent:
    """
    Spezialisierter Agent für Einrichtungs- und Bettenpflege.
    """
    
    def __init__(self):
        self.name = "FacilityAgent"
        self.role = "Verantwortlich für die Beauskunftung und Verwaltung von Einrichtungs-Kapazitäten."
        self.skills = [LocationAnalyzerSkill(), CapacityManagerSkill(), BedStatusSkill()]
        
    async def process_intent(self, user_intent: str) -> dict:
        """
        Determines which skill to use based on the intent forwarded by the Orchestrator.
        """
        intent_lower = user_intent.lower()
        
        if "auslastung" in intent_lower or "status" in intent_lower:
            skill = self.skills[0]
            semantic_payload = await skill.execute({}, None)
            return {
                "text": "Hier ist die aktuelle Auslastung der Einrichtungen:",
                "a2ui_widget": "LocationSummaryWidget",
                "semantic_payload": semantic_payload
            }
            
        if "belegung" in intent_lower:
            skill = self.skills[2]
            semantic_payload = await skill.execute({}, None)
            return {
                "text": "Hier ist die detaillierte Raum- und Bettenbelegung:",
                "a2ui_widget": "BedStatusWidget",
                "semantic_payload": semantic_payload
            }
            
        if "label" in intent_lower or "raum" in intent_lower or "bett" in intent_lower or "sperr" in intent_lower:
            skill = self.skills[1]
            action = "update_room" if "raum" in intent_lower else "deactivate_bed"
            semantic_payload = await skill.execute({"action": action}, None)
            return {
                "text": "Ich habe die Änderung im System via MCP-Tool durchgeführt.",
                "a2ui_widget": "LabelChipsWidget",
                "semantic_payload": semantic_payload
            }
        
        return {"text": "Das habe ich leider nicht verstanden."}
