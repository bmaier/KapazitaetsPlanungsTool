import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from '@mui/material'
import FlightIcon from '@mui/icons-material/Flight'
import PersonIcon from '@mui/icons-material/Person'
import { extractApiError, useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'

interface Location {
  id: string
  name: string
}

interface Occupant {
  azr_id: string
  alias_id?: string | null
  geschlecht: string
  geburtsjahr?: number | null
  herkunftsland?: string | null
  belegung_start?: string
  belegung_ende?: string
  bed_id?: string
  labels?: string[]
}

interface AnkunftPerson {
  azr_id: string
  alias_id?: string | null
  geschlecht: string
  occ_labels?: string[]
  bed_id: string
  belegung_start?: string
  belegung_ende?: string
}

interface Props {
  open: boolean
  onClose: () => void
  onCreated: () => void
  locations: Location[]
  // Vorausgefüllte Person (z.B. von Bett-Klick oder Wartebereich)
  prefillOccupant?: Occupant | null
  // Mehrere Personen für Gruppenverlegung
  prefillGroup?: Occupant[]
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

function GenderChip({ g }: { g: string }) {
  const label = g === 'M' ? 'Männlich' : g === 'W' ? 'Weiblich' : 'Divers'
  const color = g === 'M' ? '#1565c0' : g === 'W' ? '#880e4f' : '#4a148c'
  return <Chip label={label} size="small" sx={{ bgcolor: color + '15', color, fontWeight: 600, height: 20 }} />
}

export default function VerlegungsanfrageDialog({ open, onClose, onCreated, locations, prefillOccupant, prefillGroup }: Props) {
  const { post, get } = useApiClient()
  const { locationId } = useKeycloak()
  const [form, setForm] = useState<FormState>(EMPTY)
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [ankunftPersonen, setAnkunftPersonen] = useState<AnkunftPerson[]>([])
  const [selectedAnkunftPerson, setSelectedAnkunftPerson] = useState<AnkunftPerson | null>(null)

  // Gruppe: alle Personen die noch submitted werden müssen
  const [groupQueue, setGroupQueue] = useState<Occupant[]>([])
  const [groupIndex, setGroupIndex] = useState(0)
  const [groupResults, setGroupResults] = useState<{ azr_id: string; success: boolean }[]>([])
  const isGroupMode = (prefillGroup?.length ?? 0) > 1

  const today = new Date().toISOString().slice(0, 10)
  const in30 = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)

  // Personen aus Wartebereich laden
  useEffect(() => {
    if (!open || !locationId) return
    get<{ room_id: string; room_name: string; room_type: string; beds: { bed_id: string; azr_id?: string; alias_id?: string; occ_geschlecht?: string; occ_labels?: string[]; status: string; belegung_start?: string; belegung_ende?: string }[] }[]>(
      `/api/locations/${locationId}/bed-status`
    ).then((rooms) => {
      const persons: AnkunftPerson[] = []
      for (const room of rooms) {
        if (room.room_type !== 'WARTEBEREICH') continue
        for (const bed of room.beds) {
          if (bed.status === 'BELEGT' && bed.azr_id) {
            persons.push({
              azr_id: bed.azr_id,
              alias_id: bed.alias_id,
              geschlecht: bed.occ_geschlecht ?? 'M',
              occ_labels: bed.occ_labels ?? [],
              bed_id: bed.bed_id,
              belegung_start: bed.belegung_start,
              belegung_ende: bed.belegung_ende,
            })
          }
        }
      }
      setAnkunftPersonen(persons)
    }).catch(() => setAnkunftPersonen([]))
  }, [open, locationId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Dialog öffnen: Formular aus prefill befüllen
  useEffect(() => {
    if (!open) return
    setApiError(null)
    setGroupResults([])

    const src = prefillGroup && prefillGroup.length > 0 ? prefillGroup[0] : prefillOccupant
    if (src) {
      setForm({
        target_location_id: '',
        azr_id: src.azr_id ?? '',
        geschlecht: src.geschlecht ?? '',
        geburtsjahr: src.geburtsjahr ? String(src.geburtsjahr) : '',
        herkunftsland: src.herkunftsland ?? '',
        belegung_start: today,
        belegung_ende: in30,
      })
      setGroupQueue(prefillGroup ?? [])
      setGroupIndex(0)
    } else {
      setForm({ ...EMPTY, belegung_start: today, belegung_ende: in30 })
      setGroupQueue([])
      setGroupIndex(0)
    }
    setSelectedAnkunftPerson(null)
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  function applyAnkunftPerson(p: AnkunftPerson) {
    setSelectedAnkunftPerson(p)
    setForm((f) => ({
      ...f,
      azr_id: p.azr_id,
      geschlecht: p.geschlecht,
    }))
  }

  const currentYear = new Date().getFullYear()
  const geburtsjahrNum = parseInt(form.geburtsjahr, 10)
  const errors = {
    target_location_id: !form.target_location_id,
    azr_id: form.azr_id.length === 0 || form.azr_id.length > 50,
    geschlecht: !form.geschlecht,
    geburtsjahr: form.geburtsjahr !== '' && (isNaN(geburtsjahrNum) || geburtsjahrNum < 1901 || geburtsjahrNum > currentYear),
    herkunftsland: form.herkunftsland !== '' && !isValidAlpha3(form.herkunftsland),
    belegung_start: !form.belegung_start,
    belegung_ende: !form.belegung_ende || (form.belegung_start ? form.belegung_ende <= form.belegung_start : false),
  }
  // Pflichtfelder: target, azr_id, geschlecht, belegung_start, belegung_ende
  // geburtsjahr + herkunftsland optional aber wenn angegeben dann valide
  const isValid = form.target_location_id &&
    form.azr_id.length > 0 && form.azr_id.length <= 50 &&
    form.geschlecht &&
    form.belegung_start &&
    form.belegung_ende &&
    form.belegung_ende > form.belegung_start &&
    !errors.geburtsjahr &&
    !errors.herkunftsland

  function set(field: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function submitOne(f: FormState): Promise<boolean> {
    try {
      await post('/api/reservations', {
        target_location_id: f.target_location_id,
        azr_id: f.azr_id,
        geschlecht: f.geschlecht,
        geburtsjahr: f.geburtsjahr ? parseInt(f.geburtsjahr, 10) : new Date().getFullYear() - 30,
        herkunftsland: f.herkunftsland ? f.herkunftsland.toUpperCase() : 'UNK',
        belegung_start: f.belegung_start,
        belegung_ende: f.belegung_ende,
      })
      return true
    } catch {
      return false
    }
  }

  async function handleSubmit() {
    setSubmitting(true)
    setApiError(null)

    if (isGroupMode && groupQueue.length > 0) {
      // Gruppe: aktuelle Person submitten, dann zur nächsten
      const success = await submitOne(form)
      const azr = form.azr_id
      setGroupResults((prev) => [...prev, { azr_id: azr, success }])

      const nextIdx = groupIndex + 1
      if (nextIdx < groupQueue.length) {
        const next = groupQueue[nextIdx]
        setGroupIndex(nextIdx)
        setForm((f) => ({
          ...f,
          azr_id: next.azr_id ?? '',
          geschlecht: next.geschlecht ?? '',
          geburtsjahr: next.geburtsjahr ? String(next.geburtsjahr) : '',
          herkunftsland: next.herkunftsland ?? '',
        }))
      } else {
        // Alle abgearbeitet
        onCreated()
        onClose()
      }
    } else {
      // Einzelperson
      try {
        await post('/api/reservations', {
          target_location_id: form.target_location_id,
          azr_id: form.azr_id,
          geschlecht: form.geschlecht,
          geburtsjahr: form.geburtsjahr ? parseInt(form.geburtsjahr, 10) : new Date().getFullYear() - 30,
          herkunftsland: form.herkunftsland ? form.herkunftsland.toUpperCase() : 'UNK',
          belegung_start: form.belegung_start,
          belegung_ende: form.belegung_ende,
        })
        onCreated()
        onClose()
      } catch (err: unknown) {
        setApiError(extractApiError(err))
      }
    }
    setSubmitting(false)
  }

  const targetLocations = locations.filter((l) => l.id !== locationId)
  const hasPrefill = !!prefillOccupant || (prefillGroup && prefillGroup.length > 0)

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle fontWeight={700}>
        <Box display="flex" alignItems="center" gap={1}>
          <FlightIcon sx={{ color: '#6a1b9a' }} />
          {isGroupMode
            ? `Verlegungsanfrage — Person ${groupIndex + 1} von ${groupQueue.length}`
            : 'Neue Verlegungsanfrage'}
        </Box>
      </DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
        {apiError && <Alert severity="error">{apiError}</Alert>}

        {/* Gruppenfortschritt */}
        {isGroupMode && groupResults.length > 0 && (
          <Alert severity="info" sx={{ py: 0.5 }}>
            Abgesendet: {groupResults.map((r) => (
              <Chip key={r.azr_id} size="small" label={r.azr_id}
                sx={{ mx: 0.3, bgcolor: r.success ? '#e8f5e9' : '#ffebee', color: r.success ? '#2e7d32' : '#b71c1c' }} />
            ))}
          </Alert>
        )}

        {/* Personen aus Wartebereich wählbar (wenn kein Prefill) */}
        {!hasPrefill && ankunftPersonen.length > 0 && (
          <Box>
            <Typography variant="caption" fontWeight={700} color="text.secondary"
              sx={{ display: 'block', mb: 1, letterSpacing: 0.5 }}>
              PERSONEN IM WARTEBEREICH — DIREKT AUSWÄHLEN
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={1}>
              {ankunftPersonen.map((p) => (
                <Paper
                  key={p.bed_id}
                  elevation={selectedAnkunftPerson?.bed_id === p.bed_id ? 3 : 1}
                  onClick={() => applyAnkunftPerson(p)}
                  sx={{
                    px: 1.5, py: 1, borderRadius: 2, cursor: 'pointer',
                    border: selectedAnkunftPerson?.bed_id === p.bed_id ? '2px solid #6a1b9a' : '2px solid transparent',
                    bgcolor: selectedAnkunftPerson?.bed_id === p.bed_id ? '#f3e5f5' : '#fafafa',
                    transition: 'all 0.15s',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={0.8}>
                    <PersonIcon sx={{ fontSize: 16, color: '#6a1b9a' }} />
                    <Typography variant="body2" fontWeight={600} fontFamily="monospace">{p.azr_id}</Typography>
                    <GenderChip g={p.geschlecht} />
                  </Box>
                </Paper>
              ))}
            </Box>
            <Divider sx={{ mt: 2, mb: 0.5 }} />
            <Typography variant="caption" color="text.secondary">— oder manuell eingeben —</Typography>
          </Box>
        )}

        {/* Vorausgefüllte Person anzeigen */}
        {hasPrefill && (
          <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
            <Typography variant="caption" fontWeight={700} sx={{ color: '#6a1b9a', display: 'block', mb: 0.5 }}>
              Person
            </Typography>
            <Box display="flex" gap={1.5} flexWrap="wrap" alignItems="center">
              <Typography variant="body2" fontWeight={700} fontFamily="monospace">{form.azr_id}</Typography>
              {form.geschlecht && <GenderChip g={form.geschlecht} />}
              {form.geburtsjahr && <Typography variant="body2">*{form.geburtsjahr}</Typography>}
              {form.herkunftsland && <Typography variant="body2">{form.herkunftsland.toUpperCase()}</Typography>}
            </Box>
          </Paper>
        )}

        <FormControl fullWidth required error={!form.target_location_id && submitting}>
          <InputLabel>Ziel-Einrichtung</InputLabel>
          <Select value={form.target_location_id} label="Ziel-Einrichtung"
            onChange={(e) => setForm((f) => ({ ...f, target_location_id: e.target.value }))}>
            {targetLocations.map((l) => (
              <MenuItem key={l.id} value={l.id}>{l.name}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField label="AZR-ID" value={form.azr_id} onChange={set('azr_id')}
          inputProps={{ maxLength: 50 }} required={!selectedAnkunftPerson}
          error={submitting && errors.azr_id}
          helperText="Anonymisierte Identifikationsnummer (max. 50 Zeichen)" />

        <FormControl fullWidth required>
          <InputLabel>Geschlecht</InputLabel>
          <Select value={form.geschlecht} label="Geschlecht"
            onChange={(e) => setForm((f) => ({ ...f, geschlecht: e.target.value }))}>
            <MenuItem value="M">Männlich (M)</MenuItem>
            <MenuItem value="W">Weiblich (W)</MenuItem>
            <MenuItem value="D">Divers (D)</MenuItem>
          </Select>
        </FormControl>

        <TextField label="Geburtsjahr (optional)" type="number" value={form.geburtsjahr}
          onChange={set('geburtsjahr')} inputProps={{ min: 1901, max: currentYear }}
          error={form.geburtsjahr !== '' && errors.geburtsjahr}
          helperText={`Optional. Zwischen 1901 und ${currentYear}`} />

        <TextField label="Herkunftsland ISO-3 (optional)" value={form.herkunftsland}
          onChange={set('herkunftsland')} inputProps={{ maxLength: 3 }}
          error={form.herkunftsland !== '' && errors.herkunftsland}
          helperText="Optional. Dreistelliger Ländercode, z.B. DEU, AFG, SYR" />

        <Box display="flex" gap={2}>
          <TextField label="Von" type="date" value={form.belegung_start} onChange={set('belegung_start')}
            InputLabelProps={{ shrink: true }} required fullWidth />
          <TextField label="Bis" type="date" value={form.belegung_ende} onChange={set('belegung_ende')}
            InputLabelProps={{ shrink: true }} required fullWidth
            error={form.belegung_ende !== '' && errors.belegung_ende}
            helperText={errors.belegung_ende && form.belegung_ende ? '"Bis" muss nach "Von" liegen' : ''} />
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={submitting}>Abbrechen</Button>
        <Button variant="contained" onClick={handleSubmit}
          disabled={!isValid || submitting}
          sx={{ bgcolor: '#6a1b9a', '&:hover': { bgcolor: '#4a148c' } }}>
          {isGroupMode && groupQueue.length > groupIndex + 1
            ? `Senden & weiter (${groupIndex + 1}/${groupQueue.length})`
            : 'Verlegungsanfrage senden'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
