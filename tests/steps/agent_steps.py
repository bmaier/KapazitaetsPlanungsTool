"""
Behave step definitions for @agent feature files.
These tests are standalone — no Keycloak or DB required.
"""
import asyncio
import sys
import os

# Ensure agent_layer is importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from behave import given, when, then
from agent_layer.orchestrator.main_orchestrator import MockOrchestratorAgent


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given('der MCP-Server ist mit der FastAPI verbunden')
def step_mcp_server_connected(context):
    context.orchestrator = MockOrchestratorAgent()
    context.agent_response = None
    context.called_tools = []


@given('der "{skill_name}" Agent ist initialisiert')
def step_agent_initialized(context, skill_name):
    pass  # Orchestrator already initializes all sub-agents in before step


@given('der "{skill_name}" ist im "{agent_name}" initialisiert')
def step_skill_in_agent_initialized(context, skill_name, agent_name):
    pass  # Covered by MockOrchestratorAgent constructor


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when('der Benutzer im Chat schreibt: "{message}"')
def step_user_writes(context, message):
    context.user_message = message
    context.agent_response = _run(context.orchestrator.handle_message(message))


@when('der Benutzer im Chat fragt: "{message}"')
def step_user_asks(context, message):
    context.user_message = message
    context.agent_response = _run(context.orchestrator.handle_message(message))


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then('sollte der Agent das MCP-Tool "{tool_name}" aufrufen')
def step_mcp_tool_called(context, tool_name):
    # The mock agents route to skills that represent MCP tool calls.
    # We verify the response is consistent with the expected tool's output domain.
    TOOL_TO_WIDGET = {
        "get_locations_summary": "LocationSummaryWidget",
        "update_room_labels": "LabelChipsWidget",
        "deactivate_bed": "LabelChipsWidget",
        "run_suggestion_wizard": "SuggestionWizardWidget",
        "create_reservation_request": "SuggestionWizardWidget",
        "get_inbox_tasks": "TaskInboxWidget",
        "resolve_task": "TaskInboxWidget",
    }
    expected_widget = TOOL_TO_WIDGET.get(tool_name)
    assert context.agent_response is not None, "Kein Agent-Response vorhanden"
    assert "a2ui_widget" in context.agent_response, (
        f"Response enthält kein 'a2ui_widget': {context.agent_response}"
    )
    if expected_widget:
        actual_widget = context.agent_response.get("a2ui_widget")
        assert actual_widget == expected_widget, (
            f"MCP-Tool '{tool_name}' erwartet Widget '{expected_widget}', "
            f"aber '{actual_widget}' wurde zurückgegeben"
        )


@then('die Antwort sollte als semantisches A2UI-Widget "{widget_name}" formatiert sein')
def step_widget_type(context, widget_name):
    actual = context.agent_response.get("a2ui_widget")
    assert actual == widget_name, (
        f"Erwartet A2UI-Widget '{widget_name}', erhalten: '{actual}'"
    )


@then('der JSON-LD Payload sollte den "@type" "{type_value:w}" enthalten')
def step_jsonld_type(context, type_value):
    payload = context.agent_response.get("semantic_payload", {})
    assert payload, "Kein semantic_payload im Response"
    found = _find_value_in_dict(payload, "@type", type_value)
    assert found, (
        f"JSON-LD @type '{type_value}' nicht im Payload gefunden.\nPayload: {payload}"
    )


@then('der JSON-LD Payload sollte den "@type" "{type_value}" und die neuen "bcc:labels" enthalten')
def step_jsonld_type_and_labels(context, type_value):
    payload = context.agent_response.get("semantic_payload", {})
    assert payload, "Kein semantic_payload im Response"
    found_type = _find_value_in_dict(payload, "@type", type_value)
    assert found_type, (
        f"JSON-LD @type '{type_value}' nicht im Payload gefunden.\nPayload: {payload}"
    )
    found_labels = _find_key_in_dict(payload, "bcc:labels")
    assert found_labels, (
        f"'bcc:labels' nicht im Payload gefunden.\nPayload: {payload}"
    )


@then('die "{field_name}" sollte validiert im SHACL-Shape enthalten sein')
def step_shacl_field_present(context, field_name):
    payload = context.agent_response.get("semantic_payload", {})
    found = _find_key_in_dict(payload, field_name)
    assert found, (
        f"SHACL-relevantes Feld '{field_name}' nicht im Payload.\nPayload: {payload}"
    )


@then('die Änderungen sollten durch SHACL Constraints validiert werden')
def step_shacl_validated(context):
    payload = context.agent_response.get("semantic_payload", {})
    assert payload.get("bcc:status") == "ERFOLGREICH", (
        f"Erwarte bcc:status='ERFOLGREICH' als SHACL-Erfolgsindikator.\nPayload: {payload}"
    )


@then('der JSON-LD Payload sollte eine Liste der offenen Tasks (z. B. Reservierungsanfragen) enthalten')
def step_jsonld_task_list(context):
    payload = context.agent_response.get("semantic_payload", {})
    tasks = payload.get("bcc:tasks", [])
    assert len(tasks) > 0, f"Keine Tasks im Payload gefunden.\nPayload: {payload}"
    open_tasks = [t for t in tasks if t.get("bcc:status") == "OPEN"]
    assert len(open_tasks) > 0, (
        f"Keine offenen Tasks (bcc:status=OPEN) gefunden.\nTasks: {tasks}"
    )


@then('der Benutzer kann interaktiv auf "Genehmigen" klicken, was das MCP Tool "resolve_task" triggert')
def step_resolve_task_available(context):
    payload = context.agent_response.get("semantic_payload", {})
    tasks = payload.get("bcc:tasks", [])
    open_tasks = [t for t in tasks if t.get("bcc:status") == "OPEN"]
    assert len(open_tasks) > 0, (
        "Es gibt keine offenen Tasks — 'Genehmigen'-Aktion nicht verfügbar"
    )
    for task in open_tasks:
        assert "bcc:taskId" in task, (
            f"Task hat keine 'bcc:taskId' — resolve_task kann nicht aufgerufen werden: {task}"
        )


@then('der JSON-LD Payload sollte den Vorschlag inklusive Ziel-Einrichtung enthalten')
def step_jsonld_suggestion_with_location(context):
    payload = context.agent_response.get("semantic_payload", {})
    suggestions = payload.get("bcc:suggestions", [])
    assert len(suggestions) > 0, f"Keine Vorschläge im Payload.\nPayload: {payload}"
    for suggestion in suggestions:
        assert "schema:name" in suggestion, (
            f"Vorschlag ohne 'schema:name'.\nVorschlag: {suggestion}"
        )
        assert "bcc:locationId" in suggestion, (
            f"Vorschlag ohne 'bcc:locationId' — Ziel-Einrichtung fehlt.\nVorschlag: {suggestion}"
        )


@then(
    'der User hat im Frontend die Möglichkeit, die Reservierung interaktiv '
    '(MCP Tool "create_reservation_request") zu bestätigen'
)
def step_reservation_confirmable(context):
    payload = context.agent_response.get("semantic_payload", {})
    suggestions = payload.get("bcc:suggestions", [])
    assert len(suggestions) > 0, "Keine Vorschläge vorhanden — Reservierung kann nicht bestätigt werden"
    for s in suggestions:
        assert "bcc:locationId" in s, (
            f"Vorschlag ohne 'bcc:locationId' — create_reservation_request wäre nicht aufrufbar: {s}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_value_in_dict(d, key, value):
    """Rekursiv nach key=value in einem verschachtelten Dict/List suchen."""
    if isinstance(d, dict):
        if d.get(key) == value:
            return True
        return any(_find_value_in_dict(v, key, value) for v in d.values())
    if isinstance(d, list):
        return any(_find_value_in_dict(item, key, value) for item in d)
    return False


def _find_key_in_dict(d, key):
    """Rekursiv prüfen, ob ein Key irgendwo im Dict vorhanden ist."""
    if isinstance(d, dict):
        if key in d:
            return True
        return any(_find_key_in_dict(v, key) for v in d.values())
    if isinstance(d, list):
        return any(_find_key_in_dict(item, key) for item in d)
    return False
