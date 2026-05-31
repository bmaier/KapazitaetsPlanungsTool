from pydantic import BaseModel, ConfigDict


class OccupancyDataPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    belegt: int
    frei: int
    notbetten_belegt: int
    kontingent: int
    belegungsgrad_pct: float


class KpiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    aktuell_pct: float
    avg30t_pct: float
    trend_delta_pct: float


class StatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    data: list[OccupancyDataPoint]
    kpis: KpiResponse
