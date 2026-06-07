import { useEffect, useState } from 'react'
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
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from '@mui/material'
import BedIcon from '@mui/icons-material/Hotel'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import { extractApiError, useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'

interface Location {
  id: string
  name: string
}

interface Props {
  open: boolean
  onClose: () => void
  onCreated: () => void
  locations: Location[]
}

interface FormState {
  target_location_id: string
  azr_id: string
  geschlecht: string
  geburtsjahr: string
  herkunftsland: string
  belegung_start: string
  belegung_ende: string
}

interface BedItem {
  bed_id: string
  bett_nummer: string
  status: string
  period_available?: boolean | null
}

interface RoomStatus {
  room_id: string
  room_name: string
  geschlechts_designation: string
  room_type: string
  labels: string[]
  beds: BedItem[]
}

const EMPTY: FormState = {
  target_location_id: '',
  azr_id: '',
  geschlecht: '',
  geburtsjahr: '',
  herkunftsland: '',
  belegung_start: '',
  belegung_ende: '',
}

function isValidAlpha3(v: string) {
  return /^[A-Za-z]{3}$/.test(v)
}

function genderMismatchWarning(room: RoomStatus, geschlecht: string): string | null {
  const labels = room.labels ?? []
  if (geschlecht === 'M' && labels.includes('Frauen'))
    return 'Frauenraum — eine männliche Person wird hier wahrscheinlich abgelehnt.'
  if (geschlecht === 'W' && labels.includes('Männer'))
    return 'Männerraum — eine weibliche Person wird hier wahrscheinlich abgelehnt.'
  if (geschlecht === 'M' && room.geschlechts_designation === 'W')
    return 'Raum ist für Frauen designiert — die Anfrage könnte abgelehnt werden.'
  if (geschlecht === 'W' && room.geschlechts_designation === 'M')
    return 'Raum ist für Männer designiert — die Anfrage könnte abgelehnt werden.'
  return null
}

export default function ReservationCreateDialog({ open, onClose, onCreated, locations }: Props) {
  const { get, post } = useApiClient()
  const { locationId } = useKeycloak()

  const [step, setStep] = useState(0)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [loadingBeds, setLoadingBeds] = useState(false)
  const [rooms, setRooms] = useState<RoomStatus[]>([])
  const [selectedBedId, setSelectedBedId] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setStep(0)
      setForm(EMPTY)
      setApiError(null)
      setRooms([])
      setSelectedBedId(null)
      setWarning(null)
    }
  }, [open])

  const today = new Date().toISOString().slice(0, 10)
  const currentYear = new Date().getFullYear()
  const geburtsjahrNum = parseInt(form.geburtsjahr, 10)
  const errors = {
    target_location_id: !form.target_location_id,
    azr_id: form.azr_id.length === 0 || form.azr_id.length > 50,
    geschlecht: !form.geschlecht,
    geburtsjahr: isNaN(geburtsjahrNum) || geburtsjahrNum < 1901 || geburtsjahrNum > currentYear,
    herkunftsland: !isValidAlpha3(form.herkunftsland),
    belegung_start: !form.belegung_start,
    belegung_ende: !form.belegung_ende || (form.belegung_start ? form.belegung_ende <= form.belegung_start : false),
  }
  const isStep0Valid = !Object.values(errors).some(Boolean)

  function set(field: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function goToStep1() {
    setLoadingBeds(true)
    setApiError(null)
    try {
      const data = await get<RoomStatus[]>(
        `/api/locations/${form.target_location_id}/bed-status?date_from=${form.belegung_start}&date_to=${form.belegung_ende}&exclude_ankunft=true`
      )
      setRooms(data.filter((r) => r.room_type !== 'WARTEBEREICH'))
      setSelectedBedId(null)
      setWarning(null)
      setStep(1)
    } catch {
      setApiError('Verfügbare Betten konnten nicht geladen werden.')
    } finally {
      setLoadingBeds(false)
    }
  }

  function selectBed(bedId: string, room: RoomStatus) {
    if (selectedBedId === bedId) {
      setSelectedBedId(null)
      setWarning(null)
    } else {
      setSelectedBedId(bedId)
      setWarning(genderMismatchWarning(room, form.geschlecht))
    }
  }

  async function handleSubmit() {
    setSubmitting(true)
    setApiError(null)
    try {
      await post('/api/reservations', {
        target_location_id: form.target_location_id,
        azr_id: form.azr_id,
        geschlecht: form.geschlecht,
        geburtsjahr: geburtsjahrNum,
        herkunftsland: form.herkunftsland.toUpperCase(),
        belegung_start: form.belegung_start,
        belegung_ende: form.belegung_ende,
        ...(selectedBedId ? { suggested_bed_id: selectedBedId } : {}),
      })
      onCreated()
      onClose()
    } catch (err: unknown) {
      setApiError(extractApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  const targetLocations = locations.filter((l) => l.id !== locationId)
  const freeBedRooms = rooms.map((r) => ({
    ...r,
    beds: r.beds.filter((b) => b.status === 'FREI' && b.period_available !== false),
  })).filter((r) => r.beds.length > 0)

  const GENDER_LABEL: Record<string, string> = { M: 'Männer', W: 'Frauen', D: 'Gemischt/Familie' }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography fontWeight={700}>Neue Verlegungsanfrage</Typography>
          <Typography variant="caption" color="text.secondary">
            Schritt {step + 1} / 2
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
        {apiError && <Alert severity="error">{apiError}</Alert>}

        {/* ── Schritt 1: Personendaten ── */}
        {step === 0 && (
          <>
            <FormControl fullWidth required error={form.target_location_id === '' && submitting}>
              <InputLabel>Ziel-Einrichtung</InputLabel>
              <Select
                value={form.target_location_id}
                label="Ziel-Einrichtung"
                onChange={(e) => setForm((f) => ({ ...f, target_location_id: e.target.value }))}
              >
                {targetLocations.map((l) => (
                  <MenuItem key={l.id} value={l.id}>{l.name}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="AZR-ID"
              value={form.azr_id}
              onChange={set('azr_id')}
              inputProps={{ maxLength: 50 }}
              required
              error={submitting && errors.azr_id}
              helperText="Anonymisierte Identifikationsnummer (max. 50 Zeichen)"
            />

            <FormControl fullWidth required>
              <InputLabel>Geschlecht</InputLabel>
              <Select
                value={form.geschlecht}
                label="Geschlecht"
                onChange={(e) => setForm((f) => ({ ...f, geschlecht: e.target.value }))}
              >
                <MenuItem value="M">Männlich (M)</MenuItem>
                <MenuItem value="W">Weiblich (W)</MenuItem>
                <MenuItem value="D">Divers (D)</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Geburtsjahr"
              type="number"
              value={form.geburtsjahr}
              onChange={set('geburtsjahr')}
              inputProps={{ min: 1901, max: currentYear }}
              required
              error={form.geburtsjahr !== '' && errors.geburtsjahr}
              helperText={`Zwischen 1901 und ${currentYear}`}
            />

            <TextField
              label="Herkunftsland (ISO 3166-1 alpha-3)"
              value={form.herkunftsland}
              onChange={set('herkunftsland')}
              inputProps={{ maxLength: 3 }}
              required
              error={form.herkunftsland !== '' && errors.herkunftsland}
              helperText="Dreistelliger Ländercode, z.B. DEU, AFG, SYR"
            />

            <TextField
              label="Belegung von"
              type="date"
              value={form.belegung_start}
              onChange={set('belegung_start')}
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: today }}
              required
            />

            <TextField
              label="Belegung bis"
              type="date"
              value={form.belegung_ende}
              onChange={set('belegung_ende')}
              InputLabelProps={{ shrink: true }}
              inputProps={{ min: form.belegung_start || today }}
              required
              error={form.belegung_ende !== '' && errors.belegung_ende}
              helperText={errors.belegung_ende && form.belegung_ende ? '"Bis" muss nach "Von" liegen' : ''}
            />
          </>
        )}

        {/* ── Schritt 2: Bettauswahl ── */}
        {step === 1 && (
          <>
            <Box sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
              <Typography variant="caption" fontWeight={700} color="#6a1b9a">
                {form.azr_id} · {GENDER_LABEL[form.geschlecht] ?? form.geschlecht} · *{form.geburtsjahr} · {form.herkunftsland.toUpperCase()}
              </Typography>
              <Typography variant="caption" display="block" color="text.secondary">
                {form.belegung_start} – {form.belegung_ende} · {locations.find(l => l.id === form.target_location_id)?.name}
              </Typography>
            </Box>

            {warning && (
              <Alert severity="warning" icon={<WarningAmberIcon />}>
                {warning}
              </Alert>
            )}

            <Typography variant="body2" color="text.secondary">
              Bett vorschlagen (optional) — die Zieleinrichtung kann ein anderes Bett zuweisen.
            </Typography>

            {loadingBeds ? (
              <Box display="flex" justifyContent="center" py={3}>
                <CircularProgress size={28} />
              </Box>
            ) : freeBedRooms.length === 0 ? (
              <Alert severity="info">
                Keine freien Betten im gewählten Zeitraum verfügbar. Die Anfrage kann trotzdem gesendet werden.
              </Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, maxHeight: 340, overflowY: 'auto', pr: 0.5 }}>
                {freeBedRooms.map((room) => {
                  const warn = genderMismatchWarning(room, form.geschlecht)
                  const genderLabels = (room.labels ?? []).filter(l =>
                    ['Männer', 'Frauen', 'Familie', 'Familienraum', 'Gemischt'].includes(l)
                  )
                  return (
                    <Paper key={room.room_id} elevation={0} sx={{ border: '1px solid #e0e0e0', borderRadius: 1.5, overflow: 'hidden' }}>
                      <Box sx={{ px: 1.5, py: 1, bgcolor: '#fafafa', display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="body2" fontWeight={700}>{room.room_name}</Typography>
                        {genderLabels.map(l => (
                          <Chip key={l} label={l} size="small" sx={{ height: 18, fontSize: 10 }} />
                        ))}
                        {warn && (
                          <Chip
                            icon={<WarningAmberIcon sx={{ fontSize: 13 }} />}
                            label="Geschlecht passt ggf. nicht"
                            size="small"
                            sx={{ height: 18, fontSize: 10, bgcolor: '#fff3e0', color: '#e65100', border: '1px solid #ffb74d' }}
                          />
                        )}
                      </Box>
                      <Box sx={{ px: 1.5, py: 1, display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                        {room.beds.map((bed) => {
                          const isSelected = selectedBedId === bed.bed_id
                          return (
                            <Box
                              key={bed.bed_id}
                              onClick={() => selectBed(bed.bed_id, room)}
                              sx={{
                                width: 52, height: 52, borderRadius: 1.5,
                                display: 'flex', flexDirection: 'column',
                                alignItems: 'center', justifyContent: 'center',
                                border: `2px solid ${isSelected ? '#2e7d32' : warn ? '#fb8c00' : '#43a047'}`,
                                bgcolor: isSelected ? '#e8f5e9' : warn ? '#fff8f0' : 'white',
                                cursor: 'pointer', transition: 'all 0.15s',
                                '&:hover': { transform: 'scale(1.08)', boxShadow: 2 },
                              }}
                            >
                              <BedIcon sx={{ fontSize: 15, color: isSelected ? '#2e7d32' : warn ? '#e65100' : '#43a047', mb: 0.2 }} />
                              <Typography variant="caption" fontWeight={700} sx={{ fontSize: 10, color: isSelected ? '#2e7d32' : warn ? '#e65100' : '#43a047', lineHeight: 1 }}>
                                {bed.bett_nummer}
                              </Typography>
                            </Box>
                          )
                        })}
                      </Box>
                    </Paper>
                  )
                })}
              </Box>
            )}

            {selectedBedId && (
              <Button size="small" variant="text" color="inherit"
                sx={{ alignSelf: 'flex-start', color: '#888', mt: -1 }}
                onClick={() => { setSelectedBedId(null); setWarning(null) }}>
                Auswahl aufheben
              </Button>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={step === 0 ? onClose : () => setStep(0)} disabled={submitting || loadingBeds}>
          {step === 0 ? 'Abbrechen' : 'Zurück'}
        </Button>

        {step === 0 && (
          <Button
            variant="contained"
            onClick={goToStep1}
            disabled={!isStep0Valid || loadingBeds}
          >
            {loadingBeds ? <CircularProgress size={18} /> : 'Weiter — Bett wählen'}
          </Button>
        )}

        {step === 1 && (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? <CircularProgress size={18} /> : selectedBedId ? 'Anfrage mit Bettvorschlag senden' : 'Anfrage senden (ohne Bettvorschlag)'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  )
}
