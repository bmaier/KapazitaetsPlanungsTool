from ..skills.task_resolution import TaskResolutionSkill

class InboxAgent:
    """
    Spezialisierter Agent für das Task-Management (Postkorb).
    """
    
    def __init__(self):
        self.name = "InboxAgent"
        self.role = "Verantwortlich für das Anzeigen und Genehmigen von offenen Aufgaben im Postkorb."
        self.skills = [TaskResolutionSkill()]
        
    async def process_intent(self, user_intent: str) -> dict:
        """
        Determines which skill to use based on the intent forwarded by the Orchestrator.
        """
        intent_lower = user_intent.lower()
        
        if "postkorb" in intent_lower or "aufgabe" in intent_lower or "genehmig" in intent_lower:
            skill = self.skills[0]
            semantic_payload = await skill.execute({}, None)
            return {
                "text": "Hier ist dein aktueller Postkorb. Du kannst Aufgaben direkt hier genehmigen:",
                "a2ui_widget": "TaskInboxWidget",
                "semantic_payload": semantic_payload
            }
        
        return {"text": "Der Inbox-Agent hat diese Anfrage nicht verstanden."}
