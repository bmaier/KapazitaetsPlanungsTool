import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
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
import { useApiClient } from '../api/client'
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
  created_at: string
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

  function copyId(id: string) {
    navigator.clipboard.writeText(id).catch(() => {})
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  async function handleConfirm(resId: string) {
    try {
      await post(`/api/reservations/${resId}/confirm`, {})
      setSnackbar({ open: true, message: 'Reservierung bestätigt.', severity: 'success' })
      loadAll()
    } catch {
      setSnackbar({ open: true, message: 'Bestätigung fehlgeschlagen.', severity: 'error' })
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
            return (
              <TableRow key={r.id} sx={{ '&:hover': { bgcolor: '#fafafa' } }}>
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
                  <Typography variant="caption">{r.belegung_start} – {r.belegung_ende}</Typography>
                </TableCell>
                <TableCell>
                  <Chip label={cfg.label} color={cfg.color} size="small" />
                </TableCell>
                {showActions && (
                  <TableCell>
                    <Box display="flex" gap={0.5} flexWrap="wrap">
                      {r.status === 'PENDING' && (
                        <>
                          <Button size="small" variant="contained" color="success"
                            onClick={() => handleConfirm(r.id)}>
                            Bestätigen
                          </Button>
                          <Button size="small" variant="outlined" color="error"
                            onClick={() => handleReject(r.id)}>
                            Ablehnen
                          </Button>
                        </>
                      )}
                      {['PENDING', 'CONFIRMED'].includes(r.status) && (
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
        {tab === 0 && <ReservationTable rows={reservations} showActions={false} />}
        {tab === 1 && <ReservationTable rows={incoming} showActions={true} />}
      </Paper>

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
