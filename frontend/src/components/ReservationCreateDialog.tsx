import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
} from '@mui/material'
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

export default function ReservationCreateDialog({ open, onClose, onCreated, locations }: Props) {
  const { post } = useApiClient()
  const { locationId } = useKeycloak()
  const [form, setForm] = useState<FormState>(EMPTY)
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setForm(EMPTY)
      setApiError(null)
    }
  }, [open])

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
  const isValid = !Object.values(errors).some(Boolean)

  function set(field: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
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

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Neue Reservierungsanfrage</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
        {apiError && <Alert severity="error">{apiError}</Alert>}

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
          required
        />

        <TextField
          label="Belegung bis"
          type="date"
          value={form.belegung_ende}
          onChange={set('belegung_ende')}
          InputLabelProps={{ shrink: true }}
          required
          error={form.belegung_ende !== '' && errors.belegung_ende}
          helperText={errors.belegung_ende && form.belegung_ende ? '"Bis" muss nach "Von" liegen' : ''}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>Abbrechen</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!isValid || submitting}
          aria-label="Reservierungsanfrage absenden"
        >
          Anfrage senden
        </Button>
      </DialogActions>
    </Dialog>
  )
}
