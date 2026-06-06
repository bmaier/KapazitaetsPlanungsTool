from typing import Dict, Any

class BedStatusSkill:
    """
    Skill for visualizing the detailed room and bed occupancy.
    """
    
    name = "BedStatusSkill"
    description = "Zeigt die detaillierte Raum- und Bettenbelegung graphisch an."
    
    async def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Executes the skill to return detailed bed status data.
        """
        # Semantic A2UI JSON-LD representation of the Bed Status
        result_data = {
            "@context": "http://bordercap.eu/schema/bcc_context.jsonld",
            "@type": "BedStatusWidget",
            "schema:name": "Bettenstatus & Raumbelegung: Erstaufnahmeeinrichtung",
            "bcc:rooms": [
                {
                    "@type": "Room",
                    "schema:name": "Raum A",
                    "bcc:roomType": "Männer",
                    "bcc:totalBeds": 3,
                    "bcc:occupiedBeds": 2,
                    "bcc:isFullyOccupied": False,
                    "bcc:beds": [
                        {"@type": "Bed", "schema:name": "Bett 01", "bcc:status": "BELEGT"},
                        {"@type": "Bed", "schema:name": "Bett 02", "bcc:status": "BELEGT"},
                        {"@type": "Bed", "schema:name": "Bett 03", "bcc:status": "FREI"}
                    ]
                },
                {
                    "@type": "Room",
                    "schema:name": "Raum B",
                    "bcc:roomType": "Familie",
                    "bcc:totalBeds": 2,
                    "bcc:occupiedBeds": 2,
                    "bcc:isFullyOccupied": True,
                    "bcc:beds": [
                        {"@type": "Bed", "schema:name": "Bett 04", "bcc:status": "BELEGT"},
                        {"@type": "Bed", "schema:name": "Bett 05", "bcc:status": "BELEGT"}
                    ]
                },
                {
                    "@type": "Room",
                    "schema:name": "Raum C",
                    "bcc:roomType": "Gemischt",
                    "bcc:totalBeds": 4,
                    "bcc:occupiedBeds": 0,
                    "bcc:isFullyOccupied": False,
                    "bcc:beds": [
                        {"@type": "Bed", "schema:name": "Bett 06", "bcc:status": "FREI"},
                        {"@type": "Bed", "schema:name": "Bett 07", "bcc:status": "FREI"},
                        {"@type": "Bed", "schema:name": "Bett 08", "bcc:status": "GESPERRT"},
                        {"@type": "Bed", "schema:name": "Bett 09", "bcc:status": "FREI"}
                    ]
                }
            ]
        }
            
        return result_data
