import { useEffect, useState } from 'react'
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogContentText, DialogTitle, Paper,
  Table, TableBody, TableCell, TableContainer, TableHead, TablePagination,
  TableRow, TextField, Tooltip, Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import DeleteIcon from '@mui/icons-material/DeleteForever'
import FilterListIcon from '@mui/icons-material/FilterList'
import HistoryIcon from '@mui/icons-material/History'
import { useKeycloak } from '../auth/KeycloakProvider'
import { useApiClient } from '../api/client'

interface AuditEntry {
  id: string
  event_type: string
  payload: Record<string, unknown> | null
  created_at: string
  actor_id: string | null
  actor_role: string | null
  location_id: string | null
  entity_type: string | null
  entity_id: string | null
}

interface AuditListResponse {
  items: AuditEntry[]
  total: number
  page: number
  page_size: number
}

const EVENT_COLORS: Record<string, string> = {
  OCCUPANCY_CREATED: '#2e7d32',
  OCCUPANCY_DELETED: '#c62828',
  RESERVATION_CREATED: '#1565c0',
  RESERVATION_CONFIRMED: '#0277bd',
  RESERVATION_CANCELLED: '#e65100',
  RESERVATION_REJECTED: '#b71c1c',
  RESERVATION_TRANSFERRED: '#4a148c',
  SUGGESTION_CREATED: '#00695c',
  SUGGESTION_ACCEPTED: '#2e7d32',
  SUGGESTION_REJECTED: '#c62828',
}

function eventColor(t: string) {
  return EVENT_COLORS[t] ?? '#455a64'
}

function fmt(dt: string) {
  return new Date(dt).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'medium' })
}

function defaultDateFrom() {
  const d = new Date()
  d.setDate(d.getDate() - 5)
  return d.toISOString().slice(0, 16)
}

export default function AuditLog() {
  const { keycloak } = useKeycloak()
  const { get } = useApiClient()
  const tokenParsed = keycloak?.tokenParsed as Record<string, unknown> | undefined
  const roles = ((tokenParsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [])
  const isAdmin = roles.includes('location-admin') || roles.includes('system-admin')
  const isSystemAdmin = roles.includes('system-admin')

  const [dateFrom, setDateFrom] = useState(defaultDateFrom())
  const [dateTo, setDateTo] = useState('')
  const [azrId, setAzrId] = useState('')
  const [evtType, setEvtType] = useState('')
  const [page, setPage] = useState(0)
  const [pageSize] = useState(50)

  const [data, setData] = useState<AuditListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [deleteAzrOpen, setDeleteAzrOpen] = useState(false)
  const [deleteAzrTarget, setDeleteAzrTarget] = useState('')
  const [purgeOpen, setPurgeOpen] = useState(false)
  const [deleteMsg, setDeleteMsg] = useState('')

  async function load(p = page) {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (dateFrom) params.set('date_from', new Date(dateFrom).toISOString())
      if (dateTo) params.set('date_to', new Date(dateTo).toISOString())
      if (azrId.trim()) params.set('azr_id', azrId.trim())
      if (evtType.trim()) params.set('event_type', evtType.trim())
      params.set('page', String(p + 1))
      params.set('page_size', String(pageSize))
      const result = await get<AuditListResponse>(`/api/audit?${params}`)
      setData(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(0); setPage(0) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function buildExportUrl() {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', new Date(dateFrom).toISOString())
    if (dateTo) params.set('date_to', new Date(dateTo).toISOString())
    if (azrId.trim()) params.set('azr_id', azrId.trim())
    if (evtType.trim()) params.set('event_type', evtType.trim())
    return `/api/audit/export.csv?${params}`
  }

  async function handleExport() {
    const token = keycloak?.token
    const url = buildExportUrl()
    const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    if (!resp.ok) { setError('Export fehlgeschlagen'); return }
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'audit.csv'
    a.click()
  }

  async function handleDeleteAzr() {
    setDeleteAzrOpen(false)
    try {
      const token = keycloak?.token
      const resp = await fetch(`/api/audit/azr/${encodeURIComponent(deleteAzrTarget)}?confirm=true`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await resp.json()
      setDeleteMsg(`${json.deleted} Einträge für AZR "${deleteAzrTarget}" gelöscht.`)
      load(0)
    } catch {
      setError('Löschen fehlgeschlagen')
    }
  }

  async function handlePurge() {
    setPurgeOpen(false)
    try {
      const token = keycloak?.token
      const resp = await fetch('/api/audit/purge-old', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await resp.json()
      setDeleteMsg(`${json.deleted} Einträge älter als 10 Jahre gelöscht.`)
      load(0)
    } catch {
      setError('Löschen fehlgeschlagen')
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: 'auto' }}>
      <Box display="flex" alignItems="center" gap={1} mb={3}>
        <HistoryIcon sx={{ color: '#003366', fontSize: 28 }} />
        <Typography variant="h5" fontWeight={700}>Fachliches Protokoll (Audit-Log)</Typography>
      </Box>

      {/* Filter Bar */}
      <Paper elevation={1} sx={{ p: 2, mb: 2, borderRadius: 2 }}>
        <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
          <FilterListIcon sx={{ color: '#888' }} />
          <TextField
            label="Von" type="datetime-local" size="small" value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            InputLabelProps={{ shrink: true }} sx={{ width: 200 }}
          />
          <TextField
            label="Bis" type="datetime-local" size="small" value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            InputLabelProps={{ shrink: true }} sx={{ width: 200 }}
          />
          <TextField
            label="AZR-ID / Alias" size="small" value={azrId}
            onChange={e => setAzrId(e.target.value)}
            placeholder="AZR-2024-FFM-M-01"
            sx={{ width: 200 }}
          />
          <TextField
            label="Event-Typ" size="small" value={evtType}
            onChange={e => setEvtType(e.target.value)}
            placeholder="OCCUPANCY_CREATED"
            sx={{ width: 200 }}
          />
          <Button variant="contained" onClick={() => { setPage(0); load(0) }}>
            Suchen
          </Button>
          <Box flexGrow={1} />
          {isAdmin && (
            <Tooltip title="Aktuelle Filtermenge als CSV herunterladen">
              <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleExport}>
                CSV-Export
              </Button>
            </Tooltip>
          )}
          {isAdmin && (
            <Tooltip title="Alle Einträge einer AZR löschen (DSGVO)">
              <Button
                variant="outlined" color="error" startIcon={<DeleteIcon />}
                onClick={() => { setDeleteAzrTarget(azrId); setDeleteAzrOpen(true) }}
                disabled={!azrId.trim()}
              >
                AZR löschen
              </Button>
            </Tooltip>
          )}
          {isSystemAdmin && (
            <Tooltip title="Alle Einträge älter als 10 Jahre unwiderruflich löschen">
              <Button variant="outlined" color="error" onClick={() => setPurgeOpen(true)}>
                &gt;10 Jahre löschen
              </Button>
            </Tooltip>
          )}
        </Box>
      </Paper>

      {deleteMsg && (
        <Alert severity="success" onClose={() => setDeleteMsg('')} sx={{ mb: 2 }}>
          {deleteMsg}
        </Alert>
      )}
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Table */}
      <Paper elevation={1} sx={{ borderRadius: 2 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : (
          <>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f5f7fa' }}>
                    <TableCell sx={{ fontWeight: 700 }}>Zeitpunkt</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Event-Typ</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Akteur</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Rolle</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>AZR / Entity</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Payload</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(data?.items ?? []).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 4, color: '#888' }}>
                        Keine Einträge gefunden.
                      </TableCell>
                    </TableRow>
                  ) : (data?.items ?? []).map(row => (
                    <TableRow key={row.id} hover>
                      <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12 }}>
                        {fmt(row.created_at)}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={row.event_type}
                          size="small"
                          sx={{
                            bgcolor: eventColor(row.event_type) + '15',
                            color: eventColor(row.event_type),
                            fontWeight: 600, fontSize: 11,
                          }}
                        />
                      </TableCell>
                      <TableCell sx={{ fontSize: 12, fontFamily: 'monospace', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <Tooltip title={row.actor_id ?? ''}>
                          <span>{row.actor_id ? row.actor_id.slice(0, 16) + '…' : '–'}</span>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        {row.actor_role ? (
                          <Chip label={row.actor_role} size="small" variant="outlined" sx={{ fontSize: 11 }} />
                        ) : '–'}
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {row.entity_id ?? '–'}
                        {row.entity_type && (
                          <Typography variant="caption" display="block" color="text.secondary">
                            {row.entity_type}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 300 }}>
                        <Tooltip title={JSON.stringify(row.payload, null, 2)}>
                          <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#555', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }}>
                            {row.payload ? JSON.stringify(row.payload) : '–'}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={data?.total ?? 0}
              page={page}
              rowsPerPage={pageSize}
              rowsPerPageOptions={[50]}
              onPageChange={(_, p) => { setPage(p); load(p) }}
              labelDisplayedRows={({ from, to, count }) => `${from}–${to} von ${count}`}
            />
          </>
        )}
      </Paper>

      {/* DSGVO Delete Dialog */}
      <Dialog open={deleteAzrOpen} onClose={() => setDeleteAzrOpen(false)}>
        <DialogTitle fontWeight={700}>DSGVO-Löschung bestätigen</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Alle Audit-Einträge für AZR <strong>{deleteAzrTarget}</strong> werden unwiderruflich gelöscht.
            Diese Aktion kann nicht rückgängig gemacht werden.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteAzrOpen(false)}>Abbrechen</Button>
          <Button onClick={handleDeleteAzr} color="error" variant="contained">Unwiderruflich löschen</Button>
        </DialogActions>
      </Dialog>

      {/* Purge Old Dialog */}
      <Dialog open={purgeOpen} onClose={() => setPurgeOpen(false)}>
        <DialogTitle fontWeight={700}>Einträge älter als 10 Jahre löschen</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Alle Audit-Einträge die älter als 10 Jahre sind werden permanent gelöscht.
            Diese Aktion ist unwiderruflich und nur für System-Administratoren vorgesehen.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPurgeOpen(false)}>Abbrechen</Button>
          <Button onClick={handlePurge} color="error" variant="contained">Löschen</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
