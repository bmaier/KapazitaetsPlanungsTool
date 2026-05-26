import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Snackbar,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import InboxIcon from '@mui/icons-material/Inbox'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import FlightIcon from '@mui/icons-material/Flight'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import HotelIcon from '@mui/icons-material/Hotel'
import { useApiClient } from '../api/client'
import { useSseNotifications } from '../hooks/useSseNotifications'
import { useKeycloak } from '../auth/KeycloakProvider'

interface Task {
  id: string
  task_type: string
  priority: string
  status: string
  title: string
  body: string
  created_at: string
  related_reservation_id?: string | null
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
}

interface Location {
  id: string
  name: string
}

interface OccupantResult {
  location_id: string
  bed_id: string
}

const PRIORITY_META: Record<string, { color: string; bg: string; label: string }> = {
  HIGH:   { color: '#b71c1c', bg: '#ffebee', label: 'Dringend' },
  MEDIUM: { color: '#e65100', bg: '#fff3e0', label: 'Mittel' },
  LOW:    { color: '#1b5e20', bg: '#e8f5e9', label: 'Niedrig' },
}

function shortId(id: string) {
  return `#${id.slice(0, 8).toUpperCase()}`
}

function extractAzrId(text: string): string | null {
  const match = text.match(/\bAZR-[\w-]+/)
  return match ? match[0] : null
}

function TaskCard({
  task,
  reservation,
  locationName,
  onConfirm,
  onReject,
  onCancel,
  onDismiss,
  onJumpToBed,
}: {
  task: Task
  reservation?: Reservation
  locationName?: string
  onConfirm?: (resId: string) => void
  onReject?: (resId: string, reason: string) => void
  onCancel?: (resId: string) => void
  onDismiss: (taskId: string) => void
  onJumpToBed?: (azrId: string) => void
}) {
  const pm = PRIORITY_META[task.priority] ?? { color: '#555', bg: '#f5f5f5', label: task.priority }
  const isDone = ['DONE', 'DISMISSED', 'CANCELLED', 'REJECTED', 'CONFIRMED'].includes(task.status)
    || (reservation && !['PENDING'].includes(reservation.status))
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)
  const [copied, setCopied] = useState(false)

  const bodyAzrId = extractAzrId(task.body)

  function copyId(id: string) {
    navigator.clipboard.writeText(id).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const resStatus = reservation?.status
  const resStatusLabel: Record<string, string> = {
    PENDING: 'Ausstehend', CONFIRMED: 'Bestätigt', REJECTED: 'Abgelehnt',
    CANCELLED: 'Storniert', TRANSFERRED: 'Verlegt',
  }
  const resStatusColor: Record<string, 'warning' | 'success' | 'error' | 'default' | 'info'> = {
    PENDING: 'warning', CONFIRMED: 'success', REJECTED: 'error',
    CANCELLED: 'default', TRANSFERRED: 'info',
  }

  return (
    <Card elevation={isDone ? 0 : 2} sx={{
      borderRadius: 2.5,
      borderLeft: `5px solid ${isDone ? '#bdbdbd' : pm.color}`,
      opacity: isDone ? 0.65 : 1,
      transition: 'all 0.2s',
    }}>
      <CardContent sx={{ pb: '16px !important' }}>
        <Box display="flex" alignItems="flex-start" gap={1.5}>
          <Box sx={{ mt: 0.3, color: pm.color, flexShrink: 0 }}>
            <FlightIcon sx={{ fontSize: 22 }} />
          </Box>
          <Box flex={1}>
            <Box display="flex" alignItems="center" gap={1} flexWrap="wrap" mb={0.5}>
              <Typography fontWeight={700} variant="body1">{task.title}</Typography>
              <Chip label={pm.label} size="small"
                sx={{ bgcolor: pm.bg, color: pm.color, fontWeight: 700, height: 20 }} />
              {resStatus && (
                <Chip label={resStatusLabel[resStatus] ?? resStatus} size="small"
                  color={resStatusColor[resStatus] ?? 'default'} sx={{ height: 20 }} />
              )}
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {task.body}
            </Typography>

            {/* Reservierungs-Details */}
            {reservation && (
              <Paper elevation={0} sx={{ p: 1.5, mb: 1.5, bgcolor: '#f8f9fa', borderRadius: 1.5 }}>
                <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
                  <Tooltip title={`Vollständige ID: ${reservation.id}${copied ? ' ✓ Kopiert!' : ''}`} arrow>
                    <Box display="flex" alignItems="center" gap={0.5} sx={{ cursor: 'pointer' }}
                      onClick={() => copyId(reservation.id)}>
                      <Typography variant="caption" fontWeight={700} fontFamily="monospace"
                        sx={{ color: '#003366', fontSize: 12 }}>
                        {shortId(reservation.id)}
                      </Typography>
                      <ContentCopyIcon sx={{ fontSize: 12, color: '#888' }} />
                    </Box>
                  </Tooltip>
                  <Divider orientation="vertical" flexItem />
                  <Box>
                    <Typography variant="caption" color="text.secondary">Von</Typography>
                    <Typography variant="body2" fontWeight={600}>{locationName ?? reservation.requester_location_id.slice(0, 8)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">AZR-ID</Typography>
                    <Typography variant="body2" fontWeight={600} fontFamily="monospace">{reservation.azr_id}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Person</Typography>
                    <Box display="flex" alignItems="center" gap={0.8} flexWrap="wrap" mt={0.3}>
                      <Chip
                        label={reservation.geschlecht === 'M' ? 'Männer' : reservation.geschlecht === 'W' ? 'Frauen' : 'Divers'}
                        size="small"
                        sx={{
                          bgcolor: reservation.geschlecht === 'M' ? '#1565c020' : reservation.geschlecht === 'W' ? '#880e4f20' : '#4a148c20',
                          color: reservation.geschlecht === 'M' ? '#1565c0' : reservation.geschlecht === 'W' ? '#880e4f' : '#4a148c',
                          fontWeight: 600, height: 20,
                        }}
                      />
                      <Typography variant="body2" fontWeight={600}>*{reservation.geburtsjahr} · {reservation.herkunftsland}</Typography>
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Zeitraum</Typography>
                    <Typography variant="body2" fontWeight={600}>{reservation.belegung_start} – {reservation.belegung_ende}</Typography>
                  </Box>
                </Box>
              </Paper>
            )}

            {/* Aktionen */}
            <Box display="flex" gap={1} flexWrap="wrap" alignItems="center">
              {!isDone && reservation?.status === 'PENDING' && onConfirm && onReject && onCancel && (
                <>
                  {!showReject ? (
                    <>
                      <Button size="small" variant="contained" color="success" startIcon={<CheckCircleIcon />}
                        onClick={() => onConfirm(reservation.id)}>
                        Aufnahme bestätigen
                      </Button>
                      <Button size="small" variant="outlined" color="error" startIcon={<CancelIcon />}
                        onClick={() => setShowReject(true)}>
                        Ablehnen
                      </Button>
                      <Button size="small" variant="text" color="inherit"
                        onClick={() => onCancel(reservation.id)}>
                        Stornieren
                      </Button>
                    </>
                  ) : (
                    <>
                      <TextField label="Ablehnungsgrund" size="small" value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        sx={{ minWidth: 260 }} placeholder="z.B. keine freien Plätze verfügbar" />
                      <Button size="small" color="error" variant="contained"
                        disabled={!rejectReason.trim()}
                        onClick={() => onReject(reservation.id, rejectReason)}>
                        Ablehnen
                      </Button>
                      <Button size="small" onClick={() => setShowReject(false)}>Abbrechen</Button>
                    </>
                  )}
                </>
              )}

              {/* Jump-to-bed: shown for any task with an AZR-ID in the body and no linked reservation */}
              {!reservation && bodyAzrId && onJumpToBed && (
                <Button size="small" variant="outlined" startIcon={<HotelIcon />}
                  onClick={() => onJumpToBed(bodyAzrId)}
                  sx={{ borderColor: '#003366', color: '#003366' }}>
                  Zur Belegung: {bodyAzrId}
                </Button>
              )}

              {!isDone && !reservation && !bodyAzrId && (
                <Button size="small" variant="text" color="inherit" onClick={() => onDismiss(task.id)}>
                  Als erledigt markieren
                </Button>
              )}
              {!isDone && !reservation && bodyAzrId && (
                <Button size="small" variant="text" color="inherit" onClick={() => onDismiss(task.id)}>
                  Als erledigt markieren
                </Button>
              )}
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

export default function TaskInbox() {
  const navigate = useNavigate()
  const { get, post, patch, del } = useApiClient()
  const { resetCount } = useSseNotifications()
  const { keycloak, locationId: myLocationId } = useKeycloak()
  const tokenParsed = keycloak?.tokenParsed as Record<string, unknown> | undefined
  const roles = ((tokenParsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [])
  const isSystemAdmin = roles.includes('system-admin')

  const [tab, setTab] = useState(0)
  const [tasks, setTasks] = useState<Task[]>([])
  const [allReservations, setAllReservations] = useState<Reservation[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  })

  useEffect(() => { resetCount() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [t, r, l] = await Promise.all([
        get<Task[]>('/api/tasks'),
        get<Reservation[]>('/api/reservations'),
        get<Location[]>('/api/locations'),
      ])
      setTasks(t)
      setAllReservations(r)
      setLocations(l)
    } catch {
      setSnackbar({ open: true, message: 'Postkorb konnte nicht geladen werden.', severity: 'error' })
    } finally {
      setLoading(false)
    }
  }, [get])

  useEffect(() => { load() }, [load])

  const locName = (id: string) => locations.find((l) => l.id === id)?.name ?? id.slice(0, 8) + '…'

  // Split reservations by direction
  const incomingReservations = allReservations.filter(
    (r) => r.target_location_id === myLocationId && r.status === 'PENDING'
  )
  const outgoingReservations = allReservations.filter(
    (r) => r.requester_location_id === myLocationId
  )

  async function handleConfirm(resId: string) {
    try {
      await post(`/api/reservations/${resId}/confirm`, {})
      setSnackbar({ open: true, message: 'Reservierung bestätigt.', severity: 'success' })
      load()
    } catch {
      setSnackbar({ open: true, message: 'Bestätigung fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleReject(resId: string, _reason: string) {
    try {
      await post(`/api/reservations/${resId}/reject`, {})
      setSnackbar({ open: true, message: 'Reservierung abgelehnt.', severity: 'success' })
      load()
    } catch {
      setSnackbar({ open: true, message: 'Ablehnen fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleCancel(resId: string) {
    try {
      await del(`/api/reservations/${resId}`)
      setSnackbar({ open: true, message: 'Anfrage storniert.', severity: 'success' })
      load()
    } catch {
      setSnackbar({ open: true, message: 'Stornierung fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleDismiss(taskId: string) {
    try {
      await patch(`/api/tasks/${taskId}`, { status: 'DONE' })
      setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, status: 'DONE' } : t))
    } catch {
      setSnackbar({ open: true, message: 'Aktualisierung fehlgeschlagen.', severity: 'error' })
    }
  }

  async function handleJumpToBed(azrId: string) {
    try {
      const results = await get<OccupantResult[]>(`/api/occupants/search?q=${encodeURIComponent(azrId)}`)
      if (results.length > 0) {
        navigate(`/locations/${results[0].location_id}?highlight_bed=${results[0].bed_id}`)
      } else {
        setSnackbar({ open: true, message: `Keine aktive Belegung für ${azrId} gefunden.`, severity: 'error' })
      }
    } catch {
      setSnackbar({ open: true, message: 'Suche fehlgeschlagen.', severity: 'error' })
    }
  }

  const openTasks = tasks.filter((t) => t.status === 'OPEN' || t.status === 'IN_PROGRESS')
  const doneTasks = tasks.filter((t) => !['OPEN', 'IN_PROGRESS'].includes(t.status))
  const pendingReservations = isSystemAdmin ? allReservations.filter((r) => r.status === 'PENDING') : incomingReservations
  const totalPending = openTasks.length + incomingReservations.length

  return (
    <Box sx={{ p: 3, maxWidth: 900, mx: 'auto' }}>
      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <Box sx={{ p: 1.5, bgcolor: '#003366', borderRadius: 2 }}>
          <Badge badgeContent={totalPending} color="error">
            <InboxIcon sx={{ color: 'white', fontSize: 28 }} />
          </Badge>
        </Box>
        <Box>
          <Typography variant="h5" fontWeight={700} sx={{ color: '#003366' }}>Postkorb</Typography>
          <Typography variant="body2" color="text.secondary">
            {totalPending > 0 ? `${totalPending} offene Aufgabe${totalPending > 1 ? 'n' : ''}` : 'Keine offenen Aufgaben'}
          </Typography>
        </Box>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3, borderBottom: '1px solid #e0e0e0' }}>
        <Tab label={
          <Box display="flex" alignItems="center" gap={1}>
            {isSystemAdmin ? 'Alle Anfragen' : 'Zu beantworten'}
            {totalPending > 0 && <Chip label={totalPending} size="small" color="error" sx={{ height: 18, fontSize: 10 }} />}
          </Box>
        } />
        <Tab label={
          <Box display="flex" alignItems="center" gap={1}>
            Meine Anfragen
            {outgoingReservations.filter((r) => r.status === 'PENDING').length > 0 && (
              <Chip label={outgoingReservations.filter((r) => r.status === 'PENDING').length} size="small" color="warning" sx={{ height: 18, fontSize: 10 }} />
            )}
          </Box>
        } />
        <Tab label="Erledigt / Archiv" />
      </Tabs>

      {loading ? (
        <Box display="flex" justifyContent="center" mt={8}><CircularProgress /></Box>
      ) : tab === 0 ? (
        /* TAB 0: Eingehend / Zu beantworten */
        <Box>
          {pendingReservations.length > 0 && (
            <Box mb={3}>
              <Typography variant="caption" fontWeight={700} color="text.secondary"
                sx={{ display: 'block', mb: 1.5, letterSpacing: 1 }}>
                {isSystemAdmin
                  ? `ALLE OFFENEN ANFRAGEN (${pendingReservations.length})`
                  : `EINGEHENDE ANFRAGEN — ZU BEANTWORTEN (${pendingReservations.length})`}
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                {pendingReservations.map((res) => {
                  const linkedTask = tasks.find((t) => t.related_reservation_id === res.id)
                  const isIncoming = res.target_location_id === myLocationId
                  return (
                    <TaskCard
                      key={res.id}
                      task={linkedTask ?? {
                        id: `res-${res.id}`,
                        task_type: 'RESERVATION_RECEIVED',
                        priority: 'HIGH',
                        status: 'OPEN',
                        title: isIncoming || isSystemAdmin ? `Anfrage von ${locName(res.requester_location_id)}` : 'Eigene Anfrage',
                        body: `${res.azr_id} · ${locName(res.requester_location_id)} → ${locName(res.target_location_id)}`,
                        created_at: '',
                        related_reservation_id: res.id,
                      }}
                      reservation={res}
                      locationName={isSystemAdmin
                        ? `${locName(res.requester_location_id)} → ${locName(res.target_location_id)}`
                        : locName(res.requester_location_id)}
                      onConfirm={(isIncoming || isSystemAdmin) ? handleConfirm : undefined}
                      onReject={(isIncoming || isSystemAdmin) ? handleReject : undefined}
                      onDismiss={handleDismiss}
                    />
                  )
                })}
              </Box>
            </Box>
          )}

          {pendingReservations.length > 0 &&
            openTasks.filter((t) => !allReservations.some((r) => r.id === t.related_reservation_id)).length > 0 && (
              <Divider sx={{ my: 3 }} />
            )}

          {(() => {
            const standalone = openTasks.filter(
              (t) => !allReservations.some((r) => r.id === t.related_reservation_id)
            )
            return standalone.length > 0 ? (
              <Box>
                <Typography variant="caption" fontWeight={700} color="text.secondary"
                  sx={{ display: 'block', mb: 1.5, letterSpacing: 1 }}>
                  WEITERE AUFGABEN ({standalone.length})
                </Typography>
                <Box display="flex" flexDirection="column" gap={2}>
                  {standalone.map((task) => (
                    <TaskCard key={task.id} task={task} onDismiss={handleDismiss} onJumpToBed={handleJumpToBed} />
                  ))}
                </Box>
              </Box>
            ) : null
          })()}

          {totalPending === 0 && openTasks.length === 0 && (
            <Box textAlign="center" py={6}>
              <CheckCircleIcon sx={{ fontSize: 56, color: '#a5d6a7', mb: 1.5 }} />
              <Typography variant="h6" color="text.secondary">Alles erledigt</Typography>
              <Typography variant="body2" color="text.secondary">Keine offenen Aufgaben im Postkorb.</Typography>
            </Box>
          )}
        </Box>
      ) : tab === 1 ? (
        /* TAB 1: Meine Anfragen (ausgehend) */
        <Box>
          {outgoingReservations.length === 0 ? (
            <Typography color="text.secondary">Keine eigenen Reservierungsanfragen vorhanden.</Typography>
          ) : (
            <>
              <Typography variant="caption" fontWeight={700} color="text.secondary"
                sx={{ display: 'block', mb: 1.5, letterSpacing: 1 }}>
                MEINE ANFRAGEN ({outgoingReservations.length})
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                {outgoingReservations.map((res) => (
                  <TaskCard
                    key={res.id}
                    task={{
                      id: `out-${res.id}`,
                      task_type: 'RESERVATION_SENT',
                      priority: res.status === 'PENDING' ? 'MEDIUM' : 'LOW',
                      status: ['CONFIRMED', 'CANCELLED', 'REJECTED', 'TRANSFERRED'].includes(res.status) ? 'DONE' : 'OPEN',
                      title: `Anfrage an ${locName(res.target_location_id)}`,
                      body: `${res.azr_id} · Status: ${res.status}`,
                      created_at: '',
                      related_reservation_id: res.id,
                    }}
                    reservation={res}
                    locationName={locName(res.target_location_id)}
                    onCancel={res.status === 'PENDING' ? handleCancel : undefined}
                    onDismiss={handleDismiss}
                  />
                ))}
              </Box>
            </>
          )}
        </Box>
      ) : (
        /* TAB 2: Erledigt / Archiv */
        <Box>
          {doneTasks.length === 0 ? (
            <Typography color="text.secondary">Keine archivierten Aufgaben.</Typography>
          ) : (
            <Box display="flex" flexDirection="column" gap={2}>
              {doneTasks.map((task) => (
                <TaskCard key={task.id} task={task} onDismiss={handleDismiss} />
              ))}
            </Box>
          )}
        </Box>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
