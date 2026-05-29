import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
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
  Snackbar,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import BedIcon from '@mui/icons-material/Hotel'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import PeopleIcon from '@mui/icons-material/People'
import LocationOnIcon from '@mui/icons-material/LocationOn'
import StarIcon from '@mui/icons-material/Star'
import FlightIcon from '@mui/icons-material/Flight'
import PersonIcon from '@mui/icons-material/Person'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApiClient } from '../api/client'
import { useKeycloak } from '../auth/KeycloakProvider'

const STEPS = ['Suche', 'Option wählen', 'Bestätigen']

interface BedOption {
  bed_id: string
  bett_nummer: string
  room_name: string
  bett_typ: string
  location_name: string
  location_id: string
  room_labels: string[]
}
interface Variant {
  beds: BedOption[]
  location_name: string
  is_own: boolean
  description: string
}
interface SuggestionResponse {
  suggestion_id: string
  variants: Variant[]
  message: string
}

type Modus = 'einzeln' | 'gruppe' | 'familie'

interface GroupPerson {
  azr_id: string
  geschlecht: string
}

function parseGroup(raw: string): GroupPerson[] {
  if (!raw) return []
  return raw.split(',').map((s) => {
    const [azr_id, geschlecht] = s.trim().split(':')
    return { azr_id: azr_id ?? '', geschlecht: geschlecht ?? 'M' }
  }).filter((p) => p.azr_id)
}

function GenderChip({ g }: { g: string }) {
  const label = g === 'M' ? 'Männlich' : g === 'W' ? 'Weiblich' : 'Divers'
  const color = g === 'M' ? '#1565c0' : g === 'W' ? '#880e4f' : '#4a148c'
  return <Chip label={label} size="small" sx={{ bgcolor: color + '15', color, fontWeight: 600, height: 20 }} />
}

export default function SuggestionWizard() {
  const { post, get } = useApiClient()
  const navigate = useNavigate()
  const { locationId } = useKeycloak()
  const [searchParams] = useSearchParams()

  // URL params: person context
  const preAzrId = searchParams.get('azrId') ?? ''
  const preGeschlecht = searchParams.get('geschlecht') ?? 'M'
  const preGroupRaw = searchParams.get('group') ?? ''
  const preCross = searchParams.get('cross') === '1'

  const preGroup = parseGroup(preGroupRaw)
  const hasPerson = !!preAzrId || preGroup.length > 0
  const isGroupMode = preGroup.length > 1

  // Group cycling state
  const [groupIndex, setGroupIndex] = useState(0)
  const [groupResults, setGroupResults] = useState<{ azr_id: string; success: boolean }[]>([])

  // Current person in focus — also covers single-person group URL (?group=X:M)
  const currentPerson: GroupPerson | null = preGroup.length > 0
    ? (preGroup[groupIndex] ?? null)
    : preAzrId ? { azr_id: preAzrId, geschlecht: preGeschlecht } : null

  const today = new Date().toISOString().slice(0, 10)
  const in30 = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)

  const [modus, setModus] = useState<Modus>('einzeln')
  const [geschlecht, setGeschlecht] = useState((currentPerson?.geschlecht ?? preGeschlecht) || 'M')

  // Single-gender group
  const [anzahl, setAnzahl] = useState(1)

  // Multi-gender group
  const [anzahlM, setAnzahlM] = useState(0)
  const [anzahlW, setAnzahlW] = useState(0)
  const [anzahlD, setAnzahlD] = useState(0)

  // Family
  const [erwMaenner, setErwMaenner] = useState(1)
  const [erwFrauen, setErwFrauen] = useState(1)
  const [kinder, setKinder] = useState(1)

  const [start, setStart] = useState(today)
  const [ende, setEnde] = useState(in30)
  const [crossLocation, setCrossLocation] = useState(preCross || hasPerson)
  const [ignoreGender, setIgnoreGender] = useState(false)
  const [labelFilter, setLabelFilter] = useState<string[]>([])
  const [roomLabelCatalog, setRoomLabelCatalog] = useState<string[]>([])

  // Confirmation form extras (for Verlegungsanfrage)
  const [confirmGeburtsjahr, setConfirmGeburtsjahr] = useState('')
  const [confirmHerkunftsland, setConfirmHerkunftsland] = useState('')

  // Optional person data for "Belegung vormerken" (no person context)
  const [confirmAzrId, setConfirmAzrId] = useState('')
  const [confirmAzrGeschlecht, setConfirmAzrGeschlecht] = useState('M')

  useEffect(() => {
    get<{ items: Array<{ name: string; entity_types: string[] }> }>('/api/labels')
      .then((res) => setRoomLabelCatalog(
        res.items.filter((e) => e.entity_types.includes('ROOM')).map((e) => e.name)
      ))
      .catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // When groupIndex changes, update geschlecht for new person
  useEffect(() => {
    if (currentPerson) setGeschlecht(currentPerson.geschlecht)
  }, [groupIndex]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-init gruppe fields from preGroup composition when navigating from multi-select
  useEffect(() => {
    if (isGroupMode) {
      setModus('gruppe')
      setAnzahlM(preGroup.filter((p) => p.geschlecht === 'M').length)
      setAnzahlW(preGroup.filter((p) => p.geschlecht === 'W').length)
      setAnzahlD(preGroup.filter((p) => p.geschlecht === 'D').length)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const [activeStep, setActiveStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState<SuggestionResponse | null>(null)
  const [selectedVariant, setSelectedVariant] = useState<number | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  })

  const multiGender = modus === 'gruppe' && (anzahlM > 0 || anzahlW > 0 || anzahlD > 0)
  const totalPersons = modus === 'familie'
    ? erwMaenner + erwFrauen + kinder
    : modus === 'gruppe'
      ? (multiGender ? anzahlM + anzahlW + anzahlD : anzahl)
      : 1

  const formValid = start && ende && ende > start && totalPersons >= 1 &&
    (modus !== 'familie' || (erwMaenner + erwFrauen >= 1 && kinder >= 1)) &&
    (modus !== 'gruppe' || totalPersons >= 1)

  function handleStartChange(val: string) {
    setStart(val)
    if (val) {
      const d = new Date(val)
      d.setDate(d.getDate() + 30)
      setEnde(d.toISOString().slice(0, 10))
    }
  }

  async function handleSearch() {
    setLoading(true)
    try {
      let reqGeschlecht = currentPerson?.geschlecht ?? geschlecht
      let reqAnzahl = totalPersons
      let familienModus = false
      let minderjaehrige = 0
      let maennerAnzahl = 0
      let frauenAnzahl = 0
      let diversAnzahl = 0

      if ((!hasPerson || isGroupMode) && modus === 'familie') {
        reqGeschlecht = 'D'
        reqAnzahl = isGroupMode ? preGroup.length : totalPersons
        familienModus = true
        minderjaehrige = isGroupMode ? 0 : kinder
        maennerAnzahl = isGroupMode ? preGroup.filter((p) => p.geschlecht === 'M').length : erwMaenner
        frauenAnzahl = isGroupMode ? preGroup.filter((p) => p.geschlecht === 'W').length : erwFrauen
      } else if ((!hasPerson || isGroupMode) && modus === 'gruppe' && multiGender) {
        reqGeschlecht = 'M'
        reqAnzahl = isGroupMode ? preGroup.length : totalPersons
        maennerAnzahl = anzahlM
        frauenAnzahl = anzahlW
        diversAnzahl = anzahlD
      } else if (!hasPerson && modus === 'einzeln') {
        reqAnzahl = 1
      }

      const res = await post<SuggestionResponse>('/api/suggestions', {
        geschlecht: reqGeschlecht,
        anzahl: reqAnzahl,
        belegung_start: start,
        belegung_ende: ende,
        cross_location: crossLocation,
        familien_modus: familienModus,
        minderjaehrige,
        label_filter: labelFilter,
        maenner_anzahl: maennerAnzahl,
        frauen_anzahl: frauenAnzahl,
        divers_anzahl: diversAnzahl,
        ignore_gender: ignoreGender,
      })
      setSuggestion(res)
      setSelectedVariant(null)
      setActiveStep(1)
    } catch (err: unknown) {
      const apiErr = err as { detail?: { detail?: string } }
      const msg = apiErr?.detail?.detail ?? 'Suche fehlgeschlagen. Bitte erneut versuchen.'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  async function handleAccept() {
    if (!suggestion || selectedVariant === null) return
    const variant = suggestion.variants[selectedVariant]
    setLoading(true)

    // If person context: create Verlegungsanfrage (cross-location transfer request)
    if (hasPerson && isGroupMode && modus !== 'einzeln') {
      // Gruppenverlegung: alle Personen auf einmal — beds[i] → preGroup[i]
      const targetLocationId = variant.beds[0]?.location_id
      if (!targetLocationId) {
        setSnackbar({ open: true, message: 'Keine Ziel-Einrichtung in der ausgewählten Option.', severity: 'error' })
        setLoading(false)
        return
      }
      const results: { azr_id: string; success: boolean }[] = []
      for (let i = 0; i < preGroup.length; i++) {
        const person = preGroup[i]
        const bed = variant.beds[i]
        try {
          await post('/api/reservations', {
            target_location_id: targetLocationId,
            azr_id: person.azr_id,
            geschlecht: person.geschlecht,
            geburtsjahr: confirmGeburtsjahr ? parseInt(confirmGeburtsjahr, 10) : new Date().getFullYear() - 30,
            herkunftsland: confirmHerkunftsland ? confirmHerkunftsland.toUpperCase() : 'UNK',
            belegung_start: start,
            belegung_ende: ende,
            suggested_bed_id: bed?.bed_id ?? null,
          })
          results.push({ azr_id: person.azr_id, success: true })
        } catch {
          results.push({ azr_id: person.azr_id, success: false })
        }
      }
      setGroupResults(results)
      setConfirmOpen(false)
      setCompleted(true)
      setActiveStep(2)
      const failed = results.filter((r) => !r.success).length
      if (failed > 0) {
        setSnackbar({ open: true, message: `${failed} Verlegungsanfrage(n) fehlgeschlagen.`, severity: 'error' })
      }
    } else if (hasPerson && currentPerson) {
      // Einzelperson oder Einzeln-Modus (zyklisch durch Gruppe)
      const azrId = currentPerson.azr_id
      const targetLocationId = variant.beds[0]?.location_id
      if (!targetLocationId) {
        setSnackbar({ open: true, message: 'Keine Ziel-Einrichtung in der ausgewählten Option.', severity: 'error' })
        setLoading(false)
        return
      }
      try {
        await post('/api/reservations', {
          target_location_id: targetLocationId,
          azr_id: azrId,
          geschlecht: currentPerson.geschlecht,
          geburtsjahr: confirmGeburtsjahr ? parseInt(confirmGeburtsjahr, 10) : new Date().getFullYear() - 30,
          herkunftsland: confirmHerkunftsland ? confirmHerkunftsland.toUpperCase() : 'UNK',
          belegung_start: start,
          belegung_ende: ende,
          suggested_bed_id: variant.beds[0]?.bed_id ?? null,
        })

        if (isGroupMode && groupIndex + 1 < preGroup.length) {
          // More persons in group — advance
          const nextIdx = groupIndex + 1
          setGroupResults((prev) => [...prev, { azr_id: azrId, success: true }])
          setGroupIndex(nextIdx)
          setConfirmOpen(false)
          setActiveStep(0)
          setSuggestion(null)
          setSelectedVariant(null)
          setGeschlecht(preGroup[nextIdx]?.geschlecht ?? 'M')
          setSnackbar({ open: true, message: `Verlegungsanfrage für ${azrId} gesendet. Weiter mit Person ${nextIdx + 1}/${preGroup.length}.`, severity: 'success' })
        } else {
          // Done
          setGroupResults((prev) => [...prev, { azr_id: azrId, success: true }])
          setConfirmOpen(false)
          setCompleted(true)
          setActiveStep(2)
        }
      } catch {
        setGroupResults((prev) => [...prev, { azr_id: azrId, success: false }])
        setSnackbar({ open: true, message: `Verlegungsanfrage für ${azrId} fehlgeschlagen.`, severity: 'error' })
      }
    } else {
      // No person context: Belegung vormerken
      try {
        if (confirmAzrId.trim() && selectedVariantData?.beds[0]) {
          // AZR-ID provided — create actual occupancy
          await post(`/api/beds/${selectedVariantData.beds[0].bed_id}/occupancy`, {
            azr_id: confirmAzrId.trim(),
            geschlecht: confirmAzrGeschlecht,
            belegung_start: start,
            belegung_ende: ende,
          })
        } else {
          // No AZR-ID — just log suggestion acceptance
          await post(`/api/suggestions/${suggestion.suggestion_id}/accept`, { variant_index: selectedVariant })
        }
        setConfirmOpen(false)
        setCompleted(true)
        setActiveStep(2)
      } catch {
        setSnackbar({ open: true, message: 'Bestätigung fehlgeschlagen.', severity: 'error' })
      }
    }
    setLoading(false)
  }

  const selectedVariantData = suggestion && selectedVariant !== null ? suggestion.variants[selectedVariant] : null

  return (
    <Box sx={{ p: 3, maxWidth: 820, mx: 'auto' }}>
      <Box display="flex" alignItems="center" gap={1} mb={0.5}>
        <FlightIcon sx={{ color: hasPerson ? '#6a1b9a' : '#003366' }} />
        <Typography variant="h5" fontWeight={700} sx={{ color: hasPerson ? '#6a1b9a' : '#003366' }}>
          {hasPerson ? 'Verlegungsanfrage' : 'Bettsuche'}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {hasPerson
          ? 'Freie Plätze an anderen Einrichtungen finden und Verlegungsanfrage stellen'
          : 'Freie Plätze suchen, Option auswählen und Belegung vormerken'}
      </Typography>

      {/* Group progress */}
      {isGroupMode && groupResults.length > 0 && (
        <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>
          <strong>Gruppenverlegung:</strong> {groupResults.map((r) => (
            <Chip key={r.azr_id} size="small" label={r.azr_id}
              sx={{ mx: 0.3, bgcolor: r.success ? '#e8f5e9' : '#ffebee', color: r.success ? '#2e7d32' : '#b71c1c' }} />
          ))}
        </Alert>
      )}

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}><StepLabel>{label}</StepLabel></Step>
        ))}
      </Stepper>

      {/* Step 1: Search Form */}
      {activeStep === 0 && (
        <Box display="flex" flexDirection="column" gap={2.5}>
          {/* Person banner — Gruppe (Gruppe/Familie-Modus) */}
          {isGroupMode && modus !== 'einzeln' && (
            <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 2, border: '1px solid #ce93d8' }}>
              <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                <PeopleIcon sx={{ color: '#6a1b9a', fontSize: 20 }} />
                <Typography variant="body2" fontWeight={700} color="#6a1b9a">
                  Gruppe ({preGroup.length} Personen):
                </Typography>
                {preGroup.map((p) => (
                  <Box key={p.azr_id} display="flex" alignItems="center" gap={0.5}>
                    <Typography variant="body2" fontFamily="monospace" fontWeight={600}>{p.azr_id}</Typography>
                    <GenderChip g={p.geschlecht} />
                  </Box>
                ))}
                <Box sx={{ flexGrow: 1 }} />
                <Chip label="Standortübergreifend aktiv" size="small"
                  sx={{ bgcolor: '#6a1b9a', color: 'white', fontWeight: 600, fontSize: 11 }} />
              </Box>
            </Paper>
          )}

          {/* Person banner — Einzelperson oder Einzeln-Modus in Gruppe */}
          {currentPerson && (!isGroupMode || modus === 'einzeln') && (
            <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 2, border: '1px solid #ce93d8' }}>
              <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                <PersonIcon sx={{ color: '#6a1b9a', fontSize: 20 }} />
                <Typography variant="body2" fontWeight={700} color="#6a1b9a">
                  {isGroupMode ? `Person ${groupIndex + 1}/${preGroup.length}:` : 'Person:'}
                </Typography>
                <Typography variant="body2" fontWeight={700} fontFamily="monospace">{currentPerson.azr_id}</Typography>
                <GenderChip g={currentPerson.geschlecht} />
                <Box sx={{ flexGrow: 1 }} />
                <Chip label="Standortübergreifend aktiv" size="small"
                  sx={{ bgcolor: '#6a1b9a', color: 'white', fontWeight: 600, fontSize: 11 }} />
              </Box>
            </Paper>
          )}

          {/* Modus — sichtbar ohne Person-Kontext oder im Gruppenverlegungsmodus */}
          {(!hasPerson || isGroupMode) && (
            <Paper elevation={0} sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                SUCHMODUS
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                {([
                  { key: 'einzeln', label: 'Einzelperson' },
                  { key: 'gruppe', label: 'Gruppe' },
                  { key: 'familie', label: 'Familie / Minderjährige' },
                ] as { key: Modus; label: string }[]).map(({ key, label }) => (
                  <Chip key={key} label={label} onClick={() => setModus(key)}
                    color={modus === key ? 'primary' : 'default'}
                    variant={modus === key ? 'filled' : 'outlined'}
                    sx={{ fontWeight: modus === key ? 700 : 400 }} />
                ))}
              </Box>
            </Paper>
          )}

          {/* Geschlecht — nur ohne Person-Kontext */}
          {!hasPerson && modus === 'einzeln' && (
            <FormControl fullWidth>
              <InputLabel>Geschlecht</InputLabel>
              <Select value={geschlecht} label="Geschlecht" onChange={(e) => setGeschlecht(e.target.value)}>
                <MenuItem value="M">Männlich</MenuItem>
                <MenuItem value="W">Weiblich</MenuItem>
                <MenuItem value="D">Divers</MenuItem>
              </Select>
            </FormControl>
          )}

          {/* Gruppe — ohne Person-Kontext oder im Gruppenverlegungsmodus */}
          {(!hasPerson || isGroupMode) && modus === 'gruppe' && (
            <Paper elevation={0} sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
                GRUPPENZUSAMMENSETZUNG
              </Typography>
              <Box display="flex" gap={1.5} flexWrap="wrap" mb={1.5}>
                <TextField label="Männer" type="number" value={anzahlM}
                  onChange={(e) => setAnzahlM(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 100 }} sx={{ flex: 1, minWidth: 100 }} />
                <TextField label="Frauen" type="number" value={anzahlW}
                  onChange={(e) => setAnzahlW(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 100 }} sx={{ flex: 1, minWidth: 100 }} />
                <TextField label="Divers" type="number" value={anzahlD}
                  onChange={(e) => setAnzahlD(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 100 }} sx={{ flex: 1, minWidth: 100 }} />
              </Box>
              {!multiGender && (
                <Box display="flex" gap={1.5} flexWrap="wrap">
                  <FormControl sx={{ flex: 1 }}>
                    <InputLabel>Einzelnes Geschlecht</InputLabel>
                    <Select value={geschlecht} label="Einzelnes Geschlecht" onChange={(e) => setGeschlecht(e.target.value)}>
                      <MenuItem value="M">Männlich</MenuItem>
                      <MenuItem value="W">Weiblich</MenuItem>
                      <MenuItem value="D">Gemischt</MenuItem>
                    </Select>
                  </FormControl>
                  <TextField label="Anzahl" type="number" value={anzahl}
                    onChange={(e) => setAnzahl(Math.max(1, Number(e.target.value)))}
                    inputProps={{ min: 1, max: 200 }} sx={{ flex: 1 }} />
                </Box>
              )}
            </Paper>
          )}

          {/* Familie — ohne Person-Kontext oder im Gruppenverlegungsmodus */}
          {(!hasPerson || isGroupMode) && modus === 'familie' && (
            <Paper elevation={0} sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
                FAMILIENZUSAMMENSETZUNG
              </Typography>
              <Box display="flex" gap={2} flexWrap="wrap">
                <TextField label="Erwachsene Männer" type="number" value={erwMaenner}
                  onChange={(e) => setErwMaenner(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 20 }} sx={{ flex: 1, minWidth: 140 }} />
                <TextField label="Erwachsene Frauen" type="number" value={erwFrauen}
                  onChange={(e) => setErwFrauen(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 20 }} sx={{ flex: 1, minWidth: 140 }} />
                <TextField label="Kinder" type="number" value={kinder}
                  onChange={(e) => setKinder(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 20 }} sx={{ flex: 1, minWidth: 140 }} />
              </Box>
            </Paper>
          )}

          {/* Dates */}
          <Box display="flex" gap={2}>
            <TextField label="Belegung von" type="date" value={start}
              onChange={(e) => handleStartChange(e.target.value)}
              InputLabelProps={{ shrink: true }} required sx={{ flex: 1 }} inputProps={{ min: today }} />
            <TextField label="Belegung bis" type="date" value={ende}
              onChange={(e) => setEnde(e.target.value)}
              InputLabelProps={{ shrink: true }} required sx={{ flex: 1 }} inputProps={{ min: start }}
              error={!!ende && !!start && ende <= start}
              helperText={ende && start && ende <= start ? '"Bis" muss nach "Von" liegen' : ''} />
          </Box>

          {/* Cross-location toggle — gesperrt wenn Person-Kontext */}
          <Box display="flex" alignItems="center" justifyContent="space-between"
            sx={{ p: 1.5, border: `1px solid ${crossLocation ? '#6a1b9a' : '#e0e0e0'}`, borderRadius: 2,
              bgcolor: crossLocation ? '#faf5ff' : 'transparent' }}>
            <Box>
              <Typography variant="body2" fontWeight={600}>Standortübergreifend suchen</Typography>
              <Typography variant="caption" color="text.secondary">
                {hasPerson
                  ? 'Aktiv — Verlegungsanfragen sind immer standortübergreifend'
                  : 'Zeigt freie Plätze in allen aktiven Einrichtungen'}
              </Typography>
            </Box>
            <input type="checkbox" checked={crossLocation}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => !hasPerson && setCrossLocation(e.target.checked)}
              style={{ width: 20, height: 20, cursor: hasPerson ? 'default' : 'pointer' }}
              disabled={hasPerson} />
          </Box>

          {/* Ignore gender */}
          {!hasPerson && (
            <Box display="flex" alignItems="center" justifyContent="space-between"
              sx={{ p: 1.5, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <Box>
                <Typography variant="body2" fontWeight={600}>Geschlechtertrennung ignorieren</Typography>
                <Typography variant="caption" color="text.secondary">
                  Zeigt alle freien Betten unabhängig vom Raum-Geschlecht
                </Typography>
              </Box>
              <input type="checkbox" checked={ignoreGender}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setIgnoreGender(e.target.checked)}
                style={{ width: 20, height: 20, cursor: 'pointer' }} />
            </Box>
          )}

          {/* Room label filter */}
          <Paper elevation={0} sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              RAUM-FILTER (OPTIONAL)
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {roomLabelCatalog.map((lbl) => {
                const active = labelFilter.includes(lbl)
                return (
                  <Chip key={lbl} label={lbl} size="small"
                    onClick={() => setLabelFilter((prev) => active ? prev.filter((l) => l !== lbl) : [...prev, lbl])}
                    color={active ? 'primary' : 'default'} variant={active ? 'filled' : 'outlined'}
                    sx={{ fontWeight: active ? 700 : 400, fontSize: 12 }} />
                )
              })}
              {labelFilter.length > 0 && (
                <Chip label="Filter leeren" size="small" color="error" variant="outlined"
                  onClick={() => setLabelFilter([])} sx={{ fontSize: 12 }} />
              )}
            </Box>
          </Paper>

          {!locationId && (
            <Alert severity="warning">Kein Einrichtungs-Kontext erkannt. Bitte ab- und wieder anmelden.</Alert>
          )}

          <Box display="flex" gap={2} mt={1}>
            <Button variant="outlined" onClick={() => navigate(-1)}>Zurück</Button>
            <Button variant="contained" onClick={handleSearch}
              disabled={!formValid || loading || !locationId}
              startIcon={loading ? <CircularProgress size={16} /> : <SearchIcon />}
              size="large"
              sx={hasPerson ? { bgcolor: '#6a1b9a', '&:hover': { bgcolor: '#4a148c' } } : {}}>
              Freie Plätze suchen
            </Button>
          </Box>
        </Box>
      )}

      {/* Step 2: Results */}
      {activeStep === 1 && suggestion && (
        <Box>
          {/* Person reminder banner */}
          {currentPerson && (
            <Paper elevation={0} sx={{ p: 1.5, mb: 2, bgcolor: '#f3e5f5', borderRadius: 2, border: '1px solid #ce93d8' }}>
              <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                <PersonIcon sx={{ color: '#6a1b9a', fontSize: 18 }} />
                <Typography variant="body2" fontWeight={700} fontFamily="monospace" color="#6a1b9a">
                  {currentPerson.azr_id}
                </Typography>
                <GenderChip g={currentPerson.geschlecht} />
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                  {start} – {ende}
                </Typography>
              </Box>
            </Paper>
          )}

          {!currentPerson && (
            <Paper elevation={0} sx={{ p: 2, mb: 3, borderRadius: 2, bgcolor: '#f3f6fb', display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip label={`${totalPersons} Person${totalPersons > 1 ? 'en' : ''}`} icon={<PeopleIcon />} size="small" />
              <Chip label={`${start} – ${ende}`} size="small" />
              {crossLocation && <Chip label="Standortübergreifend" size="small" color="info" />}
            </Paper>
          )}

          {suggestion.message && (
            <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>{suggestion.message}</Alert>
          )}

          {suggestion.variants.length === 0 ? (
            <Box>
              <Alert severity="warning" sx={{ mb: 2, borderRadius: 2 }}>
                Keine freien Plätze gefunden. Suchkriterien anpassen oder anderen Zeitraum wählen.
              </Alert>
              <Button variant="outlined" onClick={() => setActiveStep(0)}>Suche anpassen</Button>
            </Box>
          ) : (() => {
            // Single-bed mode: all variants have exactly 1 bed → group by location
            const isSingleBedMode = suggestion.variants.every((v) => v.beds.length === 1)

            type LocGroup = { locationName: string; isOwn: boolean; entries: { idx: number; v: Variant }[] }
            const grouped: LocGroup[] = []
            if (isSingleBedMode) {
              const byLoc = new Map<string, LocGroup>()
              suggestion.variants.forEach((v, idx) => {
                const locName = v.location_name || v.beds[0]?.location_name || ''
                if (!byLoc.has(locName)) byLoc.set(locName, { locationName: locName, isOwn: v.is_own, entries: [] })
                byLoc.get(locName)!.entries.push({ idx, v })
              })
              const own = [...byLoc.values()].filter((g) => g.isOwn)
              const others = [...byLoc.values()].filter((g) => !g.isOwn)
              grouped.push(...own, ...others)
            }

            const accentColor = hasPerson ? '#6a1b9a' : '#003366'
            const totalFree = suggestion.variants.length

            return (
              <Box>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <Typography variant="body2" color="text.secondary">
                    {isSingleBedMode
                      ? `${totalFree} freie Bett${totalFree !== 1 ? 'en' : ''} in ${grouped.length} Einrichtung${grouped.length !== 1 ? 'en' : ''}:`
                      : `${totalFree} Option${totalFree !== 1 ? 'en' : ''} gefunden:`}
                  </Typography>
                  <Button size="small" variant="outlined" onClick={handleSearch} disabled={loading} sx={{ ml: 'auto', fontSize: 11 }}>
                    Aktualisieren
                  </Button>
                </Box>

                {isSingleBedMode ? (
                  /* ── Lokations-gruppierte Ansicht (Einzelperson) ── */
                  <Box display="flex" flexDirection="column" gap={2} mb={3}>
                    {grouped.map(({ locationName, isOwn, entries }) => (
                      <Card key={locationName} elevation={1} sx={{
                        borderRadius: 2,
                        border: `1px solid ${isOwn ? '#1565c0' : '#e0e0e0'}`,
                      }}>
                        <CardContent sx={{ pb: '16px !important' }}>
                          <Box display="flex" alignItems="center" gap={1} mb={1.5} flexWrap="wrap">
                            {isOwn ? <StarIcon sx={{ color: '#1565c0', fontSize: 18 }} /> : <LocationOnIcon sx={{ color: '#666', fontSize: 18 }} />}
                            <Typography fontWeight={700} color={isOwn ? '#1565c0' : 'text.primary'}>
                              {locationName}
                            </Typography>
                            {isOwn && <Chip label="Diese Einrichtung" size="small"
                              sx={{ bgcolor: '#e3f2fd', color: '#1565c0', fontWeight: 600, height: 20, fontSize: 11 }} />}
                            {hasPerson && !isOwn && <Chip label="Verlegungsziel" size="small"
                              sx={{ bgcolor: '#f3e5f5', color: '#6a1b9a', fontWeight: 600, height: 20, fontSize: 11 }} />}
                            <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                              {entries.length} freie{entries.length !== 1 ? '' : 's'} Bett{entries.length !== 1 ? 'en' : ''}
                            </Typography>
                          </Box>
                          <Box display="flex" flexWrap="wrap" gap={0.8}>
                            {entries.map(({ idx, v }) => {
                              const bed = v.beds[0]
                              const isSelected = selectedVariant === idx
                              return (
                                <Box
                                  key={bed.bed_id}
                                  onClick={() => setSelectedVariant(isSelected ? null : idx)}
                                  sx={{
                                    px: 1.2, py: 0.7, borderRadius: 1.5, cursor: 'pointer',
                                    border: `2px solid ${isSelected ? '#2e7d32' : '#e0e0e0'}`,
                                    bgcolor: isSelected ? '#e8f5e9' : 'white',
                                    display: 'flex', alignItems: 'center', gap: 0.5,
                                    transition: 'all 0.12s',
                                    '&:hover': { border: '2px solid #43a047', bgcolor: '#f1f8e9' },
                                  }}
                                >
                                  <BedIcon sx={{ fontSize: 13, color: isSelected ? '#2e7d32' : '#43a047' }} />
                                  <Typography variant="caption" fontWeight={600} color={isSelected ? '#2e7d32' : '#333'}>
                                    {v.description} · {bed.bett_nummer}
                                  </Typography>
                                  {isSelected && <CheckCircleIcon sx={{ fontSize: 13, color: '#2e7d32', ml: 0.3 }} />}
                                  {(bed.room_labels ?? []).filter((l) =>
                                    ['Männer', 'Frauen', 'Familie', 'Familienraum', 'Gemischt'].includes(l)
                                  ).map((lbl) => (
                                    <Chip key={lbl} label={lbl} size="small"
                                      sx={{ height: 14, fontSize: 9, px: 0.2, bgcolor: '#f3e5f5', color: '#6a1b9a' }} />
                                  ))}
                                </Box>
                              )
                            })}
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                ) : (
                  /* ── Varianten-Karten (Gruppe / Familie) ── */
                  <Box display="flex" flexDirection="column" gap={2} mb={3}>
                    {suggestion.variants.map((v, idx) => {
                      const isSelected = selectedVariant === idx
                      const locName = v.location_name || v.beds[0]?.location_name || ''
                      const roomsInVariant = [...new Set(v.beds.map((b) => b.room_name))]
                      const complete = v.beds.length >= totalPersons
                      const isOwn = v.is_own
                      return (
                        <Card key={idx} elevation={isSelected ? 4 : 1}
                          sx={{ border: `2px solid ${isSelected ? accentColor : isOwn ? '#1565c0' : 'transparent'}`,
                            borderRadius: 2, transition: 'all 0.15s', opacity: complete ? 1 : 0.8 }}>
                          <CardActionArea onClick={() => setSelectedVariant(idx)} sx={{ p: 0 }}>
                            <CardContent sx={{ pb: '16px !important' }}>
                              <Box display="flex" alignItems="center" gap={1} mb={1.5}>
                                {isSelected && <CheckCircleIcon sx={{ color: accentColor, fontSize: 20 }} />}
                                {isOwn && !isSelected && <StarIcon sx={{ color: '#1565c0', fontSize: 18 }} />}
                                <LocationOnIcon sx={{ color: isOwn ? '#1565c0' : '#666', fontSize: 18 }} />
                                <Typography fontWeight={700} color={isSelected ? accentColor : isOwn ? '#1565c0' : 'text.primary'}>
                                  {locName || `Option ${idx + 1}`}
                                </Typography>
                                {isOwn && <Chip label="Diese Einrichtung" size="small"
                                  sx={{ bgcolor: '#e3f2fd', color: '#1565c0', fontWeight: 600, height: 20, fontSize: 11 }} />}
                                {hasPerson && !isOwn && <Chip label="Verlegungsziel" size="small"
                                  sx={{ bgcolor: '#f3e5f5', color: '#6a1b9a', fontWeight: 600, height: 20, fontSize: 11 }} />}
                                <Box sx={{ flexGrow: 1 }} />
                                <Chip label={roomsInVariant.length === 1 ? '1 Raum' : `${roomsInVariant.length} Räume`}
                                  size="small" color={roomsInVariant.length === 1 ? 'success' : 'default'} />
                                <Chip label={`${v.beds.length} Bett${v.beds.length > 1 ? 'en' : ''}`} size="small" />
                              </Box>
                              {v.description && (
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, ml: 0.5 }}>
                                  {v.description}
                                </Typography>
                              )}
                              <Box display="flex" flexWrap="wrap" gap={0.8}>
                                {v.beds.map((b) => (
                                  <Box key={b.bed_id} sx={{ display: 'flex', alignItems: 'center', gap: 0.5,
                                    px: 1.2, py: 0.5, borderRadius: 1.5, bgcolor: '#e8f5e9', border: '1px solid #a5d6a7' }}>
                                    <BedIcon sx={{ fontSize: 13, color: '#2e7d32' }} />
                                    <Typography variant="caption" fontWeight={600} color="#1b5e20">
                                      {b.room_name} · {b.bett_nummer}
                                    </Typography>
                                    {(b.room_labels ?? []).map((lbl) => (
                                      <Chip key={lbl} label={lbl} size="small"
                                        sx={{ height: 16, fontSize: 10, px: 0.3, bgcolor: '#c8e6c9', color: '#1b5e20' }} />
                                    ))}
                                  </Box>
                                ))}
                              </Box>
                            </CardContent>
                          </CardActionArea>
                        </Card>
                      )
                    })}
                  </Box>
                )}

                <Box display="flex" gap={2}>
                  <Button variant="outlined" onClick={() => setActiveStep(0)}>Zurück</Button>
                  <Button variant="contained" onClick={() => setConfirmOpen(true)}
                    disabled={selectedVariant === null}
                    size="large"
                    sx={hasPerson ? { bgcolor: accentColor, '&:hover': { bgcolor: '#4a148c' } } : {}}>
                    {hasPerson ? 'Verlegungsanfrage stellen →' : 'Option bestätigen →'}
                  </Button>
                </Box>
              </Box>
            )
          })()}
        </Box>
      )}

      {/* Step 3: Done */}
      {activeStep === 2 && (
        <Box textAlign="center" py={4}>
          <CheckCircleIcon sx={{ fontSize: 64, color: completed ? '#43a047' : '#bdbdbd', mb: 2 }} />
          <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
            {isGroupMode && groupResults.length > 1
              ? `${groupResults.filter((r) => r.success).length}/${groupResults.length} Verlegungsanfragen gesendet`
              : hasPerson ? 'Verlegungsanfrage gesendet' : 'Abgeschlossen'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {hasPerson
              ? 'Die Anfrage erscheint im Postkorb der Ziel-Einrichtung zur Bestätigung.'
              : 'Der Eintrag erscheint im Postkorb zur weiteren Bearbeitung.'}
          </Typography>
          {isGroupMode && groupResults.length > 0 && (
            <Box display="flex" flexWrap="wrap" gap={1} justifyContent="center" mb={3}>
              {groupResults.map((r) => (
                <Chip key={r.azr_id} label={r.azr_id}
                  sx={{ bgcolor: r.success ? '#e8f5e9' : '#ffebee', color: r.success ? '#2e7d32' : '#b71c1c', fontWeight: 600 }} />
              ))}
            </Box>
          )}
          <Box display="flex" gap={2} justifyContent="center">
            <Button variant="contained" onClick={() => navigate('/tasks')}>Zum Postkorb</Button>
            <Button variant="outlined" onClick={() => navigate('/')}>Zum Dashboard</Button>
          </Box>
        </Box>
      )}

      {/* Confirm Dialog */}
      <Dialog open={confirmOpen} onClose={() => { setConfirmOpen(false); setConfirmAzrId(''); setConfirmAzrGeschlecht('M') }} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            {hasPerson ? <FlightIcon sx={{ color: '#6a1b9a' }} /> : <CheckCircleIcon sx={{ color: '#003366' }} />}
            {hasPerson
              ? (isGroupMode && modus !== 'einzeln'
                  ? `Gruppenverlegung — ${preGroup.length} Personen`
                  : isGroupMode
                  ? `Verlegungsanfrage ${groupIndex + 1}/${preGroup.length}`
                  : 'Verlegungsanfrage bestätigen')
              : 'Belegung vormerken'}
          </Box>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          {/* Gruppe */}
          {isGroupMode && modus !== 'einzeln' && (
            <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
              <Typography variant="caption" fontWeight={700} color="#6a1b9a" sx={{ display: 'block', mb: 0.5 }}>
                Gruppe ({preGroup.length} Personen)
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                {preGroup.map((p) => (
                  <Box key={p.azr_id} display="flex" alignItems="center" gap={0.5}>
                    <Typography variant="body2" fontWeight={700} fontFamily="monospace">{p.azr_id}</Typography>
                    <GenderChip g={p.geschlecht} />
                  </Box>
                ))}
              </Box>
            </Paper>
          )}

          {/* Einzelperson */}
          {currentPerson && (!isGroupMode || modus === 'einzeln') && (
            <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
              <Typography variant="caption" fontWeight={700} color="#6a1b9a" sx={{ display: 'block', mb: 0.5 }}>
                Person
              </Typography>
              <Box display="flex" gap={1.5} alignItems="center" flexWrap="wrap">
                <Typography fontWeight={700} fontFamily="monospace">{currentPerson.azr_id}</Typography>
                <GenderChip g={currentPerson.geschlecht} />
              </Box>
            </Paper>
          )}

          {/* Target + beds */}
          {selectedVariantData && (
            <Box>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <LocationOnIcon sx={{ color: hasPerson ? '#6a1b9a' : '#003366', fontSize: 18 }} />
                <Typography fontWeight={700} color={hasPerson ? '#6a1b9a' : '#003366'}>
                  {selectedVariantData.location_name || selectedVariantData.beds[0]?.location_name}
                </Typography>
              </Box>
              {selectedVariantData.beds.map((b) => (
                <Box key={b.bed_id} display="flex" alignItems="center" gap={1} mb={0.8}>
                  <BedIcon sx={{ color: '#2e7d32', fontSize: 18 }} />
                  <Typography variant="body2">{b.room_name} · Bett {b.bett_nummer}</Typography>
                </Box>
              ))}
            </Box>
          )}

          <Box display="flex" gap={2}>
            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>Zeitraum:</Typography>
            <Typography variant="body2" fontWeight={600}>{start} – {ende}</Typography>
          </Box>

          {/* Optional extras for Verlegungsanfrage */}
          {hasPerson && (
            <>
              <TextField label="Geburtsjahr (optional)" type="number"
                value={confirmGeburtsjahr} onChange={(e) => setConfirmGeburtsjahr(e.target.value)}
                inputProps={{ min: 1901, max: new Date().getFullYear() }}
                helperText="Erleichtert der Zieleinrichtung die Planung" size="small" />
              <TextField label="Herkunftsland ISO-3 (optional)" value={confirmHerkunftsland}
                onChange={(e) => setConfirmHerkunftsland(e.target.value)} inputProps={{ maxLength: 3 }}
                helperText="z.B. SYR, AFG, IRQ" size="small" />
            </>
          )}

          {/* Optional person assignment for "Belegung vormerken" */}
          {!hasPerson && (
            <Paper elevation={0} sx={{ p: 1.5, border: '1px solid #e0e0e0', borderRadius: 1.5 }}>
              <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                PERSON ZUWEISEN (OPTIONAL)
              </Typography>
              <Box display="flex" gap={1.5} flexWrap="wrap">
                <TextField
                  label="AZR-ID" size="small" value={confirmAzrId}
                  onChange={(e) => setConfirmAzrId(e.target.value)}
                  placeholder="AZR-2024-0001-M01"
                  sx={{ flex: 2, minWidth: 160 }}
                />
                <FormControl size="small" sx={{ flex: 1, minWidth: 110 }}>
                  <InputLabel>Geschlecht</InputLabel>
                  <Select value={confirmAzrGeschlecht} label="Geschlecht"
                    onChange={(e) => setConfirmAzrGeschlecht(e.target.value as string)}>
                    <MenuItem value="M">Männlich</MenuItem>
                    <MenuItem value="W">Weiblich</MenuItem>
                    <MenuItem value="D">Divers</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              {confirmAzrId.trim() && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  Belegung wird direkt eingebucht und im Protokoll erfasst.
                </Typography>
              )}
            </Paper>
          )}

          {hasPerson && (
            <Alert severity="info" sx={{ py: 0.5, fontSize: 12 }}>
              Die Anfrage erscheint im Postkorb der Ziel-Einrichtung und muss dort bestätigt werden.
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setConfirmOpen(false); setConfirmAzrId(''); setConfirmAzrGeschlecht('M') }}>Abbrechen</Button>
          <Button variant="contained" onClick={handleAccept} disabled={loading}
            sx={hasPerson ? { bgcolor: '#6a1b9a', '&:hover': { bgcolor: '#4a148c' } } : {}}>
            {loading ? <CircularProgress size={18} /> : hasPerson ? 'Verlegungsanfrage senden' : (confirmAzrId.trim() ? 'Jetzt einbuchen' : 'Jetzt vormerken')}
          </Button>
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
