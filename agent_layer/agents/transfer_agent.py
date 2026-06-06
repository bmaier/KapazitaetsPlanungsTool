from ..skills.transfer_workflow import TransferWorkflowSkill

class TransferAgent:
    """
    Spezialisierter Agent für Personenverlegungen und Platzsuche (Suggestion Wizard).
    """
    
    def __init__(self):
        self.name = "TransferAgent"
        self.role = "Verantwortlich für die optimale Zuweisung von Personen zu freien Betten."
        self.skills = [TransferWorkflowSkill()]
        
    async def process_intent(self, user_intent: str) -> dict:
        """
        Determines which skill to use based on the intent forwarded by the Orchestrator.
        """
        intent_lower = user_intent.lower()
        
        if "suche" in intent_lower or "verleg" in intent_lower or "person" in intent_lower:
            skill = self.skills[0]
            
            # Simple mock to extract name for BDD
            person_name = "Max Mustermann"
            if " für " in intent_lower:
                parts = intent_lower.split(" für ")
                person_name = parts[1].title()
                
            semantic_payload = await skill.execute({"person_name": person_name}, None)
            return {
                "text": f"Ich habe den Suggestion-Wizard für {person_name} gestartet. Hier sind die besten Vorschläge:",
                "a2ui_widget": "SuggestionWizardWidget",
                "semantic_payload": semantic_payload
            }
        
        return {"text": "Der Transfer-Agent hat diese Anfrage nicht verstanden."}
