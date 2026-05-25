import html as html_module

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import text

from src.adapters.db.engine import AsyncSessionFactory

router = APIRouter(tags=["map"])

LOCATION_COORDS = {
    "Frankfurt": (8.68, 50.11),
    "München": (11.58, 48.14),
    "Passau": (13.46, 48.57),
    "Hamburg": (10.00, 53.55),
}

AMPEL_COLORS = [
    (90.0, "#f44336"),
    (70.0, "#ff9800"),
    (0.0, "#4caf50"),
]


def ampel_color(pct: float) -> str:
    for threshold, color in AMPEL_COLORS:
        if pct >= threshold:
            return color
    return "#4caf50"  # noqa: RET504 — safety fallback for negative pct


def to_svg_coords(lon: float, lat: float) -> tuple[float, float]:
    x = (lon - 5.9) / (15.0 - 5.9) * 700 + 50
    y = (55.1 - lat) / (55.1 - 47.3) * 500 + 50
    return round(x, 1), round(y, 1)


@router.get("/map/svg")
async def get_map_svg():
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("""
            SELECT l.id, l.name, l.kontingent, l.is_active,
                CASE WHEN l.kontingent > 0 THEN
                    LEAST(COUNT(o.id) FILTER (WHERE o.belegung_ende IS NULL OR o.belegung_ende > NOW()) * 100.0 / l.kontingent, 100.0)
                ELSE 0.0 END AS belegungsgrad_pct
            FROM capacity.locations l
            LEFT JOIN capacity.rooms r ON r.location_id = l.id AND r.is_active = true
            LEFT JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true
            LEFT JOIN persons.occupants o ON o.bed_id = b.id
            WHERE l.is_active = true
            GROUP BY l.id, l.name, l.kontingent, l.is_active
            ORDER BY l.name
        """))
        rows = result.fetchall()

    circles = []
    for row in rows:
        name = html_module.escape(str(row.name))
        pct = float(row.belegungsgrad_pct)
        lon, lat = LOCATION_COORDS.get(row.name, (10.4, 51.1))
        cx, cy = to_svg_coords(lon, lat)
        color = ampel_color(pct)
        circles.append(f'''
  <circle cx="{cx}" cy="{cy}" r="18" fill="{color}" fill-opacity="0.85" stroke="white" stroke-width="2"/>
  <text x="{cx}" y="{cy - 24}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#333">{name}</text>
  <text x="{cx}" y="{cy + 34}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#555">{pct:.1f}%</text>''')

    circles_svg = "\n".join(circles)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
  <rect width="800" height="600" fill="#e8ecef"/>
  <text x="400" y="30" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#003366" font-weight="bold">Kapazitätskarte (Schematisch)</text>
{circles_svg}
</svg>'''

    return Response(content=svg, media_type="image/svg+xml")
