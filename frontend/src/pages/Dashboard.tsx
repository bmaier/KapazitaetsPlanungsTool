import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Paper,
  Snackbar,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import WarningIcon from '@mui/icons-material/Warning'
import ErrorIcon from '@mui/icons-material/Error'
import GridViewIcon from '@mui/icons-material/GridView'
import MapIcon from '@mui/icons-material/Map'
import AddIcon from '@mui/icons-material/Add'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import { useKeycloak } from '../auth/KeycloakProvider'
import { useApiClient } from '../api/client'
import type { SvgIconComponent } from '@mui/icons-material'
import MapView from '../components/MapView'

interface LocationSummary {
  id: string
  name: string
  kontingent: number
  notbett_kapazitaet: number
  belegt: number
  belegungsgrad_pct: number
  is_active: boolean
}

interface Reservation {
  id: string
  requester_location_id: string
  target_location_id: string
  azr_id: string
  status: string
}

type AmpelStatus = 'GRUEN' | 'GELB' | 'ROT'

function getAmpel(pct: number): AmpelStatus {
  if (pct >= 90) return 'ROT'
  if (pct >= 70) return 'GELB'
  return 'GRUEN'
}

const AMPEL_CONFIG: Record<AmpelStatus, { color: string; bgColor: string; Icon: SvgIconComponent; label: string }> = {
  GRUEN: { color: '#1b5e20', bgColor: '#e8f5e9', Icon: CheckCircleIcon, label: 'Grün — Kapazität verfügbar' },
  GELB:  { color: '#e65100', bgColor: '#fff3e0', Icon: WarningIcon,     label: 'Gelb — Kapazität begrenzt' },
  ROT:   { color: '#b71c1c', bgColor: '#ffebee', Icon: ErrorIcon,        label: 'Rot — Kapazität kritisch' },
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: '#e65100', CONFIRMED: '#1b5e20', REJECTED: '#b71c1c', CANCELLED: '#757575', TRANSFERRED: '#1565c0',
}
const STATUS_LABELS: Record<string, string> = {
  PENDING: 'Ausstehend', CONFIRMED: 'Bestätigt', REJECTED: 'Abgelehnt', CANCELLED: 'Storniert', TRANSFERRED: 'Verlegt',
}

export default function Dashboard() {
  const { locationId, keycloak, initialized } = useKeycloak()
  const { get, post } = useApiClient()
  const navigate = useNavigate()
  const [locations, setLocations] = useState<LocationSummary[]>([])
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [loading, setLoading] = useState(true)
  const [errorOpen, setErrorOpen] = useState(false)
  const [warnOpen, setWarnOpen] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'map'>('map')

  // Neue Einrichtung Dialog
  const [newLocOpen, setNewLocOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newAdresse, setNewAdresse] = useState('')
  const [newKontingent, setNewKontingent] = useState('10')
  const [newNotbett, setNewNotbett] = useState('0')
  const [newLocSaving, setNewLocSaving] = useState(false)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' })

  const roles = ((keycloak?.tokenParsed as Record<string, unknown>)?.realm_access as { roles?: string[] } | undefined)?.roles ?? []
  const isAdmin = roles.some((r) => ['system-admin', 'location-admin'].includes(r))

  useEffect(() => {
    if (initialized && !locationId) setWarnOpen(true)
  }, [initialized, locationId])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [data, resData] = await Promise.all([
        get<LocationSummary[]>('/api/locations/summary'),
        get<Reservation[]>('/api/reservations').catch(() => [] as Reservation[]),
      ])
      const sorted = [...data].sort((a, b) => {
        if (a.id === locationId) return -1
        if (b.id === locationId) return 1
        return a.name.localeCompare(b.name, 'de')
      })
      setLocations(sorted)
      setReservations(resData)
    } catch {
      setErrorOpen(true)
    } finally {
      setLoading(false)
    }
  }, [get, locationId])

  useEffect(() => { loadData() }, [loadData])

  const myReservations = reservations.filter(
    (r) => r.requester_location_id === locationId || r.target_location_id === locationId
  ).slice(0, 5)

  async function handleCreateLocation() {
    setNewLocSaving(true)
    try {
      await post('/api/locations', {
        name: newName,
        adresse: newAdresse,
        kontingent: Number(newKontingent),
        notbett_kapazitaet: Number(newNotbett),
      })
      setNewLocOpen(false)
      setNewName(''); setNewAdresse(''); setNewKontingent('10'); setNewNotbett('0')
      setSnackbar({ open: true, message: 'Einrichtung angelegt.', severity: 'success' })
      loadData()
    } catch {
      setSnackbar({ open: true, message: 'Anlegen fehlgeschlagen.', severity: 'error' })
    } finally {
      setNewLocSaving(false)
    }
  }

  if (loading) {
    return <Box display="flex" justifyContent="center" mt={8}><CircularProgress /></Box>
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2} flexWrap="wrap" gap={1}>
        <Typography variant="h4" sx={{ color: '#003366', fontWeight: 700 }}>
          Kapazitätsübersicht
        </Typography>
        <Box display="flex" gap={1} alignItems="center">
          {isAdmin && (
            <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={() => setNewLocOpen(true)}>
              Neue Einrichtung
            </Button>
          )}
          <ToggleButtonGroup value={viewMode} exclusive
            onChange={(_e, val) => { if (val !== null) setViewMode(val) }}
            aria-label="Ansicht wählen" size="small">
            <ToggleButton value="grid" aria-label="Rasteransicht"><GridViewIcon /></ToggleButton>
            <ToggleButton value="map" aria-label="Kartenansicht"><MapIcon /></ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      {/* Meine Reservierungen (Schnellzugriff) */}
      {myReservations.length > 0 && (
        <Paper elevation={0} sx={{ p: 2, mb: 2.5, borderRadius: 2, border: '1px solid #e0e0e0' }}>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
            <Box display="flex" alignItems="center" gap={1}>
              <SwapHorizIcon sx={{ color: '#003366', fontSize: 20 }} />
              <Typography fontWeight={700} variant="body2" color="#003366">Meine Reservierungen</Typography>
            </Box>
            <Button size="small" onClick={() => navigate('/reservations')}>Alle anzeigen →</Button>
          </Box>
          <Box display="flex" gap={1.5} flexWrap="wrap">
            {myReservations.map((r) => {
              const isIncoming = r.target_location_id === locationId
              const statusColor = STATUS_COLORS[r.status] ?? '#555'
              return (
                <Chip
                  key={r.id}
                  label={
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <Typography variant="caption" fontFamily="monospace" fontWeight={700}>
                        {r.azr_id}
                      </Typography>
                      <Typography variant="caption" sx={{ opacity: 0.8 }}>
                        {isIncoming ? '← eingehend' : '→ ausgehend'}
                      </Typography>
                      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: statusColor }} />
                    </Box>
                  }
                  onClick={() => navigate('/reservations')}
                  size="small"
                  sx={{ bgcolor: statusColor + '15', cursor: 'pointer', height: 26 }}
                  title={STATUS_LABELS[r.status] ?? r.status}
                />
              )
            })}
          </Box>
        </Paper>
      )}

      {/* Grid-Ansicht */}
      <Box sx={{ display: viewMode === 'grid' ? 'block' : 'none' }}>
        <Grid container spacing={3}>
          {locations.map((loc) => {
            const ampel = getAmpel(loc.belegungsgrad_pct)
            const cfg = AMPEL_CONFIG[ampel]
            const isOwn = loc.id === locationId
            return (
              <Grid item xs={12} sm={6} md={4} key={loc.id}>
                <Card elevation={isOwn ? 6 : 2} sx={{ border: isOwn ? '2px solid #003366' : 'none', backgroundColor: cfg.bgColor }}>
                  <CardActionArea onClick={() => navigate(`/locations/${loc.id}`)}>
                    <CardContent>
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        <cfg.Icon sx={{ color: cfg.color, fontSize: 32 }} aria-hidden="true" />
                        <Typography variant="h6" sx={{ color: '#003366', fontWeight: 600 }}>
                          {loc.name}
                          {isOwn && <Typography component="span" variant="caption" sx={{ ml: 1, color: '#003366' }}>(Meine)</Typography>}
                        </Typography>
                      </Box>
                      <Box display="flex" gap={2} mt={1}>
                        <Box>
                          <Typography variant="caption" color="text.secondary">Auslastung</Typography>
                          <Typography fontWeight={700} sx={{ color: cfg.color }}>{loc.belegungsgrad_pct.toFixed(1)}%</Typography>
                        </Box>
                        <Divider orientation="vertical" flexItem />
                        <Box>
                          <Typography variant="caption" color="text.secondary">Belegt</Typography>
                          <Typography fontWeight={700}>{loc.belegt}/{loc.kontingent}</Typography>
                        </Box>
                        <Divider orientation="vertical" flexItem />
                        <Box>
                          <Typography variant="caption" color="text.secondary">Frei</Typography>
                          <Typography fontWeight={700} sx={{ color: cfg.color }}>{loc.kontingent - loc.belegt}</Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            )
          })}
        </Grid>
      </Box>

      {/* Karten-Ansicht */}
      <Box sx={{ display: viewMode === 'map' ? 'block' : 'none' }}>
        <MapView locations={locations} visible={viewMode === 'map'} />
      </Box>

      {/* Neue Einrichtung Dialog */}
      <Dialog open={newLocOpen} onClose={() => setNewLocOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>Neue Einrichtung anlegen</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 2 }}>
          <TextField label="Name der Einrichtung *" value={newName}
            onChange={(e) => setNewName(e.target.value)} fullWidth required />
          <TextField label="Adresse" value={newAdresse}
            onChange={(e) => setNewAdresse(e.target.value)} fullWidth multiline rows={2} />
          <Box display="flex" gap={2}>
            <TextField label="Kontingent (Plätze) *" type="number" value={newKontingent}
              onChange={(e) => setNewKontingent(e.target.value)} inputProps={{ min: 0 }} fullWidth />
            <TextField label="Notbett-Kapazität" type="number" value={newNotbett}
              onChange={(e) => setNewNotbett(e.target.value)} inputProps={{ min: 0 }} fullWidth />
          </Box>
          <Alert severity="info">
            Nach dem Anlegen können Räume und Betten in der Drilldown-Ansicht der Einrichtung verwaltet werden.
          </Alert>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setNewLocOpen(false)}>Abbrechen</Button>
          <Button variant="contained" disabled={!newName.trim() || newLocSaving} onClick={handleCreateLocation}>
            {newLocSaving ? <CircularProgress size={18} /> : 'Anlegen'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={5000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>

      <Snackbar open={errorOpen} autoHideDuration={6000} onClose={() => setErrorOpen(false)}>
        <Alert severity="error" onClose={() => setErrorOpen(false)}>Daten konnten nicht geladen werden.</Alert>
      </Snackbar>
      <Snackbar open={warnOpen} autoHideDuration={8000} onClose={() => setWarnOpen(false)}>
        <Alert severity="warning" onClose={() => setWarnOpen(false)}>
          Standort-Zuordnung fehlt im Token — eigene Einrichtung kann nicht hervorgehoben werden.
        </Alert>
      </Snackbar>
    </Box>
  )
}
