import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Snackbar,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import BedIcon from '@mui/icons-material/Hotel'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import { useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'

interface Location {
  id: string
  name: string
  is_active: boolean
}

interface Reservation {
  id: string
  requester_location_id: string
  target_location_id: string
  azr_id: string
  geschlecht: string
  geburtsjahr: number
  herkunftsland: string
  belegung_start: string
  belegung_ende: string
  status: string
  confirmed_bed_id?: string | null
  suggested_bed_id?: string | null
  confirmed_at?: string | null
  created_at: string
}

interface FreeBed {
  bed_id: string
  bett_nummer: string
  room_name: string
  geschlechts_designation: string
  is_suggested?: boolean
  is_notbett?: boolean
  room_labels: string[]
  bed_labels: string[]
}

const STATUS_CONFIG: Record<string, { bg: string; color: string; label: string }> = {
  PENDING:     { bg: '#ede7f6', color: '#6a1b9a', label: 'Ausstehend' },
  CONFIRMED:   { bg: '#e3f2fd', color: '#1565c0', label: 'Bestätigt' },
  REJECTED:    { bg: '#ffebee', color: '#b71c1c', label: 'Abgelehnt' },
  CANCELLED:   { bg: '#f5f5f5', color: '#757575', label: 'Storniert' },
  TRANSFERRED: { bg: '#e0f2f1', color: '#00695c', label: 'Verlegt' },
}

function shortId(id: string) {
  return `#${id.slice(0, 8).toUpperCase()}`
}

function GenderChip({ g }: { g: string }) {
  const label = g === 'M' ? 'Männlich' : g === 'W' ? 'Weiblich' : 'Divers'
  const color = g === 'M' ? '#1565c0' : g === 'W' ? '#880e4f' : '#4a148c'
  return <Chip label={label} size="small" sx={{ bgcolor: color + '15', color, fontWeight: 600, height: 20 }} />
}

export default function Reservations() {
  const navigate = useNavigate()
  const { get, post, del } = useApiClient()
  const { locationId, keycloak } = useKeycloak()
  const roles = ((keycloak?.tokenParsed as Record<string, unknown>)?.realm_access as { roles?: string[] } | undefined)?.roles ?? []
  const isSystemAdmin = roles.includes('system-admin')
  const [searchParams] = useSearchParams()
  const highlightId = searchParams.get('highlight')

  const [tab, setTab] = useState(0)
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [incoming, setIncoming] = useState<Reservation[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string | null>(null)

  // Filter state — default: letzte 5 Tage, alle Status
  const [filterDateFrom, setFilterDateFrom] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 5)
    return d.toISOString().slice(0, 10)
  })
  const [filterDateTo, setFilterDateTo] = useState('')
  const [filterStatus, setFilterStatus] = useState<string[]>([])

  function applyFilters(rows: Reservation[]): Reservation[] {
    return rows.filter((r) => {
      const created = r.created_at.slice(0, 10)
      if (filterDateFrom && created < filterDateFrom) return false
      if (filterDateTo && created > filterDateTo) return false
      if (filterStatus.length > 0 && !filterStatus.includes(r.status)) return false
      return true
    })
  }

  function resetFilters() {
    const d = new Date()
    d.setDate(d.getDate() - 5)
    setFilterDateFrom(d.toISOString().slice(0, 10))
    setFilterDateTo('')
    setFilterStatus([])
  }

  function toggleStatus(s: string) {
    setFilterStatus((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s])
  }
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  })

  // Confirm dialog state: select a bed before confirming
  const [confirmRes, setConfirmRes] = useState<Reservation | null>(null)
  const [freeBeds, setFreeBeds] = useState<FreeBed[]>([])
  const [bedsLoading, setBedsLoading] = useState(false)
  const [selectedBedId, setSelectedBedId] = useState<string | null>(null)
  const [confirmSaving, setConfirmSaving] = useState(false)
  const [personLabels, setPersonLabels] = useState<string[]>([])
  const [genderMismatchGrund, setGenderMismatchGrund] = useState('')

  const genderMismatch = useMemo(() => {
    if (!selectedBedId || !confirmRes) return false
    const bed = freeBeds.find((b) => b.bed_id === selectedBedId)
    if (!bed || bed.is_notbett) return false
    const roomGender = bed.geschlechts_designation
    if (roomGender === 'D') return false
    return roomGender !== confirmRes.geschlecht
  }, [selectedBedId, confirmRes, freeBeds])

  const locName = useCallback(
    (id: string) => locations.find((l) => l.id === id)?.name ?? id.slice(0, 8) + '…',
    [locations]
  )

  const loadAll = useCallback(async () => {
    setLoading(true)
    let hasError = false
    const [locsResult, allResult, incResult] = await Promise.allSettled([
      get<Location[]>('/api/locations'),
      get<Reservation[]>('/api/reservations'),
      get<Reservation[]>('/api/reservations?target=mine'),
    ])
    if (locsResult.status === 'fulfilled') setLocations(locsResult.value)
    else hasError = true
    if (allResult.status === 'fulfilled') setReservations(allResult.value)
    else hasError = true
    if (incResult.status === 'fulfilled') setIncoming(incResult.value)
    if (hasError) setSnackbar({ open: true, message: 'Einige Daten konnten nicht geladen werden.', severity: 'error' })
    setLoading(false)
  }, [get])

  useEffect(() => { loadAll() }, [loadAll])

  // Jump to "Aktionen" tab when navigated here with a highlight param
  useEffect(() => {
    if (highlightId) setTab(1)
  }, [highlightId])

  function copyId(id: string) {
    navigator.clipboard.writeText(id).catch(() => {})
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  async function openConfirmDialog(res: Reservation) {
    setConfirmRes(res)
    setSelectedBedId(res.confirmed_bed_id ?? res.suggested_bed_id ?? null)
    setGenderMismatchGrund('')
    setPersonLabels([])
    setBedsLoading(true)
    // fetch person labels and free beds in parallel
    const [, beds] = await Promise.allSettled([
      (async () => {
        try {
          type OccResult = { azr_id: string; occ_labels: string[] }
          const occs = await get<OccResult[]>(`/api/occupants/search?q=${encodeURIComponent(res.azr_id)}`)
          const found = occs.find((o) => o.azr_id === res.azr_id)
          setPersonLabels((found?.occ_labels as string[]) ?? [])
        } catch { /* labels optional */ }
      })(),
      (async () => {
        type BedItem = { bed_id: string; bett_nummer: string; status: string; bed_labels: string[]; is_notbett?: boolean; period_available?: boolean | null }
        type RoomBedStatus = { room_id: string; room_name: string; geschlechts_designation: string; labels: string[]; beds: BedItem[] }
        const rooms = await get<RoomBedStatus[]>(
          `/api/locations/${res.target_location_id}/bed-status?date_from=${res.belegung_start}&date_to=${res.belegung_ende}&exclude_ankunft=true`
        )
        const result: FreeBed[] = rooms.flatMap((room) =>
          room.beds
            .filter((b) => (b.status === 'FREI' || b.bed_id === res.confirmed_bed_id || b.bed_id === res.suggested_bed_id) && b.period_available !== false)
            .map((b) => ({
              bed_id: b.bed_id,
              bett_nummer: b.bett_nummer,
              room_name: room.room_name,
              geschlechts_designation: room.geschlechts_designation,
              is_suggested: b.bed_id === res.suggested_bed_id,
              is_notbett: b.is_notbett ?? false,
              room_labels: room.labels ?? [],
              bed_labels: b.bed_labels ?? [],
            }))
        )
        return result
      })(),
    ])
    if (beds.status === 'fulfilled') {
      setFreeBeds(beds.value)
      if ((res.suggested_bed_id || res.confirmed_bed_id) && !beds.value.find((b) => b.bed_id === (res.confirmed_bed_id ?? res.suggested_bed_id))) {
        setSelectedBedId(null)
      }
    } else {
      setFreeBeds([])
    }
    setBedsLoading(false)
  }

  async function handleConfirmWithBed() {
    if (!confirmRes || !selectedBedId) return
    setConfirmSaving(true)
    try {
      await post(`/api/reservations/${confirmRes.id}/confirm`, {
        confirmed_bed_id: selectedBedId,
        ...(genderMismatch && genderMismatchGrund.trim() ? { geschlecht_mismatch_grund: genderMismatchGrund.trim() } : {}),
      })
      setConfirmRes(null)
      setPersonLabels([])
      setGenderMismatchGrund('')
      setSnackbar({ open: true, message: 'Verlegungsanfrage bestätigt, Bett vorgemerkt.', severity: 'success' })
      loadAll()
    } catch {
      setSnackbar({ open: true, message: 'Bestätigung fehlgeschlagen.', severity: 'error' })
    } finally {
      setConfirmSaving(false)
    }
  }

  async function handleReject(resId: string) {
    try {
      await post(`/api/reservations/${resId}/reject`, {})
      setSnackbar({ open: true, message: 'Verlegungsanfrage abgelehnt.', severity: 'success' })
      loadAll()
    } catch {
      setSnackbar({ open: true, message: 'Ablehnen fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleCancel(resId: string) {
    try {
      await del(`/api/reservations/${resId}`)
      setSnackbar({ open: true, message: 'Verlegungsanfrage storniert.', severity: 'success' })
      loadAll()
    } catch {
      setSnackbar({ open: true, message: 'Stornierung fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleTransfer(resId: string) {
    try {
      await post(`/api/reservations/${resId}/transfer`, {})
      setSnackbar({ open: true, message: 'Person eingecheckt. Belegung an Zieleinrichtung übertragen.', severity: 'success' })
      loadAll()
    } catch {
      setSnackbar({ open: true, message: 'Einchecken fehlgeschlagen.', severity: 'error' })
    }
  }

  if (loading) return <Box display="flex" justifyContent="center" mt={8}><CircularProgress /></Box>

  const filteredReservations = applyFilters(reservations)
  const filteredIncoming = applyFilters(incoming)
  const filteredMine = applyFilters(
    isSystemAdmin ? reservations : reservations.filter((r) => r.requester_location_id === locationId)
  )
  const isFilterActive = filterStatus.length > 0 || filterDateTo !== '' || (() => {
    const d = new Date(); d.setDate(d.getDate() - 5)
    return filterDateFrom !== d.toISOString().slice(0, 10)
  })()

  // mode:
  //   'all'       — Tab 0: zeige alle zutreffenden Aktionen anhand der Zeilendaten
  //   'target'    — Tab 1 (Postkorb): nur Bestätigen/Ablehnen/Einchecken; kein Stornieren
  //   'requester' — Tab 2 (Meine Anfragen): nur Stornieren; kein Bestätigen/Einchecken
  const ReservationTable = ({ rows, mode }: { rows: Reservation[]; mode: 'all' | 'target' | 'requester' }) => (
    rows.length === 0 ? (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>Keine Verlegungsanfragen vorhanden.</Typography>
    ) : (
      <Table size="small">
        <TableHead>
          <TableRow sx={{ bgcolor: '#f5f5f5' }}>
            <TableCell sx={{ fontWeight: 700 }}>Res.-ID</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Von</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Ziel</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>AZR-ID</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Person</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Zeitraum</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
            <TableCell sx={{ fontWeight: 700 }}>Aktion</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => {
            const cfg = STATUS_CONFIG[r.status] ?? { color: 'default', label: r.status }
            const isHighlighted = r.id === highlightId
            // Ob die aktuelle Einrichtung die Zieleinrichtung dieser Anfrage ist
            const isTarget = isSystemAdmin || (locationId != null && r.target_location_id === locationId)
            // Ob die aktuelle Einrichtung die anfragende Einrichtung ist
            const isRequester = isSystemAdmin || (locationId != null && r.requester_location_id === locationId)

            const showTargetActions = mode === 'target' || (mode === 'all' && isTarget)
            const showCancel = mode === 'requester' || (mode === 'all' && isRequester)
            return (
              <TableRow key={r.id} sx={{
                '&:hover': { bgcolor: '#fafafa' },
                ...(isHighlighted ? { bgcolor: '#fff8e1', outline: '2px solid #f9a825' } : {}),
              }}>
                <TableCell>
                  <Tooltip title={`Vollständige ID: ${r.id}${copied === r.id ? ' ✓ Kopiert!' : ''}`} arrow>
                    <Box display="flex" alignItems="center" gap={0.5} sx={{ cursor: 'pointer' }}
                      onClick={() => copyId(r.id)}>
                      <Typography variant="caption" fontFamily="monospace" fontWeight={700}
                        sx={{ color: '#003366', fontSize: 11 }}>
                        {shortId(r.id)}
                      </Typography>
                      <ContentCopyIcon sx={{ fontSize: 12, color: '#888' }} />
                    </Box>
                  </Tooltip>
                </TableCell>
                <TableCell>{locName(r.requester_location_id)}</TableCell>
                <TableCell>{locName(r.target_location_id)}</TableCell>
                <TableCell>
                  <Typography variant="caption" fontFamily="monospace">{r.azr_id}</Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <GenderChip g={r.geschlecht} />
                    <Typography variant="caption">*{r.geburtsjahr} · {r.herkunftsland}</Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Box>
                    <Typography variant="caption">{r.belegung_start} – {r.belegung_ende}</Typography>
                    {r.confirmed_at && (
                      <Typography variant="caption" sx={{ display: 'block', color: '#2e7d32', fontSize: 10 }}>
                        Bestätigt: {r.confirmed_at.slice(0, 10)}
                      </Typography>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip label={cfg.label} size="small"
                    sx={{ bgcolor: cfg.bg, color: cfg.color, fontWeight: 700 }} />
                </TableCell>
                <TableCell>
                  <Box display="flex" gap={0.5} flexWrap="wrap">
                    {r.status === 'PENDING' && showTargetActions && (
                      <>
                        <Button size="small" variant="contained" color="success"
                          onClick={() => openConfirmDialog(r)}>
                          Bestätigen
                        </Button>
                        <Button size="small" variant="outlined" color="error"
                          onClick={() => handleReject(r.id)}>
                          Ablehnen
                        </Button>
                      </>
                    )}
                    {r.status === 'CONFIRMED' && showTargetActions && (
                      <Button size="small" variant="contained"
                        startIcon={<CheckCircleIcon />}
                        sx={{ bgcolor: '#1565c0', '&:hover': { bgcolor: '#0d47a1' } }}
                        onClick={() => handleTransfer(r.id)}>
                        Einchecken
                      </Button>
                    )}
                    {['PENDING', 'CONFIRMED'].includes(r.status) && showCancel && (
                      <Button size="small" color="error" variant="text"
                        onClick={() => handleCancel(r.id)}>
                        Stornieren
                      </Button>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    )
  )

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" sx={{ color: '#003366', fontWeight: 700 }}>
          Verlegungsanfragen
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => navigate('/suggestions')}>
          Neue Verlegungsanfrage
        </Button>
      </Box>

      {/* ── Filterleiste ── */}
      <Paper elevation={0} sx={{ p: 2, mb: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
          <TextField
            label="Erstellt ab"
            type="date"
            size="small"
            value={filterDateFrom}
            onChange={(e) => setFilterDateFrom(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160 }}
          />
          <TextField
            label="Bis"
            type="date"
            size="small"
            value={filterDateTo}
            onChange={(e) => setFilterDateTo(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160 }}
          />
          <Box display="flex" gap={0.5} flexWrap="wrap" alignItems="center">
            <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>Status:</Typography>
            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
              const selected = filterStatus.includes(key)
              return (
                <Chip
                  key={key}
                  label={cfg.label}
                  size="small"
                  onClick={() => toggleStatus(key)}
                  sx={{
                    bgcolor: selected ? cfg.bg : 'transparent',
                    color: selected ? cfg.color : '#757575',
                    border: `1px solid ${selected ? cfg.color : '#ccc'}`,
                    fontWeight: selected ? 700 : 400,
                    cursor: 'pointer',
                  }}
                />
              )
            })}
          </Box>
          {isFilterActive && (
            <Button size="small" variant="text" onClick={resetFilters}
              sx={{ color: '#888', ml: 'auto', whiteSpace: 'nowrap' }}>
              Zurücksetzen
            </Button>
          )}
        </Box>
      </Paper>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2, borderBottom: '1px solid #e0e0e0' }}>
        <Tab label={`Alle (${filteredReservations.length})`} />
        <Tab label={
          <Box display="flex" alignItems="center" gap={1}>
            Aktionen erforderlich
            {filteredIncoming.length > 0 && (
              <Chip label={filteredIncoming.length} size="small" color="error" sx={{ height: 18, fontSize: 10 }} />
            )}
          </Box>
        } />
        <Tab label={
          <Box display="flex" alignItems="center" gap={1}>
            Meine Verlegungsanfragen
            {filteredMine.filter((r) => r.status === 'PENDING').length > 0 && (
              <Chip
                label={filteredMine.filter((r) => r.status === 'PENDING').length}
                size="small"
                sx={{ height: 18, fontSize: 10, bgcolor: '#ede7f6', color: '#6a1b9a' }}
              />
            )}
          </Box>
        } />
      </Tabs>

      <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid #e0e0e0', overflow: 'hidden' }}>
        {tab === 0 && <ReservationTable rows={filteredReservations} mode="all" />}
        {tab === 1 && <ReservationTable rows={filteredIncoming} mode="target" />}
        {tab === 2 && (
          locationId || isSystemAdmin
            ? <ReservationTable rows={filteredMine} mode="requester" />
            : <Typography color="text.secondary" sx={{ p: 3 }}>Keine Einrichtung zugeordnet.</Typography>
        )}
      </Paper>

      {/* ── Bett-Auswahl Dialog (für Bestätigung) ── */}
      <Dialog open={!!confirmRes} onClose={() => { setConfirmRes(null); setPersonLabels([]) }} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <BedIcon sx={{ color: '#2e7d32' }} />
            Verlegungsanfrage bestätigen — Bett zuweisen
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 1.5 }}>
          {confirmRes && (
            <Paper elevation={0} sx={{ p: 1.5, mb: 2, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
              <Typography variant="caption" fontWeight={700} sx={{ color: '#6a1b9a', display: 'block', mb: 1 }}>
                Person — Anfrage für Bett-Zuweisung
              </Typography>
              <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
                <Box>
                  <Typography variant="caption" color="text.secondary">AZR-ID</Typography>
                  <Typography variant="body2" fontWeight={700} fontFamily="monospace">{confirmRes.azr_id}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">Geschlecht</Typography>
                  <GenderChip g={confirmRes.geschlecht} />
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Geburtsjahr</Typography>
                  <Typography variant="body2" fontWeight={600}>*{confirmRes.geburtsjahr}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Herkunftsland</Typography>
                  <Typography variant="body2" fontWeight={600}>{confirmRes.herkunftsland}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Zeitraum</Typography>
                  <Typography variant="body2" fontWeight={600}>{confirmRes.belegung_start} – {confirmRes.belegung_ende}</Typography>
                </Box>
              </Box>
              {personLabels.length > 0 && (
                <Box display="flex" gap={0.5} flexWrap="wrap" mt={1}>
                  <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', mr: 0.5 }}>Labels:</Typography>
                  {personLabels.map((l) => (
                    <Chip key={l} label={l} size="small"
                      sx={{ bgcolor: '#ede7f6', color: '#6a1b9a', height: 20, fontSize: 11, fontWeight: 600 }} />
                  ))}
                </Box>
              )}
            </Paper>
          )}
          {bedsLoading ? (
            <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
          ) : freeBeds.length === 0 ? (
            <Alert severity="warning">Keine freien Betten im gewünschten Zeitraum verfügbar.</Alert>
          ) : (
            <Box display="flex" flexDirection="column" gap={1}>
              <Typography variant="body2" color="text.secondary" mb={1}>
                Bett wählen — vorgeschlagenes Bett ist vorausgewählt:
              </Typography>
              {freeBeds.map((b) => {
                const isSelected = selectedBedId === b.bed_id
                const isSuggested = !!b.is_suggested
                const hasLabels = b.room_labels.length > 0 || b.bed_labels.length > 0
                return (
                  <Paper
                    key={b.bed_id}
                    elevation={isSelected ? 3 : 1}
                    onClick={() => { setSelectedBedId(b.bed_id); setGenderMismatchGrund('') }}
                    sx={{
                      p: 1.5, borderRadius: 2, cursor: 'pointer',
                      border: isSelected ? '2px solid #2e7d32' : isSuggested ? '2px dashed #9c27b0' : '2px solid transparent',
                      bgcolor: isSelected ? '#e8f5e9' : isSuggested ? '#f3e5f5' : 'white',
                      transition: 'all 0.15s',
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                      <BedIcon sx={{ color: isSelected ? '#2e7d32' : isSuggested ? '#7b1fa2' : '#43a047', fontSize: 20 }} />
                      <Typography fontWeight={600}>{b.room_name} — Bett {b.bett_nummer}</Typography>
                      <GenderChip g={b.geschlechts_designation} />
                      {b.is_notbett && (
                        <Chip label="Notbett" size="small"
                          sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600, height: 18, fontSize: 10 }} />
                      )}
                      {isSuggested && !isSelected && (
                        <Chip label="Vorgeschlagen" size="small"
                          sx={{ bgcolor: '#ede7f6', color: '#6a1b9a', fontWeight: 600, height: 18, fontSize: 10 }} />
                      )}
                    </Box>
                    {hasLabels && (
                      <Box display="flex" gap={0.5} flexWrap="wrap" mt={0.75} ml={3.5}>
                        {b.room_labels.map((l) => (
                          <Tooltip key={`r-${l}`} title="Raum-Label" arrow>
                            <Chip label={l} size="small"
                              sx={{ bgcolor: '#e0f2f1', color: '#00695c', height: 18, fontSize: 10 }} />
                          </Tooltip>
                        ))}
                        {b.bed_labels.map((l) => (
                          <Tooltip key={`b-${l}`} title="Bett-Label" arrow>
                            <Chip label={l} size="small"
                              sx={{ bgcolor: '#fff8e1', color: '#f57f17', height: 18, fontSize: 10 }} />
                          </Tooltip>
                        ))}
                      </Box>
                    )}
                  </Paper>
                )
              })}
              {genderMismatch && (
                <Alert severity="warning" icon={<WarningAmberIcon fontSize="small" />} sx={{ mt: 1 }}>
                  <strong>Geschlecht-Abweichung:</strong> Das gewählte Bett ist für{' '}
                  {freeBeds.find((b) => b.bed_id === selectedBedId)?.geschlechts_designation === 'M' ? 'Männer' : 'Frauen'}{' '}
                  vorgesehen, die Person ist als{' '}
                  {confirmRes?.geschlecht === 'M' ? 'männlich' : confirmRes?.geschlecht === 'W' ? 'weiblich' : 'divers'}{' '}
                  erfasst. Bitte Begründung eingeben:
                  <TextField
                    fullWidth size="small" sx={{ mt: 1 }}
                    label="Begründung *"
                    placeholder="z.B. einziges freies Bett, kurzfristige Belegung…"
                    value={genderMismatchGrund}
                    onChange={(e) => setGenderMismatchGrund(e.target.value)}
                    required
                  />
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setConfirmRes(null); setPersonLabels([]) }}>Abbrechen</Button>
          <Button variant="contained" color="success"
            disabled={!selectedBedId || confirmSaving || (genderMismatch && !genderMismatchGrund.trim())}
            onClick={handleConfirmWithBed}>
            {confirmSaving ? <CircularProgress size={18} /> : 'Bestätigen & Bett vormerken'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
