import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  Tooltip,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import BedIcon from '@mui/icons-material/Hotel'
import { useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'
import ReservationCreateDialog from '../components/ReservationCreateDialog'

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
  confirmed_at?: string | null
  created_at: string
}

interface FreeBed {
  bed_id: string
  bett_nummer: string
  room_name: string
  geschlechts_designation: string
}

const STATUS_CONFIG: Record<string, { color: 'default' | 'warning' | 'success' | 'error' | 'info'; label: string }> = {
  PENDING:     { color: 'warning', label: 'Ausstehend' },
  CONFIRMED:   { color: 'success', label: 'Bestätigt' },
  REJECTED:    { color: 'error',   label: 'Abgelehnt' },
  CANCELLED:   { color: 'default', label: 'Storniert' },
  TRANSFERRED: { color: 'info',    label: 'Verlegt' },
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
  const [dialogOpen, setDialogOpen] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  })

  // Confirm dialog state: select a bed before confirming
  const [confirmRes, setConfirmRes] = useState<Reservation | null>(null)
  const [freeBeds, setFreeBeds] = useState<FreeBed[]>([])
  const [bedsLoading, setBedsLoading] = useState(false)
  const [selectedBedId, setSelectedBedId] = useState<string | null>(null)
  const [confirmSaving, setConfirmSaving] = useState(false)

  const locName = useCallback(
    (id: string) => locations.find((l) => l.id === id)?.name ?? id.slice(0, 8) + '…',
    [locations]
  )

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [locs, all, inc] = await Promise.all([
        get<Location[]>('/api/locations'),
        get<Reservation[]>('/api/reservations'),
        get<Reservation[]>('/api/reservations?target=mine'),
      ])
      setLocations(locs)
      setReservations(all)
      setIncoming(inc)
    } catch {
      setSnackbar({ open: true, message: 'Daten konnten nicht geladen werden.', severity: 'error' })
    } finally {
      setLoading(false)
    }
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
    setSelectedBedId(null)
    setBedsLoading(true)
    try {
      type RoomBedStatus = { room_id: string; room_name: string; geschlechts_designation: string; beds: { bed_id: string; bett_nummer: string; status: string }[] }
      const rooms = await get<RoomBedStatus[]>(
        `/api/locations/${res.target_location_id}/bed-status?date_from=${res.belegung_start}&date_to=${res.belegung_ende}`
      )
      const beds: FreeBed[] = rooms.flatMap((room) =>
        room.beds
          .filter((b) => b.status === 'FREI')
          .map((b) => ({ bed_id: b.bed_id, bett_nummer: b.bett_nummer, room_name: room.room_name, geschlechts_designation: room.geschlechts_designation }))
      )
      setFreeBeds(beds)
    } catch {
      setFreeBeds([])
    } finally {
      setBedsLoading(false)
    }
  }

  async function handleConfirmWithBed() {
    if (!confirmRes || !selectedBedId) return
    setConfirmSaving(true)
    try {
      await post(`/api/reservations/${confirmRes.id}/confirm`, { confirmed_bed_id: selectedBedId })
      setConfirmRes(null)
      setSnackbar({ open: true, message: 'Reservierung bestätigt, Bett vorgemerkt.', severity: 'success' })
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
      setSnackbar({ open: true, message: 'Reservierung abgelehnt.', severity: 'success' })
      loadAll()
    } catch {
      setSnackbar({ open: true, message: 'Ablehnen fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleCancel(resId: string) {
    try {
      await del(`/api/reservations/${resId}`)
      setSnackbar({ open: true, message: 'Reservierung storniert.', severity: 'success' })
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

  const ReservationTable = ({ rows, showActions }: { rows: Reservation[]; showActions: boolean }) => (
    rows.length === 0 ? (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>Keine Reservierungen vorhanden.</Typography>
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
            {showActions && <TableCell sx={{ fontWeight: 700 }}>Aktion</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => {
            const cfg = STATUS_CONFIG[r.status] ?? { color: 'default', label: r.status }
            const isHighlighted = r.id === highlightId
            const isTargetLocation = isSystemAdmin || (locationId != null && r.target_location_id === locationId)
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
                  <Chip label={cfg.label} color={cfg.color} size="small" />
                </TableCell>
                {showActions && (
                  <TableCell>
                    <Box display="flex" gap={0.5} flexWrap="wrap">
                      {r.status === 'PENDING' && isTargetLocation && (
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
                      {r.status === 'CONFIRMED' && isTargetLocation && (
                        <Button size="small" variant="contained"
                          startIcon={<CheckCircleIcon />}
                          sx={{ bgcolor: '#1565c0', '&:hover': { bgcolor: '#0d47a1' } }}
                          onClick={() => handleTransfer(r.id)}>
                          Einchecken
                        </Button>
                      )}
                      {['PENDING', 'CONFIRMED'].includes(r.status) &&
                        (isSystemAdmin || (locationId != null && r.requester_location_id === locationId)) && (
                        <Button size="small" color="error" variant="text"
                          onClick={() => handleCancel(r.id)}>
                          Stornieren
                        </Button>
                      )}
                    </Box>
                  </TableCell>
                )}
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
          Reservierungen
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
          Neue Anfrage
        </Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2, borderBottom: '1px solid #e0e0e0' }}>
        <Tab label={`Alle Anfragen (${reservations.length})`} />
        <Tab label={
          <Box display="flex" alignItems="center" gap={1}>
            Aktionen erforderlich
            {incoming.length > 0 && (
              <Chip label={incoming.length} size="small" color="error" sx={{ height: 18, fontSize: 10 }} />
            )}
          </Box>
        } />
      </Tabs>

      <Paper elevation={0} sx={{ borderRadius: 2, border: '1px solid #e0e0e0', overflow: 'hidden' }}>
        {tab === 0 && <ReservationTable rows={reservations} showActions={true} />}
        {tab === 1 && <ReservationTable rows={incoming} showActions={true} />}
      </Paper>

      {/* ── Bett-Auswahl Dialog (für Bestätigung) ── */}
      <Dialog open={!!confirmRes} onClose={() => setConfirmRes(null)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <BedIcon sx={{ color: '#2e7d32' }} />
            Reservierung bestätigen — Bett zuweisen
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pt: 1.5 }}>
          {confirmRes && (
            <Alert severity="info" sx={{ mb: 2, py: 0.5 }}>
              AZR-ID <strong>{confirmRes.azr_id}</strong> · {confirmRes.belegung_start} – {confirmRes.belegung_ende}
            </Alert>
          )}
          {bedsLoading ? (
            <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
          ) : freeBeds.length === 0 ? (
            <Alert severity="warning">Keine freien Betten im gewünschten Zeitraum verfügbar.</Alert>
          ) : (
            <Box display="flex" flexDirection="column" gap={1}>
              <Typography variant="body2" color="text.secondary" mb={1}>
                Freies Bett wählen:
              </Typography>
              {freeBeds.map((b) => (
                <Paper
                  key={b.bed_id}
                  elevation={selectedBedId === b.bed_id ? 3 : 1}
                  onClick={() => setSelectedBedId(b.bed_id)}
                  sx={{
                    p: 1.5, borderRadius: 2, cursor: 'pointer',
                    border: selectedBedId === b.bed_id ? '2px solid #2e7d32' : '2px solid transparent',
                    bgcolor: selectedBedId === b.bed_id ? '#e8f5e9' : 'white',
                    transition: 'all 0.15s',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    <BedIcon sx={{ color: '#43a047', fontSize: 20 }} />
                    <Typography fontWeight={600}>{b.room_name} — Bett {b.bett_nummer}</Typography>
                  </Box>
                </Paper>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setConfirmRes(null)}>Abbrechen</Button>
          <Button variant="contained" color="success" disabled={!selectedBedId || confirmSaving}
            onClick={handleConfirmWithBed}>
            {confirmSaving ? <CircularProgress size={18} /> : 'Bestätigen & Bett vormerken'}
          </Button>
        </DialogActions>
      </Dialog>

      <ReservationCreateDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={() => { loadAll(); setSnackbar({ open: true, message: 'Reservierungsanfrage gesendet.', severity: 'success' }) }}
        locations={locations}
      />

      <Snackbar open={snackbar.open} autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
