import asyncio
import io
from datetime import date
from html import escape
from typing import Literal

import weasyprint
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from src.adapters.db.engine import AsyncSessionFactory

router = APIRouter(tags=["reports"])

_SQL = """
    SELECT
        l.id,
        l.name,
        l.kontingent,
        l.notbett_kapazitaet,
        COUNT(o.id) AS belegt,
        ss.eu_gesamtquote
    FROM capacity.locations l
    CROSS JOIN (
        SELECT COALESCE(
            (SELECT eu_gesamtquote FROM capacity.system_settings WHERE id = 1),
            0
        ) AS eu_gesamtquote
    ) ss
    LEFT JOIN capacity.rooms r ON r.location_id = l.id AND r.is_active = true
    LEFT JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true
    LEFT JOIN persons.occupants o ON o.bed_id = b.id
        AND o.belegung_start <= :period_end
        AND o.belegung_ende >= :period_start
    WHERE l.is_active = true
    GROUP BY l.id, l.name, l.kontingent, l.notbett_kapazitaet, ss.eu_gesamtquote
    ORDER BY l.name
"""

_ZEITRAUM_LABELS = {
    "monat": "Monatsbericht",
    "quartal": "Quartalsbericht",
    "jahr": "Jahresbericht",
}


def _get_period(zeitraum: str) -> tuple[date, date]:
    today = date.today()
    if zeitraum == "monat":
        return today.replace(day=1), today
    if zeitraum == "quartal":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        return today.replace(month=q_start_month, day=1), today
    return date(today.year, 1, 1), today


def _ampel_class(belegt: int, kontingent: int, notbett: int) -> str:
    if kontingent == 0 and notbett == 0:
        return "grey"
    if belegt > kontingent + notbett:
        return "red"
    if belegt >= kontingent:
        return "yellow"
    return "green"


def _build_html(rows: list, zeitraum: str, period_start: date, period_end: date) -> str:
    eu_gesamtquote = int(rows[0].eu_gesamtquote) if rows else 0
    gesamt_kontingent = sum(int(r.kontingent) for r in rows)
    gesamt_belegt = sum(int(r.belegt) for r in rows)

    row_html = ""
    for r in rows:
        belegt = int(r.belegt)
        kontingent = int(r.kontingent)
        notbett = int(r.notbett_kapazitaet)
        css = _ampel_class(belegt, kontingent, notbett)
        pct = f"{belegt * 100 / kontingent:.0f}%" if kontingent else "–"
        row_html += (
            f"<tr class='{css}'>"
            f"<td>{escape(r.name)}</td>"
            f"<td>{kontingent}</td>"
            f"<td>{notbett}</td>"
            f"<td>{belegt}</td>"
            f"<td>{pct}</td>"
            f"</tr>\n"
        )

    if eu_gesamtquote == 0:
        eu_status_class = "grey"
        eu_quota_display = "Nicht konfiguriert"
        eu_warning = "&nbsp;|&nbsp;<strong>&#9888; EU-Gesamtquote nicht gesetzt</strong>"
    else:
        eu_status_class = "red" if gesamt_kontingent > eu_gesamtquote else "green"
        eu_quota_display = str(eu_gesamtquote)
        eu_warning = (
            "&nbsp;|&nbsp;<strong>&#9888; Kontingent überschreitet EU-Quote</strong>"
            if gesamt_kontingent > eu_gesamtquote
            else ""
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 2cm; }}
  body {{ font-family: sans-serif; font-size: 11pt; color: #222; }}
  h1 {{ font-size: 16pt; color: #003366; margin-bottom: 4px; }}
  .subtitle {{ color: #555; margin-bottom: 20px; font-size: 10pt; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th {{ background: #003366; color: white; padding: 6px 8px; text-align: left; font-size: 10pt; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #ddd; font-size: 10pt; }}
  tr.green td {{ background: #e8f5e9; }}
  tr.yellow td {{ background: #fff8e1; }}
  tr.red td {{ background: #ffebee; }}
  tr.grey td {{ background: #f5f5f5; color: #888; }}
  .footer {{ margin-top: 24px; padding: 10px; border: 1px solid #ccc; font-size: 10pt; }}
  .footer.green {{ background: #e8f5e9; }}
  .footer.red {{ background: #ffebee; }}
  .footer.grey {{ background: #f5f5f5; color: #888; }}
  .label {{ font-weight: bold; }}
</style>
</head>
<body>
<h1>EU-Compliance-Report — {_ZEITRAUM_LABELS[zeitraum]}</h1>
<div class="subtitle">Zeitraum: {period_start.strftime('%d.%m.%Y')} bis {period_end.strftime('%d.%m.%Y')} &nbsp;|&nbsp; Erstellt: {date.today().strftime('%d.%m.%Y')}</div>

<table>
  <thead>
    <tr>
      <th>Einrichtung</th>
      <th>Kontingent</th>
      <th>Notbetten</th>
      <th>Belegt</th>
      <th>Auslastung</th>
    </tr>
  </thead>
  <tbody>
    {row_html if row_html else '<tr><td colspan="5" style="text-align:center;color:#888">Keine aktiven Einrichtungen</td></tr>'}
  </tbody>
</table>

<div class="footer {eu_status_class}">
  <span class="label">Gesamt-Kontingent:</span> {gesamt_kontingent} &nbsp;|&nbsp;
  <span class="label">EU-Gesamtquote:</span> {eu_quota_display} &nbsp;|&nbsp;
  <span class="label">Gesamt belegt:</span> {gesamt_belegt}
  {eu_warning}
</div>
</body>
</html>"""


@router.get("/reports/eu-compliance")
async def eu_compliance_report(
    zeitraum: Literal["monat", "quartal", "jahr"] = Query(..., description="monat | quartal | jahr"),
):
    period_start, period_end = _get_period(zeitraum)

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            text(_SQL),
            {"period_start": period_start, "period_end": period_end},
        )
        rows = result.fetchall()

    html = _build_html(rows, zeitraum, period_start, period_end)
    pdf_bytes = await asyncio.to_thread(weasyprint.HTML(string=html).write_pdf)

    filename = f"eu-compliance-{zeitraum}-{date.today()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
