import { useEffect, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogContentText, DialogTitle, Divider, Paper,
  Table, TableBody, TableCell, TableContainer, TableHead, TablePagination,
  TableRow, TextField, Tooltip, Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import DeleteIcon from '@mui/icons-material/DeleteForever'
import FilterListIcon from '@mui/icons-material/FilterList'
import HistoryIcon from '@mui/icons-material/History'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
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
  location_name: string | null
  entity_type: string | null
  entity_id: string | null
}

interface AuditListResponse {
  items: AuditEntry[]
  total: number
  page: number
  page_size: number
}

// ─── Farben ──────────────────────────────────────────────────────────────────

const EVENT_COLORS: Record<string, string> = {
  OCCUPANCY_CREATED: '#2e7d32',
  OCCUPANCY_DELETED: '#c62828',
  OCCUPANCY_EXTENDED: '#1b5e20',
  RESERVATION_CREATED: '#1565c0',
  RESERVATION_CONFIRMED: '#0277bd',
  RESERVATION_CANCELLED: '#e65100',
  RESERVATION_REJECTED: '#b71c1c',
  RESERVATION_TRANSFERRED: '#4a148c',
  RESERVATION_CANCELLED_WITH_GRUND: '#bf360c',
  SUGGESTION_CREATED: '#00695c',
  SUGGESTION_ACCEPTED: '#2e7d32',
  SUGGESTION_REJECTED: '#c62828',
}

function eventColor(t: string) {
  return EVENT_COLORS[t] ?? '#455a64'
}

// ─── Label-Mapping für Detail-Dialog ─────────────────────────────────────────

const LABEL_MAP: Record<string, string> = {
  ablehnungsgrund: 'Ablehnungsgrund',
  verlegung_grund: 'Verlegungsgrund',
  geschlecht_mismatch_grund: 'Begründung Geschlecht-Abweichung',
  belegung_start: 'Belegung von',
  belegung_ende: 'Belegung bis',
  requester_location_id: 'Anfragende Einrichtung (ID)',
  requester_location_name: 'Anfragende Einrichtung',
  target_location_id: 'Zieleinrichtung (ID)',
  target_location_name: 'Zieleinrichtung',
  reservation_id: 'Reservierungs-ID',
  actor_username: 'Nutzername',
  azr_id: 'AZR-ID',
  bed_id: 'Bett-ID',
  bed_info: 'Bett',
  confirmed_bed_id: 'Bestätigtes Bett (ID)',
  confirmed_bed_info: 'Bestätigtes Bett',
  actor_id: 'Nutzer-ID (Keycloak)',
  actor_role: 'Rolle',
  location_id: 'Einrichtungs-ID',
  geschlecht: 'Geschlecht',
  geburtsjahr: 'Geburtsjahr',
  herkunftsland: 'Herkunftsland',
  grund: 'Begründung',
  action: 'Aktion',
}

// ─── Fachliche Zusammenfassung je Event-Typ ───────────────────────────────────

function summarize(entry: AuditEntry): string {
  const p = entry.payload ?? {}
  const azr = entry.entity_id ?? (p.azr_id as string) ?? ''
  const azrLabel = azr ? `AZR ${azr}` : ''

  switch (entry.event_type) {
    case 'OCCUPANCY_CREATED': {
      const von = p.belegung_start as string | undefined
      const bis = p.belegung_ende as string | undefined
      const period = von && bis ? ` · ${von} – ${bis}` : ''
      return `Eingebucht: ${azrLabel}${period}`
    }
    case 'OCCUPANCY_DELETED': {
      const grund = p.grund as string | undefined
      return `Ausgebucht: ${azrLabel}${grund ? ` · ${grund}` : ''}`
    }
    case 'OCCUPANCY_EXTENDED':
      return `Notbett verlängert: ${azrLabel}`
    case 'RESERVATION_CREATED': {
      const target = (p.target_location_name as string) ?? (p.target_location_id as string) ?? ''
      const von = p.belegung_start as string | undefined
      const bis = p.belegung_ende as string | undefined
      const period = von && bis ? ` · ${von} – ${bis}` : ''
      return `Verlegung gestellt: ${azrLabel} → ${target}${period}`
    }
    case 'RESERVATION_CONFIRMED': {
      const bett = (p.confirmed_bed_info as string) ?? (p.confirmed_bed_id as string) ?? ''
      return `Verlegung bestätigt: ${azrLabel}${bett ? ` · ${bett}` : ''}`
    }
    case 'RESERVATION_CANCELLED':
    case 'RESERVATION_CANCELLED_WITH_GRUND': {
      const grund = (p.grund as string) ?? ''
      return `Storniert: ${azrLabel}${grund ? ` · ${grund}` : ''}`
    }
    case 'RESERVATION_REJECTED': {
      const grund = (p.ablehnungsgrund as string) ?? ''
      return `Abgelehnt: ${azrLabel}${grund ? ` · ${grund}` : ''}`
    }
    case 'RESERVATION_TRANSFERRED': {
      const target = (p.target_location_name as string) ?? ''
      return `Eingecheckt: ${azrLabel}${target ? ` → ${target}` : ''}`
    }
    default:
      return azrLabel
  }
}

// ─── Detail-Dialog ────────────────────────────────────────────────────────────

function DetailDialog({ entry, onClose }: { entry: AuditEntry | null; onClose: () => void }) {
  if (!entry) return null

  const p = entry.payload as Record<string, unknown> | null
  const actorUsername = p?.actor_username as string | undefined

  const structuredFields: Array<{ label: string; value: string }> = [
    { label: 'Zeitpunkt', value: fmt(entry.created_at) },
    { label: 'Event-Typ', value: entry.event_type },
    { label: 'Nutzername', value: actorUsername ?? '–' },
    { label: 'Nutzer-ID (Keycloak)', value: entry.actor_id ?? '–' },
    { label: 'Rolle', value: entry.actor_role ?? '–' },
    { label: 'Einrichtung', value: entry.location_name ?? entry.location_id ?? '–' },
    { label: 'AZR / Entity-ID', value: entry.entity_id ?? '–' },
    { label: 'Entity-Typ', value: entry.entity_type ?? '–' },
  ]

  // Wichtige fachliche Felder zuerst, dann Rest
  const PRIORITY_KEYS = [
    'requester_location_name', 'target_location_name',
    'belegung_start', 'belegung_ende',
    'geschlecht', 'geburtsjahr', 'herkunftsland',
    'confirmed_bed_info', 'bed_info',
    'ablehnungsgrund', 'verlegung_grund', 'geschlecht_mismatch_grund', 'grund',
  ]
  const SKIP_KEYS = new Set(['actor_username'])

  const payloadFields: Array<{ label: string; value: string }> = []
  if (p) {
    // Erst Prioritäts-Felder
    for (const key of PRIORITY_KEYS) {
      if (key in p && !SKIP_KEYS.has(key)) {
        const v = p[key]
        if (v !== undefined && v !== null && v !== '') {
          payloadFields.push({
            label: LABEL_MAP[key] ?? key,
            value: typeof v === 'string' ? v : JSON.stringify(v),
          })
        }
      }
    }
    // Dann alle übrigen (exkl. *_id-Doppelungen wenn *_name vorhanden und SKIP_KEYS)
    const hasName = new Set(PRIORITY_KEYS.filter(k => k.endsWith('_name')).map(k => k.replace('_name', '_id')))
    for (const [key, v] of Object.entries(p)) {
      if (SKIP_KEYS.has(key)) continue
      if (PRIORITY_KEYS.includes(key)) continue
      // Wenn für diese ID ein Name-Feld vorhanden ist, ID ausblenden
      if (hasName.has(key) && (`${key.replace('_id', '_name')}` in p)) continue
      if (v === undefined || v === null || v === '') continue
      payloadFields.push({
        label: LABEL_MAP[key] ?? key,
        value: typeof v === 'string' ? v : JSON.stringify(v),
      })
    }
  }

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle fontWeight={700} sx={{ pb: 1 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <Chip
            label={entry.event_type}
            size="small"
            sx={{
              bgcolor: eventColor(entry.event_type) + '15',
              color: eventColor(entry.event_type),
              fontWeight: 600, fontSize: 12,
            }}
          />
          <Typography variant="body2" color="text.secondary" fontFamily="monospace">
            {fmt(entry.created_at)}
          </Typography>
        </Box>
        {/* Fachliche Zusammenfassung */}
        <Typography variant="body2" sx={{ mt: 0.5, color: 'text.secondary' }}>
          {summarize(entry)}
        </Typography>
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="subtitle2" fontWeight={700} color="text.secondary" gutterBottom>
          Metadaten
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5, mb: 2 }}>
          {structuredFields.map(f => (
            <Box key={f.label}>
              <Typography variant="caption" color="text.secondary" display="block">
                {f.label}
              </Typography>
              <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                {f.value}
              </Typography>
            </Box>
          ))}
        </Box>

        {payloadFields.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" fontWeight={700} color="text.secondary" gutterBottom>
              Fachliche Details
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
              {payloadFields.map(f => (
                <Box key={f.label}>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {f.label}
                  </Typography>
                  <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                    {f.value || '–'}
                  </Typography>
                </Box>
              ))}
            </Box>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Schließen</Button>
      </DialogActions>
    </Dialog>
  )
}

// ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

function fmt(dt: string) {
  return new Date(dt).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'medium' })
}

function defaultDateFrom() {
  const d = new Date()
  d.setDate(d.getDate() - 5)
  return d.toISOString().slice(0, 16)
}

// Bekannte Event-Typen als Fallback-Liste (ergänzt durch Daten aus Backend)
const KNOWN_EVENT_TYPES = [
  'OCCUPANCY_CREATED',
  'OCCUPANCY_DELETED',
  'OCCUPANCY_EXTENDED',
  'RESERVATION_CREATED',
  'RESERVATION_CONFIRMED',
  'RESERVATION_CANCELLED',
  'RESERVATION_CANCELLED_WITH_GRUND',
  'RESERVATION_REJECTED',
  'RESERVATION_TRANSFERRED',
  'SUGGESTION_CREATED',
  'SUGGESTION_ACCEPTED',
  'SUGGESTION_REJECTED',
]

// ─── Hauptkomponente ──────────────────────────────────────────────────────────

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
  const [eventTypes, setEventTypes] = useState<string[]>(KNOWN_EVENT_TYPES)

  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null)
  const [deleteAzrOpen, setDeleteAzrOpen] = useState(false)
  const [deleteAzrTarget, setDeleteAzrTarget] = useState('')
  const [purgeOpen, setPurgeOpen] = useState(false)
  const [deleteMsg, setDeleteMsg] = useState('')

  // Lade verfügbare Event-Typen aus der DB (merge mit Fallback-Liste)
  useEffect(() => {
    get<string[]>('/api/audit/event-types')
      .then(types => {
        const merged = Array.from(new Set([...types, ...KNOWN_EVENT_TYPES])).sort()
        setEventTypes(merged)
      })
      .catch(() => { /* Fallback-Liste bleibt */ })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
          {/* Event-Typ: Autocomplete mit Liste + Wildcard-Freitext */}
          <Autocomplete
            freeSolo
            options={eventTypes}
            inputValue={evtType}
            onInputChange={(_, val) => setEvtType(val ?? '')}
            size="small"
            sx={{ width: 260 }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Event-Typ"
                placeholder="OCCUPANCY* oder auswählen"
                helperText="* als Wildcard, Groß-/Kleinschreibung egal"
                FormHelperTextProps={{ sx: { fontSize: 10, mt: 0.25 } }}
              />
            )}
            renderOption={(props, option) => (
              <li {...props} key={option}>
                <Chip
                  label={option}
                  size="small"
                  sx={{
                    bgcolor: eventColor(option) + '15',
                    color: eventColor(option),
                    fontWeight: 600, fontSize: 11,
                  }}
                />
              </li>
            )}
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

      {/* Tabelle */}
      <Paper elevation={1} sx={{ borderRadius: 2 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
        ) : (
          <>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f5f7fa' }}>
                    <TableCell sx={{ fontWeight: 700, width: 140 }}>Zeitpunkt</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 200 }}>Event-Typ</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Zusammenfassung</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 130 }}>Nutzer</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 110 }}>Rolle</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 160 }}>Einrichtung</TableCell>
                    <TableCell sx={{ width: 32 }} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(data?.items ?? []).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 4, color: '#888' }}>
                        Keine Einträge gefunden.
                      </TableCell>
                    </TableRow>
                  ) : (data?.items ?? []).map(row => {
                    const actorUsername = (row.payload as Record<string, unknown> | null)?.actor_username as string | undefined
                    return (
                      <TableRow
                        key={row.id}
                        hover
                        onClick={() => setSelectedEntry(row)}
                        sx={{ cursor: 'pointer' }}
                      >
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
                              maxWidth: 190,
                            }}
                          />
                        </TableCell>
                        <TableCell sx={{ fontSize: 12, color: '#333' }}>
                          {summarize(row)}
                        </TableCell>
                        <TableCell sx={{ fontSize: 12 }}>
                          {actorUsername ?? (row.actor_id ? row.actor_id.slice(0, 12) + '…' : '–')}
                        </TableCell>
                        <TableCell>
                          {row.actor_role ? (
                            <Chip label={row.actor_role} size="small" variant="outlined" sx={{ fontSize: 11 }} />
                          ) : '–'}
                        </TableCell>
                        <TableCell sx={{ fontSize: 12 }}>
                          {row.location_name ?? (row.location_id ? row.location_id.slice(0, 8) + '…' : '–')}
                        </TableCell>
                        <TableCell sx={{ color: '#bbb', pr: 1 }}>
                          <ChevronRightIcon fontSize="small" />
                        </TableCell>
                      </TableRow>
                    )
                  })}
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

      {/* Detail Dialog */}
      <DetailDialog entry={selectedEntry} onClose={() => setSelectedEntry(null)} />

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
