import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
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
import ChairAltIcon from '@mui/icons-material/ChairAlt'
import CheckBoxIcon from '@mui/icons-material/CheckBox'
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank'
import { extractApiError, useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'
import { useSseNotifications } from '../hooks/useSseNotifications'
import LabelChips, { LabelList } from '../components/LabelChips'
import HelpTooltip from '../components/HelpTooltip'
import BelegungSparkline from '../components/BelegungSparkline'

interface Location {
  id: string
  name: string
  adresse: string
  kontingent: number
  notbett_kapazitaet: number
  is_active: boolean
  labels?: string[]
  lat?: number | null
  lon?: number | null
  valid_from?: string | null
  valid_until?: string | null
}

interface PendingReservation {
  id: string
  azr_id: string
  geschlecht: string
  herkunftsland: string
  belegung_start: string
  belegung_ende: string
  requester_location_id: string
}

interface TransferReservationDetail {
  id: string
  azr_id: string
  status: string
  belegung_start: string
  belegung_ende: string
  requester_location_id?: string
  requester_location_name?: string | null
  target_location_name?: string | null
}

interface BedStatus {
  bed_id: string
  bett_nummer: string
  bett_typ: string
  status: 'FREI' | 'BELEGT' | 'VORGEMERKT'
  occupancy_id?: string
  azr_id?: string
  alias_id?: string
  occ_geschlecht?: string
  belegung_start?: string
  belegung_ende?: string
  room_labels?: string[]
  bed_labels?: string[]
  occ_labels?: string[]
  is_notbett?: boolean
  extended_once?: boolean
  deaktiviert_ab?: string | null
  bed_valid_from?: string | null
  reservation_id?: string
  reservation_azr_id?: string
  reservation_start?: string
  reservation_ende?: string
  has_pending_transfer?: boolean
  has_confirmed_transfer?: boolean
  pending_reservation_id?: string
  pending_requester_location_name?: string | null
  outgoing_reservation_id?: string
  transfer_target_location_name?: string | null
  pending_azr_id?: string | null
}

interface RoomStatus {
  room_id: string
  room_name: string
  geschlechts_designation: string
  room_type: string  // STANDARD | WARTEBEREICH
  beds: BedStatus[]
  pending_count: number
  labels?: string[]
  valid_from?: string | null
  valid_until?: string | null
}

interface RoomMgmt {
  id: string
  name: string
  geschlechts_designation: string
  room_type: string  // STANDARD | WARTEBEREICH
  is_active: boolean
  labels: string[]
  beds: { id: string; bett_nummer: string; bett_typ: string; is_active: boolean; deaktiviert_ab?: string | null }[]
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

function deriveGenderFromLabels(labels: string[]): string {
  if (labels.includes('Männer')) return 'M'
  if (labels.includes('Frauen')) return 'W'
  if (labels.includes('Familie') || labels.includes('Familienraum')) return 'D'
  return 'D'
}

const GENDER_LABELS = ['Männer', 'Frauen', 'Familie', 'Familienraum', 'Gemischt']

function hasGenderLabel(labels: string[]): boolean {
  return labels.some((l) => GENDER_LABELS.includes(l))
}

// Leiter das angezeigte Geschlecht eines Raums aus Labels und aktuellen Belegungen ab.
// Leerer Raum ohne Geschlechts-Label → Gemischt (D).
function deriveRoomGender(room: RoomStatus): string {
  const labels = room.labels ?? []
  if (labels.includes('Männer')) return 'M'
  if (labels.includes('Frauen')) return 'W'
  if (labels.includes('Familie') || labels.includes('Familienraum')) return 'D'
  const occupied = room.beds.filter((b) => b.status === 'BELEGT' && b.occ_geschlecht)
  if (occupied.length === 0) return 'D'
  const genders = [...new Set(occupied.map((b) => b.occ_geschlecht!))]
  return genders.length === 1 ? genders[0] : 'D'
}

function roomDateStatus(room: RoomStatus, refDate: string): 'geplant' | 'abgelaufen' | 'aktiv' {
  if (room.valid_from && refDate < room.valid_from) return 'geplant'
  if (room.valid_until && refDate > room.valid_until) return 'abgelaufen'
  return 'aktiv'
}

function bedIsActive(bed: BedStatus, refDate: string): boolean {
  if (bed.bed_valid_from && refDate < bed.bed_valid_from) return false
  if (bed.deaktiviert_ab && refDate >= bed.deaktiviert_ab) return false
  return true
}

interface BedGridProps {
  room: RoomStatus
  canEdit: boolean
  onBedClick: (bed: BedStatus, room: RoomStatus) => void
  refDate: string
}

function BedGrid({ room, canEdit, onBedClick, refDate }: BedGridProps) {
  const frei = room.beds.filter((b) => b.status === 'FREI').length
  const belegt = room.beds.filter((b) => b.status === 'BELEGT').length
  const vorgemerkt = room.beds.filter((b) => b.status === 'VORGEMERKT').length
  const effectiveGender = deriveRoomGender(room)
  const color = genderColor(effectiveGender)
  const dateStatus = roomDateStatus(room, refDate)
  const isOutOfRange = dateStatus !== 'aktiv'

  return (
    <Paper elevation={2} sx={{ p: 2.5, borderRadius: 3, borderTop: `4px solid ${isOutOfRange ? '#bdbdbd' : color}`, height: '100%', opacity: isOutOfRange ? 0.65 : 1 }}>
      <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
        <Box sx={{ color }}>{genderIcon(effectiveGender)}</Box>
        <Typography fontWeight={700} sx={{ color }}>{room.room_name}</Typography>
        <Chip label={genderLabel(effectiveGender)} size="small"
          sx={{ bgcolor: color + '15', color, fontWeight: 600, ml: 0.5 }} />
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="caption" color="text.secondary">
          {frei} frei · {belegt} belegt{vorgemerkt > 0 ? ` · ${vorgemerkt} vorgemerkt` : ''}
        </Typography>
        {isOutOfRange && (
          <Chip label={dateStatus === 'geplant' ? `ab ${room.valid_from}` : `bis ${room.valid_until}`}
            size="small" sx={{ bgcolor: '#eeeeee', color: '#616161', fontWeight: 600, height: 20 }} />
        )}
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
          const isVorgemerkt = bed.status === 'VORGEMERKT'
          const bedActive = bedIsActive(bed, refDate)
          const hasConfirmedTransfer = isBelegt && !!bed.has_confirmed_transfer
          const hasPendingTransfer = isBelegt && !hasConfirmedTransfer && !!bed.has_pending_transfer
          const hasPendingRequest = !isBelegt && !isVorgemerkt && !!bed.pending_reservation_id
          const bedColor = !bedActive ? '#9e9e9e' : isVorgemerkt ? '#0d47a1' : hasPendingRequest ? '#7b1fa2' : hasConfirmedTransfer ? '#0d47a1' : hasPendingTransfer ? '#e65100' : isBelegt ? '#c62828' : '#2e7d32'
          const bedBg = !bedActive ? '#f5f5f5' : isVorgemerkt ? '#e3f2fd' : hasPendingRequest ? '#f3e5f5' : hasConfirmedTransfer ? '#e3f2fd' : hasPendingTransfer ? '#fff3e0' : isBelegt ? '#ffebee' : '#e8f5e9'
          const bedBorder = !bedActive ? '#bdbdbd' : isVorgemerkt ? '#1565c0' : hasPendingRequest ? '#ab47bc' : hasConfirmedTransfer ? '#1565c0' : hasPendingTransfer ? '#fb8c00' : isBelegt ? '#e53935' : '#43a047'
          const isClickable = canEdit && bedActive && (isBelegt || isVorgemerkt || (!isBelegt && !isVorgemerkt))
          return (
            <Tooltip
              key={bed.bed_id}
              title={
                <Box>
                  {!bedActive
                    ? (bed.bed_valid_from && refDate < bed.bed_valid_from ? `Verfügbar ab ${bed.bed_valid_from}` : `Deaktiviert ab ${bed.deaktiviert_ab}`)
                    : isVorgemerkt
                    ? `Vorgemerkt für: ${bed.reservation_azr_id ?? '–'} · ${bed.reservation_start} – ${bed.reservation_ende}`
                    : hasPendingRequest
                    ? `${bed.pending_azr_id ?? '?'} · Anfrage von: ${bed.pending_requester_location_name ?? '?'}`
                    : isBelegt
                    ? `${bed.azr_id || '–'}${bed.alias_id ? ' · ' + bed.alias_id : ''} · ${bed.belegung_start} – ${bed.belegung_ende}${hasConfirmedTransfer ? ' · Verlegung genehmigt — Eincheck ausstehend' : hasPendingTransfer ? ` · Verlegungsanfrage → ${bed.transfer_target_location_name ?? '?'}` : ''}`
                    : 'Bett frei'}
                  {(bed.bed_labels ?? []).length > 0 && ` · ${bed.bed_labels!.join(', ')}`}
                  {isBelegt && (bed.occ_labels ?? []).length > 0 && ` · ${bed.occ_labels!.join(', ')}`}
                  {canEdit && bedActive && (isVorgemerkt ? ' · Klicken zur Reservierung' : hasPendingRequest ? ' · Klicken → Anfragen anzeigen' : isBelegt ? ' · Klicken zum Verwalten' : ' · Klicken zum Belegen')}
                </Box>
              }
              arrow
            >
              <Box
                onClick={() => isClickable && onBedClick(bed, room)}
                sx={{
                  position: 'relative',
                  width: 58,
                  height: 58,
                  borderRadius: 1.5,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: bedBg,
                  border: `2px ${isVorgemerkt || hasPendingRequest || hasPendingTransfer || hasConfirmedTransfer ? 'dashed' : 'solid'} ${bedBorder}`,
                  cursor: isClickable ? 'pointer' : 'default',
                  opacity: bedActive ? 1 : 0.5,
                  transition: 'all 0.15s',
                  '&:hover': isClickable ? { transform: 'scale(1.1)', boxShadow: 3 } : {},
                }}
              >
                <BedIcon sx={{ fontSize: 16, color: bedColor, mb: 0.2 }} />
                <Typography variant="caption" fontWeight={700} sx={{ color: bedColor, lineHeight: 1, fontSize: 10 }}>
                  {bed.bett_nummer}
                </Typography>
                {isBelegt && bed.azr_id && (
                  <Typography sx={{ fontSize: 7, color: bedColor, lineHeight: 1, maxWidth: 52, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', px: 0.3 }}>
                    {bed.azr_id.slice(-6)}
                  </Typography>
                )}
                {isVorgemerkt && bed.reservation_azr_id && (
                  <Typography sx={{ fontSize: 7, color: '#0d47a1', lineHeight: 1, maxWidth: 52, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', px: 0.3 }}>
                    {bed.reservation_azr_id.slice(-6)}
                  </Typography>
                )}
              </Box>
            </Tooltip>
          )
        })}
      </Box>

      <Box display="flex" gap={2} mt={1.5} flexWrap="wrap">
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#43a047' }} />
          <Typography variant="caption" color="text.secondary">Frei{canEdit && ' (klicken)'}</Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#e53935' }} />
          <Typography variant="caption" color="text.secondary">Belegt{canEdit && ' (klicken)'}</Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#fff3e0', border: '1.5px dashed #fb8c00' }} />
          <Typography variant="caption" color="text.secondary">Verlegungsanfrage läuft</Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#e3f2fd', border: '1.5px dashed #1565c0' }} />
          <Typography variant="caption" color="text.secondary">Verlegung genehmigt</Typography>
        </Box>
        {vorgemerkt > 0 && (
          <Box display="flex" alignItems="center" gap={0.5}>
            <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#e3f2fd', border: '1.5px dashed #1565c0' }} />
            <Typography variant="caption" color="text.secondary">Vorgemerkt (Eincheck ausst.){canEdit && ' (zur Reservierung)'}</Typography>
          </Box>
        )}
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: 0.5, border: '1.5px dashed #ab47bc' }} />
          <Typography variant="caption" color="text.secondary">Anfrage-Zielbett</Typography>
        </Box>
      </Box>
    </Paper>
  )
}

export default function Drilldown() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const highlightBedId = searchParams.get('highlight_bed')
  const { get, post, patch, del } = useApiClient()
  const { keycloak } = useKeycloak()
  const { count: sseCount } = useSseNotifications()

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
  const [addingRoom, setAddingRoom] = useState(false)
  const [newWarteRoomName, setNewWarteRoomName] = useState('')
  const [addingWarteRoom, setAddingWarteRoom] = useState(false)
  const [addBedRoomId, setAddBedRoomId] = useState<string | null>(null)
  const [newBedNummer, setNewBedNummer] = useState('')
  const [newBedTyp, setNewBedTyp] = useState('KONTINGENT')
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
  const [checkoutGrund, setCheckoutGrund] = useState('')
  const [managePeriodEnde, setManagePeriodEnde] = useState('')
  const [managePeriodSaving, setManagePeriodSaving] = useState(false)

  // Intern verlegen Dialog
  const [verlegenOpen, setVerlegenOpen] = useState(false)
  const [verlegenTargetBed, setVerlegenTargetBed] = useState('')
  const [verlegenSaving, setVerlegenSaving] = useState(false)
  const [verlegenMismatch, setVerlegenMismatch] = useState(false)
  const [verlegenMismatchGrund, setVerlegenMismatchGrund] = useState('')
  const [verlegenGrund, setVerlegenGrund] = useState('')

  // Pending requests assignment dialog
  const [pendingRequests, setPendingRequests] = useState<PendingReservation[]>([])
  const [pendingOpen, setPendingOpen] = useState(false)
  const [pendingLoading, setPendingLoading] = useState(false)
  const [assignBed, setAssignBed] = useState<BedStatus | null>(null)

  // Verlegungsanfrage-Dialog (kontextsensitiv)
  const [transferDialogBed, setTransferDialogBed] = useState<BedStatus | null>(null)
  const [transferDialogDetail, setTransferDialogDetail] = useState<TransferReservationDetail | null>(null)
  const [transferDialogLoading, setTransferDialogLoading] = useState(false)
  const [transferDialogSaving, setTransferDialogSaving] = useState(false)
  const [stornierGrund, setStornierGrund] = useState('')

  // Mehrfachauswahl Wartebereich
  const [multiSelect, setMultiSelect] = useState(false)
  const [selectedAnkunftBeds, setSelectedAnkunftBeds] = useState<Set<string>>(new Set())

  // Edit dialog extra fields
  const [editLat, setEditLat] = useState('')
  const [editLon, setEditLon] = useState('')
  const [editLocLabels, setEditLocLabels] = useState<string[]>([])
  const [editValidFrom, setEditValidFrom] = useState('')
  const [editValidUntil, setEditValidUntil] = useState('')

  // Bed timed deactivation
  const [deaktBedId, setDeaktBedId] = useState<string | null>(null)
  const [deaktDate, setDeaktDate] = useState('')
  const [deaktSaving, setDeaktSaving] = useState(false)
  const [validFromBedId, setValidFromBedId] = useState<string | null>(null)
  const [validFromDate, setValidFromDate] = useState('')
  const [validFromSaving, setValidFromSaving] = useState(false)
  const [reactivateRoomId, setReactivateRoomId] = useState<string | null>(null)
  const [reactivateDate, setReactivateDate] = useState('')
  const [reactivateSaving, setReactivateSaving] = useState(false)

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

  // SSE-triggered refresh: reload bed status when a server notification arrives
  useEffect(() => {
    if (sseCount > 0) loadBedStatus()
  }, [sseCount]) // eslint-disable-line react-hooks/exhaustive-deps

  // When navigated from person search: auto-open the bed management dialog
  useEffect(() => {
    if (!highlightBedId || rooms.length === 0) return
    for (const room of rooms) {
      const bed = room.beds.find((b) => b.bed_id === highlightBedId)
      if (bed) {
        setCheckoutConfirm(false)
        setManageBed({ bed, room })
        break
      }
    }
  }, [highlightBedId, rooms]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (manageBed) {
      setManagePeriodEnde(manageBed.bed.belegung_ende ?? '')
    }
  }, [manageBed])

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
      const roomList = await get<{ id: string; name: string; geschlechts_designation: string; room_type: string; is_active: boolean; labels: string[] }[]>(
        `/api/locations/${id}/rooms?include_inactive=true`
      )
      const withBeds = await Promise.all(
        roomList.map(async (r) => {
          const beds = await get<{ id: string; bett_nummer: string; bett_typ: string; is_active: boolean; deaktiviert_ab?: string | null }[]>(
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
    setEditLat(location?.lat != null ? String(location.lat) : '')
    setEditLon(location?.lon != null ? String(location.lon) : '')
    setEditLocLabels(location?.labels ?? [])
    setEditValidFrom(location?.valid_from ?? '')
    setEditValidUntil(location?.valid_until ?? '')
    setEditTab(0)
    setEditOpen(true)
    if (isAdmin) loadMgmtRooms()
  }

  async function loadPendingRequests() {
    if (!id) return
    setPendingLoading(true)
    try {
      const res = await get<PendingReservation[]>(`/api/reservations?status=PENDING&target=mine`)
      setPendingRequests(res)
    } catch {
      setPendingRequests([])
    } finally {
      setPendingLoading(false)
    }
  }

  function openPendingRequests() {
    setPendingOpen(true)
    loadPendingRequests()
  }

  async function saveEdit() {
    if (!id) return
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        kontingent: Number(editKontingent),
        notbett_kapazitaet: Number(editNotbett),
        adresse: editAdresse,
        labels: editLocLabels,
      }
      if (editLat !== '') body.lat = parseFloat(editLat)
      if (editLon !== '') body.lon = parseFloat(editLon)
      if (editValidFrom !== '') body.valid_from = editValidFrom
      if (editValidUntil !== '') body.valid_until = editValidUntil
      const updated = await patch<Location>(`/api/locations/${id}`, body)
      setLocation(updated)
      setEditOpen(false)
      setSnackbar({ open: true, message: 'Einrichtung aktualisiert.', severity: 'success' })
    } catch (err: unknown) {
      const detail = (err as { detail?: { detail?: string } }).detail?.detail
      setSnackbar({ open: true, message: detail ?? 'Speichern fehlgeschlagen.', severity: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleAddRoom() {
    if (!id || !newRoomName.trim()) return
    setAddingRoom(true)
    try {
      await post(`/api/locations/${id}/rooms`, { name: newRoomName, geschlechts_designation: 'D', room_type: 'STANDARD' })
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

  async function handleAddWarteRoom() {
    if (!id || !newWarteRoomName.trim()) return
    setAddingWarteRoom(true)
    try {
      await post(`/api/locations/${id}/rooms`, { name: newWarteRoomName, geschlechts_designation: 'D', room_type: 'WARTEBEREICH' })
      setNewWarteRoomName('')
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Wartebereich "${newWarteRoomName}" angelegt.`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Wartebereich anlegen fehlgeschlagen.', severity: 'error' })
    } finally {
      setAddingWarteRoom(false)
    }
  }

  async function handleReactivateRoom() {
    if (!reactivateRoomId) return
    setReactivateSaving(true)
    try {
      await post(`/api/rooms/${reactivateRoomId}/activate`, {
        valid_from: reactivateDate || undefined,
      })
      setReactivateRoomId(null)
      setReactivateDate('')
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: 'Raum reaktiviert.', severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Reaktivierung fehlgeschlagen.', severity: 'error' })
    } finally {
      setReactivateSaving(false)
    }
  }

  async function handleDeactivateRoom(roomId: string, roomName: string) {
    try {
      await del(`/api/rooms/${roomId}`)
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Raum "${roomName}" deaktiviert.`, severity: 'success' })
    } catch (err: unknown) {
      const msg = extractApiError(err)
      setSnackbar({ open: true, message: msg, severity: 'error' })
    }
  }

  async function handleAddBed(roomId: string, isWarte = false) {
    if (!newBedNummer.trim()) return
    setAddingBed(true)
    const typ = isWarte ? 'WARTEPLATZ' : newBedTyp
    try {
      await post(`/api/rooms/${roomId}/beds`, { bett_nummer: newBedNummer, bett_typ: typ })
      setAddBedRoomId(null)
      setNewBedNummer('')
      setNewBedTyp('KONTINGENT')
      await loadMgmtRooms()
      loadBedStatus()
    } catch {
      setSnackbar({ open: true, message: 'Platz hinzufügen fehlgeschlagen.', severity: 'error' })
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

  async function handleExtendNotbett(occupancyId: string) {
    try {
      await post(`/api/occupants/${occupancyId}/extend`, {})
      loadBedStatus()
      setSnackbar({ open: true, message: 'Notbett um 1 Tag verlängert.', severity: 'success' })
    } catch (err: unknown) {
      setSnackbar({ open: true, message: extractApiError(err), severity: 'error' })
    }
  }

  async function handleDeaktiviereBedTimed() {
    if (!deaktBedId || !deaktDate) return
    setDeaktSaving(true)
    try {
      await patch(`/api/beds/${deaktBedId}/deactivate`, { deaktiviert_ab: deaktDate })
      setDeaktBedId(null)
      setDeaktDate('')
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Bett-Deaktivierung ab ${deaktDate} gesetzt.`, severity: 'success' })
    } catch (err: unknown) {
      const detail = (err as { detail?: { detail?: string } }).detail?.detail ?? 'Fehler beim Setzen des Deaktivierungsdatums.'
      setSnackbar({ open: true, message: detail, severity: 'error' })
    } finally {
      setDeaktSaving(false)
    }
  }

  async function handleSetBedValidFrom() {
    if (!validFromBedId || !validFromDate) return
    setValidFromSaving(true)
    try {
      await patch(`/api/beds/${validFromBedId}/validity`, { valid_from: validFromDate })
      setValidFromBedId(null)
      setValidFromDate('')
      await loadMgmtRooms()
      loadBedStatus()
      setSnackbar({ open: true, message: `Bett verfügbar ab ${validFromDate} gesetzt.`, severity: 'success' })
    } catch (err: unknown) {
      const detail = (err as { detail?: { detail?: string } }).detail?.detail ?? 'Fehler beim Setzen des Verfügbarkeitsdatums.'
      setSnackbar({ open: true, message: detail, severity: 'error' })
    } finally {
      setValidFromSaving(false)
    }
  }

  useEffect(() => {
    if (!transferDialogBed) return
    const reservationId = transferDialogBed.outgoing_reservation_id
    if (!reservationId) return
    setTransferDialogLoading(true)
    fetch(`/api/reservations/${reservationId}`, {
      headers: {
        Authorization: `Bearer ${keycloak?.token ?? ''}`,
        ...(id ? { 'X-Location-Id': id } : {}),
      },
    })
      .then((r) => r.json())
      .then((data) => setTransferDialogDetail(data as TransferReservationDetail))
      .catch(() => setTransferDialogDetail(null))
      .finally(() => setTransferDialogLoading(false))
  }, [transferDialogBed]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleStornieren() {
    if (!transferDialogDetail || !stornierGrund.trim()) return
    setTransferDialogSaving(true)
    try {
      const resp = await fetch(`/api/reservations/${transferDialogDetail.id}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${keycloak?.token ?? ''}`,
          ...(id ? { 'X-Location-Id': id } : {}),
        },
        body: JSON.stringify({ grund: stornierGrund.trim() }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw { detail: (err as { detail?: string }).detail ?? 'Stornierung fehlgeschlagen.' }
      }
      setTransferDialogBed(null)
      setTransferDialogDetail(null)
      setStornierGrund('')
      loadBedStatus()
      setSnackbar({ open: true, message: 'Verlegungsanfrage erfolgreich storniert.', severity: 'success' })
    } catch (err: unknown) {
      setSnackbar({ open: true, message: extractApiError(err), severity: 'error' })
    } finally {
      setTransferDialogSaving(false)
    }
  }

  function handleBedClick(bed: BedStatus, room: RoomStatus) {
    if (bed.pending_reservation_id && bed.status === 'FREI') {
      navigate(`/reservations?highlight=${bed.pending_reservation_id}`)
      return
    }
    if ((bed.has_pending_transfer || bed.has_confirmed_transfer) && bed.status === 'BELEGT' && bed.outgoing_reservation_id) {
      setStornierGrund('')
      setTransferDialogDetail(null)
      setTransferDialogBed(bed)
      return
    }
    if (bed.status === 'FREI') {
      const roomGender = deriveRoomGender(room)
      setBelegGeschlecht(roomGender === 'D' ? 'M' : roomGender)
      setAzrId('')
      setAliasId('')
      setBelegStart(today)
      // Notbett: max 1 Tag — Enddatum automatisch auf morgen setzen
      const in1 = new Date(Date.now() + 1 * 86400000).toISOString().slice(0, 10)
      setBelegEnde(bed.is_notbett ? in1 : in14)
      setBelegLabels([])
      setWarn12w(false)
      setBelegBed({ bed, room })
    } else if (bed.status === 'VORGEMERKT') {
      if (bed.reservation_id) navigate(`/reservations?highlight=${bed.reservation_id}`)
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
      const occupancyData = await response.clone().json().catch(() => null) as { id?: string } | null
      // Labels für die neue Belegung setzen (wenn angegeben)
      if (belegLabels.length > 0 && occupancyData?.id) {
        await patch(`/api/occupancy/${occupancyData.id}/labels`, { labels: belegLabels }).catch(() => {})
      }
      // Geschlechts-Label am Raum automatisch setzen, wenn noch keins vorhanden
      const roomId = belegBed.room.room_id
      const existingLabels = belegBed.room.labels ?? []
      const hasGenderLabel = existingLabels.some((l) => ['Männer', 'Frauen', 'Gemischt'].includes(l))
      if (!hasGenderLabel && (belegGeschlecht === 'M' || belegGeschlecht === 'W')) {
        const genderLabel = belegGeschlecht === 'M' ? 'Männer' : 'Frauen'
        await patch(`/api/rooms/${roomId}/labels`, { labels: [...existingLabels, genderLabel] }).catch(() => {})
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
    if (!manageBed?.bed.occupancy_id || !checkoutGrund.trim()) return
    setCheckoutSaving(true)
    try {
      const groundParam = encodeURIComponent(checkoutGrund.trim())
      await del(`/api/beds/${manageBed.bed.bed_id}/occupancy/${manageBed.bed.occupancy_id}?grund=${groundParam}`)
      setManageBed(null)
      setCheckoutConfirm(false)
      setCheckoutGrund('')
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
    const targetBedInfo = freiBeds.find((b) => b.bed_id === verlegenTargetBed)
    let verlBelegStart = src.belegung_start ?? today
    let verlBelegEnde = src.belegung_ende ?? in14
    if (targetBedInfo?.is_notbett) {
      verlBelegStart = today
      const d = new Date(Date.now() + 86400000)
      verlBelegEnde = d.toISOString().slice(0, 10)
    }
    // Geschlecht-Mismatch: Ziel-Raum hat andere Designation als Person → erst bestätigen lassen
    const personGeschlecht = src.occ_geschlecht ?? 'D'
    const raumGeschlecht = targetBedInfo?.geschlecht ?? 'D'
    if (!verlegenMismatch && raumGeschlecht !== 'D' && raumGeschlecht !== personGeschlecht) {
      setVerlegenMismatch(true)
      setVerlegenSaving(false)
      return
    }
    try {
      await post(`/api/beds/${verlegenTargetBed}/occupancy`, {
        azr_id: src.azr_id,
        alias_id: src.alias_id || null,
        geschlecht: src.occ_geschlecht || 'M',
        belegung_start: verlBelegStart,
        belegung_ende: verlBelegEnde,
        ...(verlegenMismatch && verlegenMismatchGrund.trim()
          ? { geschlecht_mismatch_grund: verlegenMismatchGrund.trim() }
          : {}),
        ...(verlegenGrund.trim() ? { verlegung_grund: verlegenGrund.trim() } : {}),
      })
      await del(`/api/beds/${src.bed_id}/occupancy/${src.occupancy_id}`)
      setVerlegenOpen(false)
      setManageBed(null)
      setVerlegenMismatch(false)
      setVerlegenMismatchGrund('')
      setVerlegenGrund('')
      loadBedStatus()
      setSnackbar({ open: true, message: 'Person erfolgreich verlegt.', severity: 'success' })
    } catch (err: unknown) {
      if ((err as { status?: number }).status === 404) {
        setSnackbar({ open: true, message: 'Bett nicht mehr verfügbar — bitte Seite aktualisieren.', severity: 'error' })
      } else {
        setSnackbar({ open: true, message: extractApiError(err), severity: 'error' })
      }
    } finally {
      setVerlegenSaving(false)
    }
  }

  async function handleUpdatePeriod() {
    if (!manageBed?.bed.occupancy_id || !managePeriodEnde) return
    const origStart = manageBed.bed.belegung_start ?? ''
    if (managePeriodEnde <= origStart) return
    setManagePeriodSaving(true)
    try {
      await patch(`/api/occupancy/${manageBed.bed.occupancy_id}/period`, {
        belegung_start: origStart,
        belegung_ende: managePeriodEnde,
      })
      loadBedStatus()
      setSnackbar({ open: true, message: 'Belegungszeitraum aktualisiert.', severity: 'success' })
    } catch (err: unknown) {
      setSnackbar({ open: true, message: extractApiError(err), severity: 'error' })
    } finally {
      setManagePeriodSaving(false)
    }
  }

  function openVerlegung(bed?: BedStatus) {
    if (bed?.azr_id) {
      navigate(`/suggestions?azrId=${encodeURIComponent(bed.azr_id)}&geschlecht=${bed.occ_geschlecht ?? 'M'}&cross=1`)
    } else {
      navigate('/suggestions?cross=1')
    }
    setManageBed(null)
  }

  function toggleAnkunftSelect(bedId: string) {
    setSelectedAnkunftBeds((prev) => {
      const next = new Set(prev)
      if (next.has(bedId)) next.delete(bedId)
      else next.add(bedId)
      return next
    })
  }

  function openGruppenVerlegung(ankunftRooms: RoomStatus[]) {
    const persons: string[] = []
    for (const room of ankunftRooms) {
      for (const bed of room.beds) {
        if (selectedAnkunftBeds.has(bed.bed_id) && bed.azr_id) {
          persons.push(`${bed.azr_id}:${bed.occ_geschlecht ?? 'M'}`)
        }
      }
    }
    if (persons.length === 0) return
    navigate(`/suggestions?group=${encodeURIComponent(persons.join(','))}&cross=1`)
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
              { label: 'Kontingent', value: location.kontingent, help: 'EU-quotenrelevante Gesamtkapazität dieser Einrichtung.' },
              { label: 'Notbetten', value: location.notbett_kapazitaet, help: 'Temporäre Plätze für max. 1 Nacht — nicht EU-quotenrelevant.' },
              { label: 'Frei', value: totalFrei, color: '#a5d6a7' },
              { label: 'Belegt', value: totalBelegt, color: '#ef9a9a' },
            ].map(({ label, value, color, help }) => (
              <Box key={label} sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight={800} sx={{ color: color ?? 'white', lineHeight: 1 }}>
                  {value}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  {label}{help && <HelpTooltip text={help} />}
                </Typography>
              </Box>
            ))}
            {totalPending > 0 && (
              <Box
                sx={{ textAlign: 'center', cursor: canEdit ? 'pointer' : 'default', '&:hover': canEdit ? { opacity: 0.8 } : {} }}
                onClick={canEdit ? openPendingRequests : undefined}
              >
                <Typography variant="h4" fontWeight={800} sx={{ color: '#ffcc80', lineHeight: 1 }}>
                  {totalPending}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  {canEdit ? '▶ Anfragen' : 'Anfragen'}
                </Typography>
              </Box>
            )}
            <Box sx={{ ml: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <Typography variant="caption" sx={{ opacity: 0.6, mb: 0.5 }}>30-Tage-Auslastung</Typography>
              <BelegungSparkline locationId={id!} />
            </Box>
          </Box>
        </Paper>
      )}

      {/* Date Range Filter */}
      <Paper elevation={0} sx={{ p: 2, mb: 3, borderRadius: 2, border: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="body2" fontWeight={600} color="text.secondary">Belegung für:</Typography>
        <TextField label="Von" type="date" size="small" value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); if (e.target.value >= dateTo) setDateTo(e.target.value); if (highlightBedId) setSearchParams({}) }}
          InputLabelProps={{ shrink: true }} sx={{ width: 160 }} />
        <TextField label="Bis" type="date" size="small" value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); if (highlightBedId) setSearchParams({}) }}
          InputLabelProps={{ shrink: true }} inputProps={{ min: dateFrom }} sx={{ width: 160 }} />
        <Button variant="outlined" size="small" onClick={() => { setDateFrom(today); setDateTo(in14); if (highlightBedId) setSearchParams({}) }}>
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
            onClick={() => openVerlegung()}
            sx={{ ml: 'auto', bgcolor: '#6a1b9a', '&:hover': { bgcolor: '#4a148c' } }}>
            Verlegungsanfrage
          </Button>
        )}
      </Paper>

      {/* Bed Grid */}
      {loading ? (
        <Box display="flex" justifyContent="center" mt={6}><CircularProgress /></Box>
      ) : rooms.length === 0 ? (
        <Alert severity="info">Keine Räume für diese Einrichtung gefunden.</Alert>
      ) : (() => {
        const ankunftRooms = rooms.filter((r) => r.room_type === 'WARTEBEREICH')
        const notbettRooms = rooms.filter((r) => r.room_type !== 'WARTEBEREICH' && r.beds.some((b) => b.is_notbett))
        const kontingentRooms = rooms.filter((r) => r.room_type !== 'WARTEBEREICH' && !r.beds.some((b) => b.is_notbett))
        return (
          <>
            {/* Wartebereich */}
            {ankunftRooms.length > 0 && (
              <Box mb={4}>
                <Box display="flex" alignItems="center" gap={1} mb={2} flexWrap="wrap">
                  <ChairAltIcon sx={{ color: '#e65100' }} />
                  <Typography variant="h6" fontWeight={700} sx={{ color: '#e65100' }}>
                    Wartebereich
                  </Typography>
                  <Chip label="Warteplätze — nicht im Kontingent" size="small"
                    sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600 }} />
                  <Box sx={{ flexGrow: 1 }} />
                  {canEdit && (
                    <Button size="small" variant={multiSelect ? 'contained' : 'outlined'}
                      startIcon={multiSelect ? <CheckBoxIcon /> : <CheckBoxOutlineBlankIcon />}
                      sx={multiSelect
                        ? { bgcolor: '#e65100', '&:hover': { bgcolor: '#bf360c' } }
                        : { borderColor: '#e65100', color: '#e65100' }}
                      onClick={() => { setMultiSelect((v) => !v); setSelectedAnkunftBeds(new Set()) }}>
                      {multiSelect ? 'Auswahl aufheben' : 'Gruppe auswählen'}
                    </Button>
                  )}
                  {multiSelect && selectedAnkunftBeds.size > 0 && (
                    <Button size="small" variant="contained"
                      startIcon={<SwapHorizIcon />}
                      sx={{ bgcolor: '#6a1b9a', '&:hover': { bgcolor: '#4a148c' } }}
                      onClick={() => openGruppenVerlegung(ankunftRooms)}>
                      {selectedAnkunftBeds.size} Personen verlegen
                    </Button>
                  )}
                </Box>
                <Paper elevation={0} sx={{ p: 2.5, borderRadius: 3, bgcolor: '#fff8f0', border: '2px solid #ffcc80' }}>
                  {ankunftRooms.map((room) => (
                    <Box key={room.room_id} mb={2}>
                      <Typography variant="subtitle2" fontWeight={700} sx={{ color: '#e65100', mb: 1 }}>
                        {room.room_name}
                      </Typography>
                      <Box display="flex" flexWrap="wrap" gap={1}>
                        {room.beds.map((bed) => {
                          const isBelegt = bed.status === 'BELEGT'
                          const isSelected = selectedAnkunftBeds.has(bed.bed_id)
                          const hasPendingTransferAnk = isBelegt && !!bed.has_pending_transfer
                          return (
                            <Tooltip key={bed.bed_id} arrow title={
                              isBelegt
                                ? `${bed.azr_id} · ${bed.belegung_start} – ${bed.belegung_ende}${hasPendingTransferAnk ? ' · Verlegungsanfrage läuft' : ''}`
                                : 'Warteplatz frei'
                            }>
                              <Box
                                onClick={() => {
                                  if (multiSelect && isBelegt) { toggleAnkunftSelect(bed.bed_id); return }
                                  handleBedClick(bed, room)
                                }}
                                sx={{
                                  position: 'relative',
                                  width: 68, height: 68, borderRadius: 2, display: 'flex', flexDirection: 'column',
                                  alignItems: 'center', justifyContent: 'center', cursor: canEdit ? 'pointer' : 'default',
                                  bgcolor: isSelected ? '#ede7f6' : hasPendingTransferAnk ? '#f3e5f5' : isBelegt ? '#fff3e0' : '#f1f8e9',
                                  border: isSelected ? '2px solid #6a1b9a'
                                    : hasPendingTransferAnk ? '2px dashed #9c27b0'
                                    : isBelegt ? '2px solid #ff9800'
                                    : '2px solid #aed581',
                                  transition: 'all 0.15s',
                                  '&:hover': canEdit ? { transform: 'scale(1.05)', boxShadow: 2 } : {},
                                }}
                              >
                                <ChairAltIcon sx={{ fontSize: 18, color: isSelected ? '#6a1b9a' : hasPendingTransferAnk ? '#7b1fa2' : isBelegt ? '#e65100' : '#7cb342', mb: 0.2 }} />
                                <Typography variant="caption" fontWeight={700}
                                  sx={{ fontSize: 9, color: isSelected ? '#6a1b9a' : hasPendingTransferAnk ? '#7b1fa2' : isBelegt ? '#e65100' : '#7cb342', lineHeight: 1 }}>
                                  {bed.bett_nummer}
                                </Typography>
                                {isBelegt && bed.azr_id && (
                                  <Typography sx={{ fontSize: 7, color: hasPendingTransferAnk ? '#7b1fa2' : '#e65100', lineHeight: 1, maxWidth: 62, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', px: 0.3 }}>
                                    {bed.azr_id.slice(-6)}
                                  </Typography>
                                )}
                                {hasPendingTransferAnk && (
                                  <Box sx={{ position: 'absolute', top: 3, right: 3, width: 8, height: 8, borderRadius: '50%', bgcolor: '#6a1b9a', border: '1.5px solid white' }} />
                                )}
                              </Box>
                            </Tooltip>
                          )
                        })}
                      </Box>
                    </Box>
                  ))}
                  <Box display="flex" gap={2} mt={1} flexWrap="wrap">
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#ff9800' }} />
                      <Typography variant="caption" color="text.secondary">Belegt</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <Box sx={{ width: 10, height: 10, borderRadius: 0.5, border: '1.5px dashed #9c27b0', bgcolor: '#f3e5f5' }} />
                      <Typography variant="caption" color="text.secondary">Verlegungsanfrage läuft</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={0.5}>
                      <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: '#aed581' }} />
                      <Typography variant="caption" color="text.secondary">Frei</Typography>
                    </Box>
                  </Box>
                </Paper>
              </Box>
            )}

            <Grid container spacing={3}>
              {kontingentRooms.map((room) => (
                <Grid item xs={12} md={6} key={room.room_id}>
                  <BedGrid room={room} canEdit={canEdit} onBedClick={handleBedClick} refDate={dateFrom} />
                </Grid>
              ))}
            </Grid>

            {notbettRooms.length > 0 && (
              <Box mt={4}>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <Typography variant="h6" fontWeight={700} color="warning.dark">
                    Notbetten
                  </Typography>
                  <Chip label="Max. 1 Tag · Kurzzeitunterbringung" size="small"
                    sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600 }} />
                </Box>
                <Grid container spacing={3}>
                  {notbettRooms.map((room) => (
                    <Grid item xs={12} md={6} key={room.room_id}>
                      <Paper elevation={2} sx={{ p: 2.5, borderRadius: 3, borderTop: '4px solid #ff9800' }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1.5}>
                          <Typography fontWeight={700} color="warning.dark">{room.room_name}</Typography>
                          <Box sx={{ flexGrow: 1 }} />
                          <Typography variant="caption" color="text.secondary">
                            {room.beds.filter((b) => b.status === 'FREI').length} frei ·{' '}
                            {room.beds.filter((b) => b.status === 'BELEGT').length} belegt
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                          {room.beds.map((bed) => {
                            const isBelegt = bed.status === 'BELEGT'
                            return (
                              <Box key={bed.bed_id} display="flex" flexDirection="column" alignItems="center" gap={0.5}>
                                <Tooltip
                                  title={isBelegt
                                    ? `${bed.azr_id ?? '–'} · ${bed.belegung_start} – ${bed.belegung_ende} · Max. 1 Tag!`
                                    : 'Notbett frei · Max. 1 Tag Belegung'}
                                  arrow>
                                  <Box onClick={() => canEdit && handleBedClick(bed, room)}
                                    sx={{
                                      width: 58, height: 58, borderRadius: 1.5,
                                      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                      bgcolor: isBelegt ? '#fff3e0' : '#f1f8e9',
                                      border: `2px solid ${isBelegt ? '#ff9800' : '#8bc34a'}`,
                                      cursor: canEdit ? 'pointer' : 'default',
                                      '&:hover': canEdit ? { transform: 'scale(1.1)', boxShadow: 3 } : {},
                                    }}>
                                    <BedIcon sx={{ fontSize: 16, color: isBelegt ? '#e65100' : '#558b2f', mb: 0.2 }} />
                                    <Typography variant="caption" fontWeight={700}
                                      sx={{ color: isBelegt ? '#e65100' : '#558b2f', lineHeight: 1, fontSize: 10 }}>
                                      N{bed.bett_nummer}
                                    </Typography>
                                    {isBelegt && bed.azr_id && (
                                      <Typography sx={{ fontSize: 7, color: '#e65100', lineHeight: 1, maxWidth: 52, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', px: 0.3 }}>
                                        {bed.azr_id.slice(-6)}
                                      </Typography>
                                    )}
                                  </Box>
                                </Tooltip>
                                {canEdit && isBelegt && !bed.extended_once && bed.occupancy_id && (
                                  <Button size="small" variant="outlined" color="warning"
                                    sx={{ fontSize: 9, px: 0.5, py: 0.2, minWidth: 0 }}
                                    onClick={() => handleExtendNotbett(bed.occupancy_id!)}>
                                    +1 Tag
                                  </Button>
                                )}
                              </Box>
                            )
                          })}
                        </Box>
                        <Alert severity="warning" sx={{ mt: 1.5, py: 0.5, fontSize: 11 }}>
                          Notbetten sind temporäre Plätze. Tägliche Postkorb-Meldung bei belegten Notbetten.
                        </Alert>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}
          </>
        )
      })()}

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
            label={<>AZR-ID *<HelpTooltip text="Ausländerzentralregister-Nummer der Person. Keine Personennamen werden gespeichert (DSGVO)." /></>}
            value={azrId}
            onChange={(e) => setAzrId(e.target.value)}
            placeholder="z.B. AZR-2024-FFM-M01"
            fullWidth required
          />
          <TextField
            label={<>Alias-ID (optional)<HelpTooltip text="Einrichtungsinterne Kennung — erleichtert die Suche ohne vollständige AZR-ID." /></>}
            value={aliasId}
            onChange={(e) => setAliasId(e.target.value)}
            placeholder="z.B. AL-M-001"
            fullWidth
          />
          {belegBed && deriveRoomGender(belegBed.room) === 'D' && (
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
            <TextField label="Belegung von (heute)" type="date" size="small" value={belegStart}
              InputLabelProps={{ shrink: true }} fullWidth
              inputProps={{ readOnly: true, style: { color: '#666', cursor: 'default' } }}
              sx={{ '& fieldset': { borderColor: '#e0e0e0' }, bgcolor: '#fafafa' }} />
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

          {belegBed?.bed.is_notbett && (
            <Alert severity="info">Notbett: Belegung auf max. 1 Nacht begrenzt — Enddatum wurde automatisch gesetzt.</Alert>
          )}
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
                  <Box mt={0.5}>
                    <Chip
                      label={manageBed.bed.occ_geschlecht === 'M' ? 'Männer' : manageBed.bed.occ_geschlecht === 'W' ? 'Frauen' : 'Divers'}
                      size="small"
                      sx={{ bgcolor: genderColor(manageBed.bed.occ_geschlecht ?? 'D') + '20', color: genderColor(manageBed.bed.occ_geschlecht ?? 'D'), fontWeight: 600 }}
                    />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Belegungszeitraum</Typography>
                  <Box display="flex" alignItems="center" gap={0.5} mt={0.3} flexWrap="wrap">
                    <Typography sx={{ fontSize: 12, fontWeight: 600, px: 0.5 }}>
                      {manageBed.bed.belegung_start}
                    </Typography>
                    <Typography variant="caption">–</Typography>
                    <TextField size="small" type="date" value={managePeriodEnde}
                      onChange={(e) => setManagePeriodEnde(e.target.value)}
                      inputProps={{ min: manageBed.bed.belegung_start ?? '', style: { fontSize: 12, padding: '4px 6px' } }}
                      error={!!managePeriodEnde && !!manageBed.bed.belegung_start && managePeriodEnde <= manageBed.bed.belegung_start}
                      sx={{ width: 136 }} />
                    {managePeriodEnde !== (manageBed.bed.belegung_ende ?? '') &&
                      managePeriodEnde > (manageBed.bed.belegung_start ?? '') && (
                      <Button size="small" variant="outlined" onClick={handleUpdatePeriod} disabled={managePeriodSaving}
                        sx={{ fontSize: 11, py: 0.3, px: 1, minWidth: 0 }}>
                        {managePeriodSaving ? <CircularProgress size={12} /> : 'OK'}
                      </Button>
                    )}
                  </Box>
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
                    onSaved={() => { loadBedStatus() }}
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
              <Button fullWidth variant="outlined" startIcon={<SwapHorizIcon />}
                sx={{ borderColor: '#6a1b9a', color: '#6a1b9a', '&:hover': { borderColor: '#4a148c', bgcolor: '#f3e5f5' } }}
                onClick={() => openVerlegung(manageBed?.bed)}>
                Zu anderer Einrichtung verlegen (Verlegungsanfrage)
              </Button>
            </Box>
          ) : (
            <Box display="flex" flexDirection="column" gap={1.5}>
              <Alert severity="warning">
                Belegung für <strong>{manageBed?.bed.azr_id}</strong> wirklich beenden?
              </Alert>
              <TextField
                label="Grund für Ausbuchen *"
                value={checkoutGrund}
                onChange={(e) => setCheckoutGrund(e.target.value)}
                fullWidth
                size="small"
                multiline
                rows={2}
                placeholder="z.B. Freiwillige Ausreise, Weiterverlegung extern, …"
                required
              />
              <Box display="flex" gap={1}>
                <Button size="small" color="error" variant="contained"
                  disabled={checkoutSaving || !checkoutGrund.trim()}
                  onClick={handleAusbuchen}>
                  {checkoutSaving ? <CircularProgress size={16} /> : 'Ausbuchen'}
                </Button>
                <Button size="small" onClick={() => { setCheckoutConfirm(false); setCheckoutGrund('') }}>Abbrechen</Button>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setManageBed(null); setCheckoutConfirm(false) }}>Schließen</Button>
        </DialogActions>
      </Dialog>

      {/* ── Intern verlegen Dialog ── */}
      <Dialog open={verlegenOpen} onClose={() => { setVerlegenOpen(false); setVerlegenMismatch(false); setVerlegenMismatchGrund(''); setVerlegenGrund('') }} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>Intern verlegen — Zielbett wählen</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {verlegenMismatch ? (
            <Box display="flex" flexDirection="column" gap={2}>
              <Alert severity="warning" icon={<WarningAmberIcon />}>
                <strong>Geschlecht-Warnung:</strong> Die Person ({manageBed?.bed.occ_geschlecht ?? '?'}) wird in einen Raum verlegt, der für{' '}
                {genderLabel(freiBeds.find((b) => b.bed_id === verlegenTargetBed)?.geschlecht ?? 'D')} vorgesehen ist. Bitte Begründung angeben.
              </Alert>
              <TextField
                label="Begründung *"
                multiline
                minRows={2}
                fullWidth
                value={verlegenMismatchGrund}
                onChange={(e) => setVerlegenMismatchGrund(e.target.value)}
                placeholder="z.B. Notsituation, keine anderen Betten verfügbar..."
                autoFocus
              />
            </Box>
          ) : freiBeds.filter((b) => b.bed_id !== manageBed?.bed.bed_id).length === 0 ? (
            <Alert severity="warning">Keine freien Betten in dieser Einrichtung verfügbar.</Alert>
          ) : (
            <Box>
              {verlegenTargetBed && freiBeds.find((b) => b.bed_id === verlegenTargetBed)?.is_notbett && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Notbett: Belegung wird auf heute + 1 Nacht angepasst (max. 1 Tag).
                </Alert>
              )}
              {verlegenTargetBed && freiBeds.find((b) => b.bed_id === verlegenTargetBed)?.bett_typ === 'WARTEPLATZ' && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Warteplatz: Person wird in den Wartebereich verlegt.
                </Alert>
              )}
              <Typography variant="body2" color="text.secondary" mb={2}>
                Freie Plätze und Betten in dieser Einrichtung:
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                {freiBeds.filter((b) => b.bed_id !== manageBed?.bed.bed_id).map((b) => (
                  <Paper
                    key={b.bed_id}
                    elevation={verlegenTargetBed === b.bed_id ? 4 : 1}
                    onClick={() => { setVerlegenTargetBed(b.bed_id); setVerlegenMismatch(false); setVerlegenMismatchGrund('') }}
                    sx={{
                      p: 1.5, borderRadius: 2, cursor: 'pointer',
                      border: verlegenTargetBed === b.bed_id
                        ? `2px solid ${b.is_notbett ? '#ff9800' : b.bett_typ === 'WARTEPLATZ' ? '#e65100' : '#003366'}`
                        : '2px solid transparent',
                      bgcolor: verlegenTargetBed === b.bed_id
                        ? b.is_notbett ? '#fff3e0' : b.bett_typ === 'WARTEPLATZ' ? '#fff8f0' : '#e3f2fd'
                        : 'white',
                      transition: 'all 0.15s',
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <BedIcon sx={{ color: b.is_notbett ? '#ff9800' : b.bett_typ === 'WARTEPLATZ' ? '#e65100' : '#43a047' }} />
                      <Typography fontWeight={600}>{b.room_name} — {b.bett_typ === 'WARTEPLATZ' ? 'Platz' : 'Bett'} {b.bett_nummer}</Typography>
                      {b.is_notbett && <Chip label="Notbett" size="small" sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600, height: 20 }} />}
                      {b.bett_typ === 'WARTEPLATZ' && <Chip label="Warteplatz" size="small" sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600, height: 20 }} />}
                      {b.bett_typ !== 'WARTEPLATZ' && <Chip label={genderLabel(b.geschlecht)} size="small"
                        sx={{ bgcolor: genderColor(b.geschlecht) + '15', color: genderColor(b.geschlecht) }} />}
                    </Box>
                  </Paper>
                ))}
              </Box>
              <TextField
                label="Begründung *"
                fullWidth
                sx={{ mt: 2 }}
                value={verlegenGrund}
                onChange={(e) => setVerlegenGrund(e.target.value)}
                placeholder="z.B. Raumwechsel wegen Renovierung..."
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          {verlegenMismatch ? (
            <>
              <Button onClick={() => { setVerlegenMismatch(false); setVerlegenMismatchGrund('') }}>Zurück</Button>
              <Button variant="contained" color="warning"
                disabled={!verlegenMismatchGrund.trim() || verlegenSaving}
                onClick={handleVerlegen}>
                {verlegenSaving ? <CircularProgress size={18} /> : 'Override bestätigen'}
              </Button>
            </>
          ) : (
            <>
              <Button onClick={() => { setVerlegenOpen(false); setVerlegenGrund('') }}>Abbrechen</Button>
              <Button variant="contained" disabled={!verlegenTargetBed || !verlegenGrund.trim() || verlegenSaving}
                onClick={handleVerlegen}>
                {verlegenSaving ? <CircularProgress size={18} /> : 'Verlegen bestätigen'}
              </Button>
            </>
          )}
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
              <Box display="flex" gap={2}>
                <TextField
                  label={<>Kontingent (Plätze)<HelpTooltip text="EU-quotenrelevante Gesamtkapazität. Reduktion unter aktuelle Belegung erzeugt eine Überkapazität im EU-Reporting." /></>}
                  type="number" value={editKontingent}
                  onChange={(e) => setEditKontingent(e.target.value)} inputProps={{ min: 0 }} fullWidth />
                <TextField
                  label={<>Notbett-Kapazität<HelpTooltip text="Max. gleichzeitige Notbett-Belegungen. Notbetten sind max. 1 Nacht, nicht EU-quotenrelevant." /></>}
                  type="number" value={editNotbett}
                  onChange={(e) => setEditNotbett(e.target.value)} inputProps={{ min: 0 }} fullWidth />
              </Box>
              <TextField label="Adresse" value={editAdresse}
                onChange={(e) => setEditAdresse(e.target.value)} fullWidth multiline rows={2} />
              <Box display="flex" gap={2}>
                <TextField label="Breitengrad (Lat)" type="number" value={editLat}
                  onChange={(e) => setEditLat(e.target.value)}
                  placeholder="z.B. 50.0264" fullWidth
                  helperText="Für Kartenansicht" />
                <TextField label="Längengrad (Lon)" type="number" value={editLon}
                  onChange={(e) => setEditLon(e.target.value)}
                  placeholder="z.B. 8.5431" fullWidth
                  helperText="Für Kartenansicht" />
              </Box>
              <Box display="flex" gap={2}>
                <TextField
                  label="Gültig ab"
                  type="date"
                  value={editValidFrom}
                  onChange={(e) => setEditValidFrom(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  helperText="Einrichtung aktiv ab diesem Datum"
                />
                <TextField
                  label="Gültig bis"
                  type="date"
                  value={editValidUntil}
                  onChange={(e) => setEditValidUntil(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  helperText="Einrichtung inaktiv ab diesem Datum"
                />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Einrichtungs-Labels
                </Typography>
                <LabelChips
                  labels={editLocLabels}
                  entityType="ROOM"
                  entityId="new"
                  onSaved={(l) => setEditLocLabels(l)}
                />
              </Box>
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
                        borderLeft: `4px solid ${room.is_active ? (hasGenderLabel(room.labels ?? []) ? genderColor(deriveGenderFromLabels(room.labels ?? [])) : '#bdbdbd') : '#bdbdbd'}`,
                        opacity: room.is_active ? 1 : 0.55,
                      }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                          <MeetingRoomIcon sx={{ fontSize: 18, color: room.is_active ? (room.room_type === 'WARTEBEREICH' ? '#e65100' : '#003366') : '#888' }} />
                          <Typography fontWeight={700}>{room.name}</Typography>
                          {room.room_type === 'WARTEBEREICH' && (
                            <Chip label="Wartebereich" size="small" sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600 }} />
                          )}
                          {hasGenderLabel(room.labels ?? []) && (
                            <Chip label={genderLabel(deriveGenderFromLabels(room.labels ?? []))} size="small"
                              sx={{ bgcolor: genderColor(deriveGenderFromLabels(room.labels ?? [])) + '15', color: genderColor(deriveGenderFromLabels(room.labels ?? [])) }} />
                          )}
                          {!room.is_active && <Chip label="Inaktiv" size="small" sx={{ bgcolor: '#f5f5f5', color: '#888' }} />}
                          <Box sx={{ flexGrow: 1 }} />
                          {!room.is_active && (
                            <Button size="small" variant="outlined" color="success"
                              onClick={() => { setReactivateRoomId(room.id); setReactivateDate('') }}>
                              Reaktivieren
                            </Button>
                          )}
                          {room.is_active && (
                            <>
                              <Button size="small" startIcon={<AddIcon />}
                                onClick={() => { setAddBedRoomId(room.id); setNewBedNummer(''); setNewBedTyp('KONTINGENT') }}>
                                {room.room_type === 'WARTEBEREICH' ? 'Warteplatz' : 'Bett'}
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
                            {(() => {
                              // Gender labels are locked as long as the room has active occupancies
                              const liveRoom = rooms.find((r) => r.room_id === room.id)
                              const isOccupied = liveRoom?.beds.some((b) => b.status === 'BELEGT') ?? false
                              const locked = isOccupied
                                ? (room.labels ?? []).filter((l) => GENDER_LABELS.includes(l))
                                : []
                              return (
                                <LabelChips
                                  labels={room.labels ?? []}
                                  entityType="ROOM"
                                  entityId={room.id}
                                  compact
                                  onSaved={() => loadMgmtRooms()}
                                  lockedLabels={locked}
                                  lockedTooltip="Geschlechts-Label kann erst entfernt werden, wenn der Raum vollständig leer ist."
                                />
                              )
                            })()}
                          </Box>
                        )}

                        {/* Beds */}
                        <Box display="flex" flexWrap="wrap" gap={0.8} mb={addBedRoomId === room.id ? 1.5 : 0}>
                          {room.beds.map((bed) => {
                            return (
                              <Box key={bed.id} display="flex" alignItems="center" gap={0.5}>
                                <Tooltip title={
                                  bed.deaktiviert_ab
                                    ? `Deaktivierung geplant: ${bed.deaktiviert_ab} · Klicken: Verfügbarkeit ab setzen`
                                    : bed.is_active ? 'Aktiv · Klicken: Deaktivierung planen | Rechtsklick: Verfügbar-ab setzen' : 'Inaktiv'
                                }>
                                  <Chip
                                    icon={<BedIcon sx={{ fontSize: '14px !important' }} />}
                                    label={
                                      bed.deaktiviert_ab
                                        ? `${bed.bett_nummer} (deakt. ab ${bed.deaktiviert_ab})`
                                        : bed.bett_nummer
                                    }
                                    size="small"
                                    onClick={bed.is_active && room.is_active && !bed.deaktiviert_ab
                                      ? () => { setDeaktBedId(bed.id); setDeaktDate('') }
                                      : undefined}
                                    onDelete={bed.is_active && room.is_active ? () => handleDeactivateBed(bed.id, bed.bett_nummer) : undefined}
                                    sx={{
                                      bgcolor: bed.deaktiviert_ab ? '#fff3e0' : bed.is_active ? '#e8f5e9' : '#f5f5f5',
                                      color: bed.deaktiviert_ab ? '#e65100' : bed.is_active ? '#2e7d32' : '#888',
                                      opacity: bed.is_active ? 1 : 0.6,
                                    }}
                                  />
                                </Tooltip>
                                {bed.is_active && room.is_active && (
                                  <Tooltip title="Verfügbar-ab Datum setzen">
                                    <IconButton size="small" sx={{ width: 16, height: 16, color: '#1565c0', opacity: 0.6 }}
                                      onClick={() => { setValidFromBedId(bed.id); setValidFromDate('') }}>
                                      <AddCircleIcon sx={{ fontSize: 12 }} />
                                    </IconButton>
                                  </Tooltip>
                                )}
                              </Box>
                            )
                          })}
                          {room.beds.length === 0 && (
                            <Typography variant="caption" color="text.secondary">
                              {room.room_type === 'WARTEBEREICH' ? 'Keine Warteplätze' : 'Keine Betten'}
                            </Typography>
                          )}
                        </Box>

                        {/* Add bed/Warteplatz inline form */}
                        {addBedRoomId === room.id && (
                          <Box display="flex" gap={1} alignItems="center" mt={1} flexWrap="wrap">
                            <TextField
                              label={room.room_type === 'WARTEBEREICH' ? 'Platz-Nr *' : 'Bett-Nr *'}
                              size="small" value={newBedNummer}
                              onChange={(e) => setNewBedNummer(e.target.value)}
                              sx={{ width: 100 }} />
                            {room.room_type !== 'WARTEBEREICH' && (
                              <FormControl size="small" sx={{ width: 130 }}>
                                <InputLabel>Typ</InputLabel>
                                <Select value={newBedTyp} label="Typ" onChange={(e) => setNewBedTyp(e.target.value)}>
                                  <MenuItem value="KONTINGENT">Standard</MenuItem>
                                  <MenuItem value="NOTBETT">Notbett</MenuItem>
                                </Select>
                              </FormControl>
                            )}
                            {room.room_type === 'WARTEBEREICH' && (
                              <Chip label="Typ: Warteplatz (auto)" size="small" sx={{ bgcolor: '#fff3e0', color: '#e65100' }} />
                            )}
                            <Button size="small" variant="contained" disabled={!newBedNummer.trim() || addingBed}
                              onClick={() => handleAddBed(room.id, room.room_type === 'WARTEBEREICH')}>
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
                    Neuen Wohnraum anlegen
                  </Typography>
                  <Box display="flex" gap={1.5} alignItems="flex-end" flexWrap="wrap" mb={2}>
                    <TextField label="Raumname *" size="small" value={newRoomName}
                      onChange={(e) => setNewRoomName(e.target.value)}
                      placeholder="z.B. Raum E" sx={{ flex: 1, minWidth: 150 }} />
                    <Button variant="contained" startIcon={<AddIcon />}
                      disabled={!newRoomName.trim() || addingRoom}
                      onClick={handleAddRoom}>
                      {addingRoom ? <CircularProgress size={16} /> : 'Raum anlegen'}
                    </Button>
                  </Box>

                  {/* New Wartebereich form */}
                  <Typography variant="body2" fontWeight={700} sx={{ color: '#e65100', mb: 1.5 }}>
                    Neuen Wartebereich anlegen
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    Warteplätze zählen nicht gegen das Kontingent und erhalten automatisch den Typ „Warteplatz".
                  </Typography>
                  <Box display="flex" gap={1.5} alignItems="flex-end" flexWrap="wrap">
                    <TextField label="Bereichsname *" size="small" value={newWarteRoomName}
                      onChange={(e) => setNewWarteRoomName(e.target.value)}
                      placeholder="z.B. Wartebereich" sx={{ flex: 1, minWidth: 150 }} />
                    <Button variant="contained" startIcon={<AddIcon />}
                      disabled={!newWarteRoomName.trim() || addingWarteRoom}
                      onClick={handleAddWarteRoom}
                      sx={{ bgcolor: '#e65100', '&:hover': { bgcolor: '#bf360c' } }}>
                      {addingWarteRoom ? <CircularProgress size={16} /> : 'Wartebereich anlegen'}
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

      {/* ── Bett-Deaktivierung planen Dialog ── */}
      <Dialog open={!!deaktBedId} onClose={() => setDeaktBedId(null)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight={700}>Bett-Deaktivierung planen</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Geben Sie das Datum ein, ab dem das Bett nicht mehr belegt werden soll. Bestehende Belegungen bis zu diesem Datum bleiben erhalten.
          </Typography>
          <TextField
            label="Deaktivierung ab"
            type="date"
            value={deaktDate}
            onChange={(e) => setDeaktDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
            inputProps={{ min: today }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeaktBedId(null)}>Abbrechen</Button>
          <Button
            variant="contained"
            color="warning"
            disabled={!deaktDate || deaktSaving}
            onClick={handleDeaktiviereBedTimed}
          >
            {deaktSaving ? <CircularProgress size={18} /> : 'Datum setzen'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Bett Verfügbar-ab Dialog ── */}
      <Dialog open={!!validFromBedId} onClose={() => setValidFromBedId(null)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight={700}>Bett: Verfügbar ab Datum</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Das Bett gilt bis zu diesem Datum als "geplant" und kann nicht belegt werden.
          </Typography>
          <TextField
            label="Verfügbar ab"
            type="date"
            value={validFromDate}
            onChange={(e) => setValidFromDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
            inputProps={{ min: today }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setValidFromBedId(null)}>Abbrechen</Button>
          <Button
            variant="contained"
            color="primary"
            disabled={!validFromDate || validFromSaving}
            onClick={handleSetBedValidFrom}
          >
            {validFromSaving ? <CircularProgress size={18} /> : 'Datum setzen'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Raum Reaktivieren Dialog ── */}
      <Dialog open={!!reactivateRoomId} onClose={() => setReactivateRoomId(null)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight={700}>Raum reaktivieren</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            Raum wird wieder aktiv. Optional können Sie angeben, ab wann der Raum verfügbar ist.
          </Alert>
          <TextField
            label="Verfügbar ab (optional)"
            type="date"
            value={reactivateDate}
            onChange={(e) => setReactivateDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setReactivateRoomId(null)}>Abbrechen</Button>
          <Button variant="contained" color="success" disabled={reactivateSaving} onClick={handleReactivateRoom}>
            {reactivateSaving ? <CircularProgress size={18} /> : 'Reaktivieren'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Pending Requests Dialog ── */}
      <Dialog open={pendingOpen} onClose={() => { setPendingOpen(false); setAssignBed(null) }} maxWidth="md" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <WarningAmberIcon sx={{ color: '#e65100' }} />
            Offene Verlegungsanfragen
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          {pendingLoading ? (
            <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
          ) : pendingRequests.length === 0 ? (
            <Alert severity="info">Keine offenen Anfragen vorhanden.</Alert>
          ) : (
            <>
              {assignBed && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Bett <strong>{assignBed.bett_nummer}</strong> wird zugewiesen — wählen Sie die Anfrage:
                </Alert>
              )}
              <Box display="flex" flexDirection="column" gap={1.5}>
                {pendingRequests.map((req) => (
                  <Paper key={req.id} elevation={1} sx={{
                    p: 2, borderRadius: 2, border: '1px solid #e0e0e0',
                    '&:hover': { borderColor: '#003366', bgcolor: '#f3f6fb' },
                  }}>
                    <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
                      <Box sx={{ flex: 1 }}>
                        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                          <Typography fontWeight={700}>{req.azr_id}</Typography>
                          <Chip
                            label={req.geschlecht === 'M' ? 'Männer' : req.geschlecht === 'W' ? 'Frauen' : 'Divers'}
                            size="small"
                            sx={{ bgcolor: genderColor(req.geschlecht) + '20', color: genderColor(req.geschlecht), fontWeight: 600, height: 20 }}
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {req.herkunftsland} · {req.belegung_start} – {req.belegung_ende}
                        </Typography>
                      </Box>
                      <Button size="small" variant="outlined"
                        onClick={() => navigate(`/reservations?highlight=${req.id}`)}>
                        Zur Anfrage
                      </Button>
                    </Box>
                  </Paper>
                ))}
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setPendingOpen(false); setAssignBed(null) }}>Schließen</Button>
          {canEdit && (
            <Button variant="contained" onClick={() => navigate('/suggestions')}>
              Neue Verlegungsanfrage
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Verlegungsanfrage Detail-Dialog */}
      <Dialog open={!!transferDialogBed} onClose={() => { setTransferDialogBed(null); setTransferDialogDetail(null); setStornierGrund('') }} maxWidth="sm" fullWidth>
        <DialogTitle>Verlegungsanfrage</DialogTitle>
        <DialogContent>
          {transferDialogLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}><CircularProgress /></Box>
          ) : transferDialogDetail ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pt: 1 }}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>AZR-ID:</Typography>
                <Typography variant="body2" fontWeight={700}>{transferDialogDetail.azr_id}</Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>Anfragende Einrichtung:</Typography>
                <Typography variant="body2">{transferDialogDetail.requester_location_name ?? '–'}</Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>Ziel-Einrichtung:</Typography>
                <Typography variant="body2">{transferDialogDetail.target_location_name ?? '–'}</Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>Status:</Typography>
                <Chip label={transferDialogDetail.status} size="small" color={transferDialogDetail.status === 'PENDING' ? 'warning' : transferDialogDetail.status === 'CONFIRMED' ? 'info' : 'default'} />
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 110 }}>Zeitraum:</Typography>
                <Typography variant="body2">{transferDialogDetail.belegung_start} – {transferDialogDetail.belegung_ende}</Typography>
              </Box>
              {canEdit && transferDialogDetail?.requester_location_id === id && (
                <>
                  <Divider sx={{ my: 1 }} />
                  <TextField
                    label="Begründung für Stornierung *"
                    value={stornierGrund}
                    onChange={(e) => setStornierGrund(e.target.value)}
                    multiline
                    rows={2}
                    fullWidth
                    size="small"
                  />
                </>
              )}
            </Box>
          ) : (
            <Typography color="error">Anfrage konnte nicht geladen werden.</Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setTransferDialogBed(null); setTransferDialogDetail(null); setStornierGrund('') }}>
            Schließen
          </Button>
          {canEdit && transferDialogDetail?.requester_location_id === id && (
            <Button
              variant="contained"
              color="error"
              disabled={transferDialogSaving || !stornierGrund.trim() || !transferDialogDetail}
              onClick={handleStornieren}
            >
              {transferDialogSaving ? <CircularProgress size={20} /> : 'Stornieren'}
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
