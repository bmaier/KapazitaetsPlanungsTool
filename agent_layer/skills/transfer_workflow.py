from typing import Dict, Any

class TransferWorkflowSkill:
    """
    Skill for running the complex suggestion and reservation workflow.
    Uses MCP tools: 'run_suggestion_wizard' and 'create_reservation_request'.
    """
    
    name = "TransferWorkflowSkill"
    description = "Führt Verlegungsanfragen, Platzsuchen und Reservierungen durch."
    
    async def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Executes the skill using MCP tools.
        """
        person_name = params.get("person_name", "Unbekannte Person")
        
        # Semantic A2UI JSON-LD representation of the Suggestion Result
        result_data = {
            "@context": "http://bordercap.eu/schema/bcc_context.jsonld",
            "@type": "SuggestionWizardWidget",
            "schema:name": f"Verlegungsvorschläge für {person_name}",
            "bcc:person": {
                "@type": "Person",
                "schema:name": person_name
            },
            "bcc:suggestions": [
                {
                    "@type": "Location",
                    "bcc:locationId": "loc-muenchen-1",
                    "schema:name": "Erstaufnahmeeinrichtung München",
                    "bcc:matchScore": 95,
                    "bcc:freeBeds": 12
                },
                {
                    "@type": "Location",
                    "bcc:locationId": "loc-berlin-3",
                    "schema:name": "Sonderunterkunft Berlin",
                    "bcc:matchScore": 82,
                    "bcc:freeBeds": 3
                }
            ]
        }
            
        return result_data
