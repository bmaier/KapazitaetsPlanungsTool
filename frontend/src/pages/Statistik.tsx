import { useEffect, useState, useCallback } from 'react'
import {
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CircularProgress,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat'
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'

interface DataPoint {
  date: string
  belegt: number
  frei: number
  notbetten_belegt: number
  kontingent: number
  belegungsgrad_pct: number
}

interface KpiData {
  aktuell_pct: number
  avg30t_pct: number
  trend_delta_pct: number
}

interface LocationOption {
  id: string
  name: string
}

type Granularity = 'day' | 'week' | 'month'

function autoGranularity(from: string, to: string): Granularity {
  const days = (new Date(to).getTime() - new Date(from).getTime()) / 86400000
  if (days <= 60) return 'day'
  if (days <= 180) return 'week'
  return 'month'
}

function offsetDate(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export default function Statistik() {
  const { keycloak, locationId: myLocationId } = useKeycloak()
  const { get } = useApiClient()

  const tokenParsed = keycloak?.tokenParsed as Record<string, unknown> | undefined
  const roles = ((tokenParsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [])
  const isAdmin = roles.includes('system-admin')

  const [locations, setLocations] = useState<LocationOption[]>([])
  const [selectedLocation, setSelectedLocation] = useState<string>(myLocationId ?? '')
  const [dateFrom, setDateFrom] = useState(offsetDate(-30))
  const [dateTo, setDateTo] = useState(offsetDate(0))
  const [data, setData] = useState<DataPoint[]>([])
  const [kpis, setKpis] = useState<KpiData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Einrichtungen für system-admin laden
  useEffect(() => {
    if (!isAdmin) return
    get<LocationOption[]>('/api/locations').then(setLocations).catch(() => {})
  }, [isAdmin, get])

  // Effektive location_id
  const effectiveLocation = isAdmin ? selectedLocation : (myLocationId ?? '')

  const load = useCallback(() => {
    if (!effectiveLocation || !dateFrom || !dateTo) return
    if (dateFrom > dateTo) {
      setError('Von-Datum muss vor Bis-Datum liegen.')
      return
    }
    setError('')
    setLoading(true)
    const granularity = autoGranularity(dateFrom, dateTo)
    get<{ data: DataPoint[]; kpis: KpiData }>(
      `/api/statistics/occupancy?location_id=${effectiveLocation}&date_from=${dateFrom}&date_to=${dateTo}&granularity=${granularity}`
    )
      .then((res) => {
        setData(res.data)
        setKpis(res.kpis)
      })
      .catch(() => setError('Statistik konnte nicht geladen werden.'))
      .finally(() => setLoading(false))
  }, [effectiveLocation, dateFrom, dateTo, get])

  useEffect(() => { load() }, [load])

  function applyShortcut(days: number) {
    setDateFrom(offsetDate(-days))
    setDateTo(offsetDate(0))
  }

  function TrendIcon({ delta }: { delta: number }) {
    if (delta > 1) return <TrendingUpIcon sx={{ color: '#c62828', verticalAlign: 'middle' }} />
    if (delta < -1) return <TrendingDownIcon sx={{ color: '#2e7d32', verticalAlign: 'middle' }} />
    return <TrendingFlatIcon sx={{ color: '#888', verticalAlign: 'middle' }} />
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} mb={3}>
        Belegungs­statistik
      </Typography>

      {/* Filter-Leiste */}
      <Paper elevation={0} sx={{ p: 2, mb: 3, borderRadius: 2, border: '1px solid #e0e0e0' }}>
        <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
          {isAdmin && (
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel>Einrichtung</InputLabel>
              <Select
                value={selectedLocation}
                label="Einrichtung"
                onChange={(e) => setSelectedLocation(e.target.value)}
              >
                {locations.map((l) => (
                  <MenuItem key={l.id} value={l.id}>{l.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <TextField
            label="Von"
            type="date"
            size="small"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="Bis"
            type="date"
            size="small"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            InputLabelProps={{ shrink: true }}
          />

          <ButtonGroup size="small" variant="outlined">
            <Button onClick={() => applyShortcut(7)}>7T</Button>
            <Button onClick={() => applyShortcut(30)}>30T</Button>
            <Button onClick={() => applyShortcut(90)}>3M</Button>
            <Button onClick={() => applyShortcut(365)}>1J</Button>
          </ButtonGroup>
        </Box>
        {error && (
          <Typography color="error" variant="caption" mt={1} display="block">{error}</Typography>
        )}
      </Paper>

      {/* KPI-Cards */}
      {kpis && (
        <Box display="flex" gap={2} mb={3} flexWrap="wrap">
          {[
            { label: 'Aktuell', value: `${kpis.aktuell_pct.toFixed(1)} %`, sub: 'Aktuelle Auslastung' },
            { label: 'Ø 30 Tage', value: `${kpis.avg30t_pct.toFixed(1)} %`, sub: 'Durchschnitt letzte 30 Tage' },
            {
              label: 'Trend',
              value: (
                <Box display="flex" alignItems="center" gap={0.5}>
                  <TrendIcon delta={kpis.trend_delta_pct} />
                  <span>{kpis.trend_delta_pct > 0 ? '+' : ''}{kpis.trend_delta_pct.toFixed(1)} PP</span>
                </Box>
              ),
              sub: 'Veränderung im Zeitraum',
            },
          ].map(({ label, value, sub }) => (
            <Card key={label} elevation={1} sx={{ flex: '1 1 160px', minWidth: 140 }}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
                <Typography variant="h5" fontWeight={700} mt={0.5}>{value}</Typography>
                <Typography variant="caption" color="text.secondary">{sub}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Chart */}
      <Paper elevation={1} sx={{ p: 3, borderRadius: 2 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : data.length === 0 ? (
          <Typography color="text.secondary" textAlign="center" py={6}>
            Keine Daten für den gewählten Zeitraum.
          </Typography>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <RTooltip
                formatter={(value: number, name: string) => {
                  const labels: Record<string, string> = {
                    belegungsgrad_pct: 'Auslastung',
                    notbetten_belegt: 'Notbetten belegt',
                  }
                  const unit = name === 'notbetten_belegt' ? '' : ' %'
                  return [`${value}${unit}`, labels[name] ?? name]
                }}
                labelFormatter={(l: string) => `Datum: ${l}`}
              />
              <Legend
                formatter={(value: string) => {
                  const map: Record<string, string> = {
                    belegungsgrad_pct: 'Belegungsgrad %',
                    notbetten_belegt: 'Notbetten belegt',
                  }
                  return map[value] ?? value
                }}
              />
              <Line
                type="monotone"
                dataKey="belegungsgrad_pct"
                stroke="#003366"
                dot={false}
                strokeWidth={2}
                name="belegungsgrad_pct"
              />
              <Bar
                dataKey="notbetten_belegt"
                fill="#ff9800"
                opacity={0.4}
                name="notbetten_belegt"
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </Paper>
    </Container>
  )
}
