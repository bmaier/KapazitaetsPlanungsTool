import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  Link,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import BedIcon from '@mui/icons-material/Hotel'
import ManIcon from '@mui/icons-material/Man'
import WomanIcon from '@mui/icons-material/Woman'
import PeopleIcon from '@mui/icons-material/People'
import LogoutIcon from '@mui/icons-material/Logout'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import AddCircleIcon from '@mui/icons-material/AddCircle'
import AddIcon from '@mui/icons-material/Add'
import MeetingRoomIcon from '@mui/icons-material/MeetingRoom'
import BlockIcon from '@mui/icons-material/Block'
import { useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'
import LabelChips, { LabelList } from '../components/LabelChips'

interface Location {
  id: string
  name: string
  adresse: string
  kontingent: number
  notbett_kapazitaet: number
  is_active: boolean
}

interface BedStatus {
  bed_id: string
  bett_nummer: string
  bett_typ: string
  status: 'FREI' | 'BELEGT'
  occupancy_id?: string
  azr_id?: string
  alias_id?: string
  occ_geschlecht?: string
  belegung_start?: string
  belegung_ende?: string
  room_labels?: string[]
  bed_labels?: string[]
  occ_labels?: string[]
}

interface RoomStatus {
  room_id: string
  room_name: string
  geschlechts_designation: string
  beds: BedStatus[]
  pending_count: number
  labels?: string[]
}

interface RoomMgmt {
  id: string
  name: string
  geschlechts_designation: string
  is_active: boolean
  beds: { id: string; bett_nummer: string; bett_typ: string; is_active: boolean }[]
}

function genderIcon(g: string) {
  if (g === 'M') return <ManIcon sx={{ fontSize: 18 }} />
  if (g === 'W') return <WomanIcon sx={{ fontSize: 18 }} />
  return <PeopleIcon sx={{ fontSize: 18 }} />
}
function genderLabel(g: string) {
  if (g === 'M') return 'Männer'
  if (g === 'W') return 'Frauen'
  return 'Gemischt'
}
function genderColor(g: string): string {
  if (g === 'M') return '#1565c0'
  if (g === 'W') return '#880e4f'
  return '#4a148c'
}

interface BedGridProps {
  room: RoomStatus
  canEdit: boolean
  onBedClick: (bed: BedStatus, room: RoomStatus) => void
}

function BedGrid({ room, canEdit, onBedClick }: BedGridProps) {
  const frei = room.beds.filter((b) => b.status === 'FREI').length
  const belegt = room.beds.filter((b) => b.status === 'BELEGT').length
  const color = genderColor(room.geschlechts_designation)

  return (
    <Paper elevation={2} sx={{ p: 2.5, borderRadius: 3, borderTop: `4px solid ${color}`, height: '100%' }}>
      <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
        <Box sx={{ color }}>{genderIcon(room.geschlechts_designation)}</Box>
        <Typography fontWeight={700} sx={{ color }}>{room.room_name}</Typography>
        <Chip label={genderLabel(room.geschlechts_designation)} size="small"
          sx={{ bgcolor: color + '15', color, fontWeight: 600, ml: 0.5 }} />
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="caption" color="text.secondary">
          {frei} frei · {belegt} belegt
        </Typography>
        {room.pending_count > 0 && (
          <Chip
            icon={<WarningAmberIcon sx={{ fontSize: 14 }} />}
            label={`${room.pending_count} Anfrage${room.pending_count > 1 ? 'n' : ''} offen`}
            size="small"
            sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 700, height: 22 }}
          />
        )}
      </Box>
      {(room.labels ?? []).length > 0 && (
        <Box mb={1}>
          <LabelList labels={room.labels ?? []} />
        </Box>
      )}

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {room.beds.map((bed) => {
          const isBelegt = bed.status === 'BELEGT'
          return (
            <Tooltip
              key={bed.bed_id}
              title={
                <Box>
                  {isBelegt
                    ? `${bed.azr_id || '–'}${bed.alias_id ? ' · ' + bed.alias_id : ''} · ${bed.belegung_start} – ${bed.belegung_ende}`
                    : 'Bett frei'}
                  {(bed.bed_labels ?? []).length > 0 && ` · ${bed.bed_labels!.join(', ')}`}
                  {isBelegt && (bed.occ_labels ?? []).length > 0 && ` · ${bed.occ_labels!.join(', ')}`}
                  {canEdit && (isBelegt ? ' · Klicken zum Verwalten' : ' · Klicken zum Belegen')}
                </Box>
              }
              arrow
            >
              <Box
                onClick={() => canEdit && onBedClick(bed, room)}
                sx={{
                  width: 58,
                  height: 58,
                  borderRadius: 1.5,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: isBelegt ? '#ffebee' : '#e8f5e9',
                  border: `2px solid ${isBelegt ? '#e53935' : '#43a047'}`,
                  cursor: canEdit ? 'pointer' : 'default',
                  transition: 'all 0.15s',
                  '&:hover': canEdit ? { transform: 'scale(1.1)', boxShadow: 3 } : {},
                }}
              >
                <BedIcon sx={{ fontSize: 16, color: isBelegt ? '#c62828' : '#2e7d32', mb: 0.2 }} />
                <Typography variant="caption" fontWeight={700}
                  sx={{ color: isBelegt ? '#c62828' : '#2e7d32', lineHeight: 1, fontSize: 10 }}>
                  {bed.bett_nummer}
                </Typography>
                {isBelegt && bed.azr_id && (
                  <Typography sx={{ fontSize: 7, color: '#c62828', lineHeight: 1, maxWidth: 52, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', px: 0.3 }}>
                    {bed.azr_id.slice(-6)}
                  </Typography>
                )}
              </Box>
            </Tooltip>
          )
        })}
      </Box>

      <Box display="flex" gap={2} mt={1.5}>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#43a047' }} />
          <Typography variant="caption" color="text.secondary">Frei{canEdit && ' (klicken)'}</Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#e53935' }} />
          <Typography variant="caption" color="text.secondary">Belegt{canEdit && ' (klicken)'}</Typography>
        </Box>
      </Box>
    </Paper>
  )
}

export default function Drilldown() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { get, post, patch, del } = useApiClient()
  const { keycloak } = useKeycloak()

  const roles = ((keycloak?.tokenParsed as Record<string, unknown>)?.realm_access as { roles?: string[] } | undefined)?.roles ?? []
  const canEdit = roles.some((r) => ['location-admin', 'system-admin', 'writer'].includes(r))
  const isAdmin = roles.some((r) => ['location-admin', 'system-admin'].includes(r))

  const today = new Date().toISOString().slice(0, 10)
  const in14 = new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10)

  const [location, setLocation] = useState<Location | null>(null)
  const [rooms, setRooms] = useState<RoomStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(in14)

  // Edit-Location-Dialog
  const [editOpen, setEditOpen] = useState(false)
  const [editTab, setEditTab] = useState(0)
  const [editKontingent, setEditKontingent] = useState('')
  const [editNotbett, setEditNotbett] = useState('')
  const [editAdresse, setEditAdresse] = useState('')
  const [saving, setSaving] = useState(false)

  // Room/Bed management (shown in edit dialog tab 1)
  const [mgmtRooms, setMgmtRooms] = useState<RoomMgmt[]>([])
  const [mgmtLoading, setMgmtLoading] = useState(false)
  const [newRoomName, setNewRoomName] = useState('')
  const [newRoomGeschlecht, setNewRoomGeschlecht] = useState('M')
  const [addingRoom, setAddingRoom] = useState(false)
  const [addBedRoomId, setAddBedRoomId] = useState<string | null>(null)
  const [newBedNummer, setNewBedNummer] = useState('')
  const [newBedTyp, setNewBedTyp] = useState('STANDARD')
  const [addingBed, setAddingBed] = useState(false)

  // Bett belegen Dialog (freies Bett klicken)
  const [belegBed, setBelegBed] = useState<{ bed: BedStatus; room: RoomStatus } | null>(null)
  const [azrId, setAzrId] = useState('')
  const [aliasId, setAliasId] = useState('')
  const [belegGeschlecht, setBelegGeschlecht] = useState('M')
  const [belegStart, setBelegStart] = useState(today)
  const [belegEnde, setBelegEnde] = useState(in14)
  const [belegLabels, setBelegLabels] = useState<string[]>([])
  const [belegSaving, setBelegSaving] = useState(false)
  const [warn12w, setWarn12w] = useState(false)

  // Belegung verwalten Dialog (belegtes Bett klicken)
  const [manageBed, setManageBed] = useState<{ bed: BedStatus; room: RoomStatus } | null>(null)
  const [checkoutConfirm, setCheckoutConfirm] = useState(false)
  const [checkoutSaving, setCheckoutSaving] = useState(false)

  // Intern verlegen Dialog
  const [verlegenOpen, setVerlegenOpen] = useState(false)
  const [verlegenTargetBed, setVerlegenTargetBed] = useState('')
  const [verlegenSaving, setVerlegenSaving] = useState(false)

  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'warning' }>({
    open: false, message: '', severity: 'success',
  })

  useEffect(() => {
    if (!id) return
    get<Location>(`/api/locations/${id}`).then(setLocation).catch(() => {})
  }, [id, get])

  const loadBedStatus = useCallback(() => {
    if (!id) return
    setLoading(true)
    get<RoomStatus[]>(`/api/locations/${id}/bed-status?date_from=${dateFrom}&date_to=${dateTo}`)
      .then(setRooms)
      .catch(() => setSnackbar({ open: true, message: 'Bettstatus konnte nicht geladen werden.', severity: 'error' }))
      .finally(() => setLoading(false))
  }, [id, dateFrom, dateTo, get])

  useEffect(() => { loadBedStatus() }, [loadBedStatus])

  const totalFrei = rooms.flatMap((r) => r.beds).filter((b) => b.status === 'FREI').length
  const totalBelegt = rooms.flatMap((r) => r.beds).filter((b) => b.status === 'BELEGT').length
  const totalPending = rooms.reduce((s, r) => s + r.pending_count, 0)

  const freiBeds = rooms.flatMap((r) =>
    r.beds.filter((b) => b.status === 'FREI').map((b) => ({ ...b, room_name: r.room_name, room_id: r.room_id, geschlecht: r.geschlechts_designation }))
  )

  // Room management
  const loadMgmtRooms = useCallback(async () => {
    if (!id) return
    setMgmtLoading(true)
    try {
      const roomList = await get<{ id: string; name: string; geschlechts_designation: string; is_active: boolean }[]>(
        `/api/locations/${id}/rooms?include_inactive=true`
      )
      const withBeds = await Promise.all(
        roomList.map(async (r) => {
          const beds = await get<{ id: string; bett_nummer: string; bett_typ: string; is_active: boolean }[]>(
            `/api/rooms/${r.id}/beds?include_inactive=true`
          ).catch(() => [])
          return { ...r, beds }
        })
      )
      setMgmtRooms(withBeds)
    } catch {
      setSnackbar({ open: true, message: 'Raumliste konnte nicht geladen werden.', severity: 'error' })
    } finally {
      setMgmtLoading(false)
    }
  }, [id, get])

  function openEdit() {
    setEditKontingent(String(location?.kontingent ?? ''))
    setEditNotbett(String(location?.notbett_kapazitaet ?? ''))
    setEditAdresse(location?.adresse ?? '')
    setEditTab(0)
    setEditOpen(true)
    if (isAdmin) loadMgmtRooms()
  }

  async function saveEdit() {
    if (!id) return
    setSaving(true)
    try {
      const updated = await patch<Location>(`/api/locations/${id}`, {
        kontingent: Number(editKontingent),
        notbett_kapazitaet: Number(editNotbett),
        adresse: editAdresse,
      })
      setLocation(updated)
      setEditOpen(false)
      setSnackbar({ open: true, message: 'Einrichtung aktualisiert.', severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Speichern fehlgeschlagen.', severity: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleAddRoom() {
    if (!id || !newRoomName.trim()) return
    setAddingRoom(true)
    try {
      await post(`/api/locations/${id}/rooms`, { name: newRoomName, geschlechts_designation: newRoomGeschlecht })
      setNewRoomName('')
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Raum "${newRoomName}" angelegt.`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Raum anlegen fehlgeschlagen.', severity: 'error' })
    } finally {
      setAddingRoom(false)
    }
  }

  async function handleDeactivateRoom(roomId: string, roomName: string) {
    try {
      await del(`/api/rooms/${roomId}`)
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Raum "${roomName}" deaktiviert.`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Raum deaktivieren fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleAddBed(roomId: string) {
    if (!newBedNummer.trim()) return
    setAddingBed(true)
    try {
      await post(`/api/rooms/${roomId}/beds`, { bett_nummer: newBedNummer, bett_typ: newBedTyp })
      setAddBedRoomId(null)
      setNewBedNummer('')
      setNewBedTyp('STANDARD')
      await loadMgmtRooms()
      loadBedStatus()
    } catch {
      setSnackbar({ open: true, message: 'Bett hinzufügen fehlgeschlagen.', severity: 'error' })
    } finally {
      setAddingBed(false)
    }
  }

  async function handleDeactivateBed(bedId: string, bedNr: string) {
    try {
      await del(`/api/beds/${bedId}`)
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Bett ${bedNr} deaktiviert.`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Bett deaktivieren fehlgeschlagen.', severity: 'error' })
    }
  }

  function handleBedClick(bed: BedStatus, room: RoomStatus) {
    if (bed.status === 'FREI') {
      setBelegGeschlecht(room.geschlechts_designation === 'D' ? 'M' : room.geschlechts_designation)
      setAzrId('')
      setAliasId('')
      setBelegStart(today)
      setBelegEnde(in14)
      setBelegLabels([])
      setWarn12w(false)
      setBelegBed({ bed, room })
    } else {
      setCheckoutConfirm(false)
      setManageBed({ bed, room })
    }
  }

  async function handleBelegen() {
    if (!belegBed) return
    setBelegSaving(true)
    try {
      const response = await fetch(`/api/beds/${belegBed.bed.bed_id}/occupancy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${keycloak?.token ?? ''}`,
        },
        body: JSON.stringify({
          azr_id: azrId,
          alias_id: aliasId || null,
          geschlecht: belegGeschlecht,
          belegung_start: belegStart,
          belegung_ende: belegEnde,
        }),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error((err as { detail?: string })?.detail || 'Fehler')
      }
      const has12w = response.headers.get('X-12W-Warning') === 'true'
      // Labels für die neue Belegung setzen (wenn angegeben)
      if (belegLabels.length > 0) {
        const occupancyData = await response.clone().json().catch(() => null) as { id?: string } | null
        if (occupancyData?.id) {
          await patch(`/api/occupancy/${occupancyData.id}/labels`, { labels: belegLabels }).catch(() => {})
        }
      }
      setBelegBed(null)
      setBelegLabels([])
      loadBedStatus()
      setSnackbar({
        open: true,
        message: has12w ? 'Bett belegt. ⚠ Belegung überschreitet 12 Wochen.' : 'Bett erfolgreich belegt.',
        severity: has12w ? 'warning' : 'success',
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unbekannter Fehler'
      setSnackbar({ open: true, message: `Belegen fehlgeschlagen: ${msg}`, severity: 'error' })
    } finally {
      setBelegSaving(false)
    }
  }

  async function handleAusbuchen() {
    if (!manageBed?.bed.occupancy_id) return
    setCheckoutSaving(true)
    try {
      await del(`/api/beds/${manageBed.bed.bed_id}/occupancy/${manageBed.bed.occupancy_id}`)
      setManageBed(null)
      loadBedStatus()
      setSnackbar({ open: true, message: 'Person erfolgreich ausgebucht.', severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Ausbuchen fehlgeschlagen.', severity: 'error' })
    } finally {
      setCheckoutSaving(false)
    }
  }

  async function handleVerlegen() {
    if (!manageBed?.bed.occupancy_id || !verlegenTargetBed) return
    setVerlegenSaving(true)
    const src = manageBed.bed
    try {
      await post(`/api/beds/${verlegenTargetBed}/occupancy`, {
        azr_id: src.azr_id,
        alias_id: src.alias_id || null,
        geschlecht: src.occ_geschlecht || 'M',
        belegung_start: src.belegung_start,
        belegung_ende: src.belegung_ende,
      })
      await del(`/api/beds/${src.bed_id}/occupancy/${src.occupancy_id}`)
      setVerlegenOpen(false)
      setManageBed(null)
      loadBedStatus()
      setSnackbar({ open: true, message: 'Person erfolgreich verlegt.', severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Verlegen fehlgeschlagen.', severity: 'error' })
    } finally {
      setVerlegenSaving(false)
    }
  }

  function navigateToSuggestion() {
    const bed = manageBed?.bed
    if (!bed) return
    setManageBed(null)
    navigate(`/suggestions?azrId=${encodeURIComponent(bed.azr_id ?? '')}&geschlecht=${bed.occ_geschlecht ?? 'M'}&aliasId=${encodeURIComponent(bed.alias_id ?? '')}`)
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link component="button" underline="hover" color="inherit" onClick={() => navigate('/')} sx={{ cursor: 'pointer' }}>
          Übersicht
        </Link>
        <Typography color="text.primary">{location?.name ?? 'Einrichtung'}</Typography>
      </Breadcrumbs>

      {/* Location Header */}
      {location && (
        <Paper elevation={0} sx={{ p: 3, mb: 3, borderRadius: 3, bgcolor: '#003366', color: 'white' }}>
          <Box display="flex" alignItems="flex-start" justifyContent="space-between">
            <Box>
              <Typography variant="h5" fontWeight={700}>{location.name}</Typography>
              {location.adresse && (
                <Typography variant="body2" sx={{ opacity: 0.8, mt: 0.5 }}>{location.adresse}</Typography>
              )}
            </Box>
            {canEdit && (
              <IconButton onClick={openEdit} sx={{ color: 'white', bgcolor: 'rgba(255,255,255,0.1)', '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' } }}>
                <EditIcon />
              </IconButton>
            )}
          </Box>
          <Box display="flex" gap={3} mt={2} flexWrap="wrap">
            {[
              { label: 'Kontingent', value: location.kontingent },
              { label: 'Notbetten', value: location.notbett_kapazitaet },
              { label: 'Frei', value: totalFrei, color: '#a5d6a7' },
              { label: 'Belegt', value: totalBelegt, color: '#ef9a9a' },
            ].map(({ label, value, color }) => (
              <Box key={label} sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight={800} sx={{ color: color ?? 'white', lineHeight: 1 }}>
                  {value}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>{label}</Typography>
              </Box>
            ))}
            {totalPending > 0 && (
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight={800} sx={{ color: '#ffcc80', lineHeight: 1 }}>
                  {totalPending}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>Anfragen</Typography>
              </Box>
            )}
          </Box>
        </Paper>
      )}

      {/* Date Range Filter */}
      <Paper elevation={0} sx={{ p: 2, mb: 3, borderRadius: 2, border: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="body2" fontWeight={600} color="text.secondary">Belegung für:</Typography>
        <TextField label="Von" type="date" size="small" value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); if (e.target.value >= dateTo) setDateTo(e.target.value) }}
          InputLabelProps={{ shrink: true }} sx={{ width: 160 }} />
        <TextField label="Bis" type="date" size="small" value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }} inputProps={{ min: dateFrom }} sx={{ width: 160 }} />
        <Button variant="outlined" size="small" onClick={() => { setDateFrom(today); setDateTo(in14) }}>
          Heute · +14 Tage
        </Button>
        <Button variant="outlined" size="small" onClick={() => {
          const in90 = new Date(Date.now() + 90 * 86400000).toISOString().slice(0, 10)
          setDateTo(in90)
        }}>
          +90 Tage
        </Button>
        {canEdit && (
          <Button variant="contained" size="small" startIcon={<AddCircleIcon />}
            onClick={() => navigate('/suggestions')}
            sx={{ ml: 'auto' }}>
            Reservierungsanfrage
          </Button>
        )}
      </Paper>

      {/* Bed Grid */}
      {loading ? (
        <Box display="flex" justifyContent="center" mt={6}><CircularProgress /></Box>
      ) : rooms.length === 0 ? (
        <Alert severity="info">Keine Räume für diese Einrichtung gefunden.</Alert>
      ) : (
        <Grid container spacing={3}>
          {rooms.map((room) => (
            <Grid item xs={12} md={6} key={room.room_id}>
              <BedGrid room={room} canEdit={canEdit} onBedClick={handleBedClick} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* ── Bett belegen Dialog ── */}
      <Dialog open={!!belegBed} onClose={() => setBelegBed(null)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <BedIcon sx={{ color: '#003366' }} />
            Bett {belegBed?.bed.bett_nummer} belegen — {belegBed?.room.room_name}
          </Box>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 2 }}>
          <TextField
            label="AZR-ID *"
            value={azrId}
            onChange={(e) => setAzrId(e.target.value)}
            placeholder="z.B. AZR-2024-FFM-M01"
            fullWidth required
          />
          <TextField
            label="Alias-ID (optional)"
            value={aliasId}
            onChange={(e) => setAliasId(e.target.value)}
            placeholder="z.B. AL-M-001"
            fullWidth
          />
          {belegBed?.room.geschlechts_designation === 'D' && (
            <FormControl size="small" fullWidth>
              <InputLabel>Geschlecht</InputLabel>
              <Select value={belegGeschlecht} label="Geschlecht" onChange={(e) => setBelegGeschlecht(e.target.value)}>
                <MenuItem value="M">Männlich</MenuItem>
                <MenuItem value="W">Weiblich</MenuItem>
                <MenuItem value="D">Divers</MenuItem>
              </Select>
            </FormControl>
          )}
          <Box display="flex" gap={2}>
            <TextField label="Belegung von *" type="date" size="small" value={belegStart}
              onChange={(e) => {
                setBelegStart(e.target.value)
                const end = new Date(new Date(e.target.value).getTime() + 14 * 86400000).toISOString().slice(0, 10)
                setBelegEnde(end)
              }}
              InputLabelProps={{ shrink: true }} fullWidth />
            <TextField label="Belegung bis *" type="date" size="small" value={belegEnde}
              onChange={(e) => setBelegEnde(e.target.value)}
              InputLabelProps={{ shrink: true }} inputProps={{ min: belegStart }} fullWidth />
          </Box>

          {/* Labels-Matching-Hinweis: Raum-Labels als Kontext */}
          {(belegBed?.room.labels ?? belegBed?.bed.room_labels ?? []).length > 0 && (
            <Alert severity="info" sx={{ py: 0.5 }}>
              <Typography variant="caption" fontWeight={700}>Raum-Eigenschaften:</Typography>{' '}
              <LabelList labels={belegBed?.room.labels ?? belegBed?.bed.room_labels ?? []} />
            </Alert>
          )}

          {/* Hinweis-Labels für die Person */}
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Hinweis-Labels zur Person (optional, nicht verbindlich)
            </Typography>
            <LabelChips
              labels={belegLabels}
              entityType="OCCUPANCY"
              entityId="new"
              readOnly={false}
              onSaved={(l) => setBelegLabels(l)}
            />
          </Box>

          {warn12w && (
            <Alert severity="warning">Belegungsdauer überschreitet 12 Wochen.</Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setBelegBed(null)}>Abbrechen</Button>
          <Button variant="contained" onClick={handleBelegen} disabled={belegSaving || !azrId.trim()}>
            {belegSaving ? <CircularProgress size={18} /> : 'Bett belegen'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Belegung verwalten Dialog ── */}
      <Dialog open={!!manageBed} onClose={() => { setManageBed(null); setCheckoutConfirm(false) }} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <BedIcon sx={{ color: '#c62828' }} />
            Bett {manageBed?.bed.bett_nummer} — {manageBed?.room.room_name}
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {manageBed && (
            <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8f9fa', borderRadius: 2, mb: 2 }}>
              <Box display="flex" gap={3} flexWrap="wrap" mb={1.5}>
                <Box>
                  <Typography variant="caption" color="text.secondary">AZR-ID</Typography>
                  <Typography fontWeight={700}>{manageBed.bed.azr_id || '–'}</Typography>
                </Box>
                {manageBed.bed.alias_id && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">Alias-ID</Typography>
                    <Typography fontWeight={700}>{manageBed.bed.alias_id}</Typography>
                  </Box>
                )}
                <Box>
                  <Typography variant="caption" color="text.secondary">Geschlecht</Typography>
                  <Typography fontWeight={700}>
                    {manageBed.bed.occ_geschlecht === 'M' ? 'Männlich' : manageBed.bed.occ_geschlecht === 'W' ? 'Weiblich' : 'Divers'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Belegungszeitraum</Typography>
                  <Typography fontWeight={700}>{manageBed.bed.belegung_start} – {manageBed.bed.belegung_ende}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Belegungstyp</Typography>
                  <Typography fontWeight={700}>{manageBed.bed.bett_typ}</Typography>
                </Box>
              </Box>
              {manageBed.bed.occupancy_id && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                    Hinweis-Labels (nicht verbindlich)
                  </Typography>
                  <LabelChips
                    labels={manageBed.bed.occ_labels ?? []}
                    entityType="OCCUPANCY"
                    entityId={manageBed.bed.occupancy_id}
                    onSaved={(newLabels) => {
                      setManageBed((prev) => prev ? {
                        ...prev,
                        bed: { ...prev.bed, occ_labels: newLabels }
                      } : prev)
                    }}
                  />
                </Box>
              )}
            </Paper>
          )}

          {!checkoutConfirm ? (
            <Box display="flex" flexDirection="column" gap={1.5}>
              <Button fullWidth variant="outlined" color="error" startIcon={<LogoutIcon />}
                onClick={() => setCheckoutConfirm(true)}>
                Ausbuchen (Belegung beenden)
              </Button>
              <Button fullWidth variant="outlined" color="primary" startIcon={<SwapHorizIcon />}
                onClick={() => { setVerlegenTargetBed(''); setVerlegenOpen(true) }}>
                Intern verlegen (anderes Bett in dieser Einrichtung)
              </Button>
              <Button fullWidth variant="outlined" color="secondary" startIcon={<SwapHorizIcon />}
                onClick={navigateToSuggestion}>
                Zu anderer Einrichtung verlegen (Reservierungsanfrage)
              </Button>
            </Box>
          ) : (
            <Alert severity="warning" sx={{ mb: 1 }}>
              Belegung für <strong>{manageBed?.bed.azr_id}</strong> wirklich beenden?
              <Box mt={1} display="flex" gap={1}>
                <Button size="small" color="error" variant="contained" disabled={checkoutSaving}
                  onClick={handleAusbuchen}>
                  {checkoutSaving ? <CircularProgress size={16} /> : 'Ja, ausbuchen'}
                </Button>
                <Button size="small" onClick={() => setCheckoutConfirm(false)}>Abbrechen</Button>
              </Box>
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setManageBed(null); setCheckoutConfirm(false) }}>Schließen</Button>
        </DialogActions>
      </Dialog>

      {/* ── Intern verlegen Dialog ── */}
      <Dialog open={verlegenOpen} onClose={() => setVerlegenOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>Intern verlegen — Zielbett wählen</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {freiBeds.length === 0 ? (
            <Alert severity="warning">Keine freien Betten in dieser Einrichtung verfügbar.</Alert>
          ) : (
            <Box>
              <Typography variant="body2" color="text.secondary" mb={2}>
                Freie Betten in dieser Einrichtung:
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                {freiBeds.map((b) => (
                  <Paper
                    key={b.bed_id}
                    elevation={verlegenTargetBed === b.bed_id ? 4 : 1}
                    onClick={() => setVerlegenTargetBed(b.bed_id)}
                    sx={{
                      p: 1.5, borderRadius: 2, cursor: 'pointer',
                      border: verlegenTargetBed === b.bed_id ? '2px solid #003366' : '2px solid transparent',
                      bgcolor: verlegenTargetBed === b.bed_id ? '#e3f2fd' : 'white',
                      transition: 'all 0.15s',
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <BedIcon sx={{ color: '#43a047' }} />
                      <Typography fontWeight={600}>{b.room_name} — Bett {b.bett_nummer}</Typography>
                      <Chip label={genderLabel(b.geschlecht)} size="small"
                        sx={{ bgcolor: genderColor(b.geschlecht) + '15', color: genderColor(b.geschlecht) }} />
                    </Box>
                  </Paper>
                ))}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setVerlegenOpen(false)}>Abbrechen</Button>
          <Button variant="contained" disabled={!verlegenTargetBed || verlegenSaving}
            onClick={handleVerlegen}>
            {verlegenSaving ? <CircularProgress size={18} /> : 'Verlegen bestätigen'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Einrichtung bearbeiten Dialog (tabbed) ── */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <EditIcon sx={{ color: '#003366' }} />
            {location?.name} bearbeiten
          </Box>
        </DialogTitle>
        <Tabs value={editTab} onChange={(_, v) => { setEditTab(v); if (v === 1 && isAdmin) loadMgmtRooms() }}
          sx={{ px: 3, borderBottom: '1px solid #e0e0e0' }}>
          <Tab label="Stammdaten" />
          {isAdmin && <Tab label="Räume & Betten" icon={<MeetingRoomIcon sx={{ fontSize: 18 }} />} iconPosition="start" />}
        </Tabs>

        <DialogContent sx={{ pt: 2.5, minHeight: 300 }}>
          {/* Tab 0: Stammdaten */}
          {editTab === 0 && (
            <Box display="flex" flexDirection="column" gap={2.5}>
              <TextField label="Kontingent (Plätze)" type="number" value={editKontingent}
                onChange={(e) => setEditKontingent(e.target.value)} inputProps={{ min: 0 }} fullWidth />
              <TextField label="Notbett-Kapazität" type="number" value={editNotbett}
                onChange={(e) => setEditNotbett(e.target.value)} inputProps={{ min: 0 }} fullWidth />
              <TextField label="Adresse" value={editAdresse}
                onChange={(e) => setEditAdresse(e.target.value)} fullWidth multiline rows={2} />
            </Box>
          )}

          {/* Tab 1: Räume & Betten */}
          {editTab === 1 && isAdmin && (
            <Box>
              {mgmtLoading ? (
                <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
              ) : (
                <>
                  {mgmtRooms.length === 0 && (
                    <Alert severity="info" sx={{ mb: 2 }}>Noch keine Räume vorhanden. Legen Sie unten einen Raum an.</Alert>
                  )}

                  <Box display="flex" flexDirection="column" gap={2} mb={3}>
                    {mgmtRooms.map((room) => (
                      <Paper key={room.id} elevation={1} sx={{
                        p: 2, borderRadius: 2,
                        borderLeft: `4px solid ${room.is_active ? genderColor(room.geschlechts_designation) : '#bdbdbd'}`,
                        opacity: room.is_active ? 1 : 0.55,
                      }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                          <MeetingRoomIcon sx={{ fontSize: 18, color: room.is_active ? '#003366' : '#888' }} />
                          <Typography fontWeight={700}>{room.name}</Typography>
                          <Chip label={genderLabel(room.geschlechts_designation)} size="small"
                            sx={{ bgcolor: genderColor(room.geschlechts_designation) + '15', color: genderColor(room.geschlechts_designation) }} />
                          {!room.is_active && <Chip label="Inaktiv" size="small" sx={{ bgcolor: '#f5f5f5', color: '#888' }} />}
                          <Box sx={{ flexGrow: 1 }} />
                          {room.is_active && (
                            <>
                              <Button size="small" startIcon={<AddIcon />}
                                onClick={() => { setAddBedRoomId(room.id); setNewBedNummer(''); setNewBedTyp('STANDARD') }}>
                                Bett
                              </Button>
                              <Tooltip title="Raum deaktivieren">
                                <IconButton size="small" color="error"
                                  onClick={() => handleDeactivateRoom(room.id, room.name)}>
                                  <BlockIcon sx={{ fontSize: 18 }} />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                        </Box>
                        {room.is_active && (
                          <Box mb={1}>
                            <LabelChips
                              labels={[]}
                              entityType="ROOM"
                              entityId={room.id}
                              compact
                              onSaved={() => loadMgmtRooms()}
                            />
                          </Box>
                        )}

                        {/* Beds */}
                        <Box display="flex" flexWrap="wrap" gap={0.8} mb={addBedRoomId === room.id ? 1.5 : 0}>
                          {room.beds.map((bed) => (
                            <Chip
                              key={bed.id}
                              icon={<BedIcon sx={{ fontSize: '14px !important' }} />}
                              label={bed.bett_nummer}
                              size="small"
                              onDelete={bed.is_active && room.is_active ? () => handleDeactivateBed(bed.id, bed.bett_nummer) : undefined}
                              sx={{
                                bgcolor: bed.is_active ? '#e8f5e9' : '#f5f5f5',
                                color: bed.is_active ? '#2e7d32' : '#888',
                                opacity: bed.is_active ? 1 : 0.6,
                              }}
                            />
                          ))}
                          {room.beds.length === 0 && (
                            <Typography variant="caption" color="text.secondary">Keine Betten</Typography>
                          )}
                        </Box>

                        {/* Add bed inline form */}
                        {addBedRoomId === room.id && (
                          <Box display="flex" gap={1} alignItems="center" mt={1} flexWrap="wrap">
                            <TextField label="Bett-Nr *" size="small" value={newBedNummer}
                              onChange={(e) => setNewBedNummer(e.target.value)}
                              sx={{ width: 100 }} />
                            <FormControl size="small" sx={{ width: 130 }}>
                              <InputLabel>Typ</InputLabel>
                              <Select value={newBedTyp} label="Typ" onChange={(e) => setNewBedTyp(e.target.value)}>
                                <MenuItem value="STANDARD">Standard</MenuItem>
                                <MenuItem value="NOTBETT">Notbett</MenuItem>
                                <MenuItem value="DOPPEL">Doppel</MenuItem>
                              </Select>
                            </FormControl>
                            <Button size="small" variant="contained" disabled={!newBedNummer.trim() || addingBed}
                              onClick={() => handleAddBed(room.id)}>
                              {addingBed ? <CircularProgress size={14} /> : 'Hinzufügen'}
                            </Button>
                            <Button size="small" onClick={() => setAddBedRoomId(null)}>Abbrechen</Button>
                          </Box>
                        )}
                      </Paper>
                    ))}
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  {/* New Room form */}
                  <Typography variant="body2" fontWeight={700} color="text.secondary" mb={1.5}>
                    Neuen Raum anlegen
                  </Typography>
                  <Box display="flex" gap={1.5} alignItems="flex-end" flexWrap="wrap">
                    <TextField label="Raumname *" size="small" value={newRoomName}
                      onChange={(e) => setNewRoomName(e.target.value)}
                      placeholder="z.B. Raum E" sx={{ flex: 1, minWidth: 150 }} />
                    <FormControl size="small" sx={{ width: 150 }}>
                      <InputLabel>Belegung</InputLabel>
                      <Select value={newRoomGeschlecht} label="Belegung"
                        onChange={(e) => setNewRoomGeschlecht(e.target.value)}>
                        <MenuItem value="M">Männer</MenuItem>
                        <MenuItem value="W">Frauen</MenuItem>
                        <MenuItem value="D">Gemischt</MenuItem>
                      </Select>
                    </FormControl>
                    <Button variant="contained" startIcon={<AddIcon />}
                      disabled={!newRoomName.trim() || addingRoom}
                      onClick={handleAddRoom}>
                      {addingRoom ? <CircularProgress size={16} /> : 'Raum anlegen'}
                    </Button>
                  </Box>
                </>
              )}
            </Box>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setEditOpen(false)}>Schließen</Button>
          {editTab === 0 && (
            <Button variant="contained" onClick={saveEdit} disabled={saving}>
              {saving ? <CircularProgress size={18} /> : 'Stammdaten speichern'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
