import { useState } from 'react'
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
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApiClient } from '../api/client'

const STEPS = ['Anfrage stellen', 'Option wählen', 'Bestätigen']

interface BedOption {
  bed_id: string
  bett_nummer: string
  room_name: string
  bett_typ: string
  location_name: string
}
interface Variant {
  beds: BedOption[]
}
interface SuggestionResponse {
  suggestion_id: string
  variants: Variant[]
  message: string
}

type Modus = 'einzeln' | 'gruppe' | 'familie'

export default function SuggestionWizard() {
  const { post } = useApiClient()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // URL-Parameter: Verlegen von Drilldown übergeben
  const preAzrId = searchParams.get('azrId') ?? ''
  const preGeschlecht = searchParams.get('geschlecht') ?? 'M'

  const today = new Date().toISOString().slice(0, 10)
  const in14 = new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10)

  // Form state
  const [modus, setModus] = useState<Modus>(preAzrId ? 'einzeln' : 'einzeln')
  const [geschlecht, setGeschlecht] = useState(preGeschlecht || 'M')
  const [anzahl, setAnzahl] = useState(1)
  const [erwMaenner, setErwMaenner] = useState(1)
  const [erwFrauen, setErwFrauen] = useState(1)
  const [kinder, setKinder] = useState(1)
  const [start, setStart] = useState(today)
  const [ende, setEnde] = useState(in14)
  const [crossLocation, setCrossLocation] = useState(false)

  // Wizard state
  const [activeStep, setActiveStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState<SuggestionResponse | null>(null)
  const [selectedVariant, setSelectedVariant] = useState<number | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [completed, setCompleted] = useState(false)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  })

  const totalPersons = modus === 'familie'
    ? erwMaenner + erwFrauen + kinder
    : modus === 'gruppe' ? anzahl : 1

  const formValid = start && ende && ende > start && totalPersons >= 1 &&
    (modus !== 'familie' || erwMaenner + erwFrauen >= 1)

  function handleStartChange(val: string) {
    setStart(val)
    // Auto-fill end date = start + 14 days
    if (val) {
      const d = new Date(val)
      d.setDate(d.getDate() + 14)
      setEnde(d.toISOString().slice(0, 10))
    }
  }

  async function handleSearch() {
    setLoading(true)
    try {
      let reqGeschlecht = geschlecht
      let reqAnzahl = totalPersons
      let familienModus = false
      let minderjaehrige = 0

      if (modus === 'familie') {
        reqGeschlecht = 'D'
        reqAnzahl = totalPersons
        familienModus = true
        minderjaehrige = kinder
      } else if (modus === 'einzeln') {
        reqGeschlecht = geschlecht
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
      })
      setSuggestion(res)
      setSelectedVariant(null)
      setActiveStep(1)
    } catch {
      setSnackbar({ open: true, message: 'Suche fehlgeschlagen. Bitte erneut versuchen.', severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  async function handleAccept() {
    if (!suggestion || selectedVariant === null) return
    setLoading(true)
    try {
      await post(`/api/suggestions/${suggestion.suggestion_id}/accept`, { variant_index: selectedVariant })
      setConfirmOpen(false)
      setSnackbar({ open: true, message: 'Reservierungsanfrage bestätigt — Eintrag im Postkorb.', severity: 'success' })
      setCompleted(true)
      setActiveStep(2)
    } catch {
      setSnackbar({ open: true, message: 'Bestätigung fehlgeschlagen.', severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  async function handleReject() {
    if (!suggestion || !rejectReason.trim()) return
    setLoading(true)
    try {
      await post(`/api/suggestions/${suggestion.suggestion_id}/reject`, { reason: rejectReason })
      setRejectOpen(false)
      setSnackbar({ open: true, message: 'Anfrage abgelehnt.', severity: 'success' })
      setCompleted(true)
      setActiveStep(2)
    } catch {
      setSnackbar({ open: true, message: 'Ablehnung fehlgeschlagen.', severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 780, mx: 'auto' }}>
      <Typography variant="h5" fontWeight={700} sx={{ color: '#003366', mb: 0.5 }}>
        Reservierungsanfrage
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Freie Plätze suchen, Option auswählen und Belegung vormerken
      </Typography>

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}><StepLabel>{label}</StepLabel></Step>
        ))}
      </Stepper>

      {/* Step 1: Search Form */}
      {activeStep === 0 && (
        <Box display="flex" flexDirection="column" gap={2.5}>
          {/* Hinweis wenn aus Drilldown-Verlegen navigiert */}
          {preAzrId && (
            <Alert severity="info" sx={{ borderRadius: 2 }}>
              Verlegungsanfrage für <strong>{preAzrId}</strong> — wählen Sie die Zieleinrichtung und den Zeitraum.
            </Alert>
          )}
          {/* Modus */}
          <Paper elevation={0} sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              BUCHUNGSMODUS
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {([
                { key: 'einzeln', label: 'Einzelperson' },
                { key: 'gruppe', label: 'Gruppe' },
                { key: 'familie', label: 'Familie / Minderjährige' },
              ] as { key: Modus; label: string }[]).map(({ key, label }) => (
                <Chip
                  key={key}
                  label={label}
                  onClick={() => setModus(key)}
                  color={modus === key ? 'primary' : 'default'}
                  variant={modus === key ? 'filled' : 'outlined'}
                  sx={{ fontWeight: modus === key ? 700 : 400 }}
                />
              ))}
            </Box>
          </Paper>

          {/* Person details */}
          {modus === 'einzeln' && (
            <FormControl fullWidth>
              <InputLabel>Geschlecht</InputLabel>
              <Select value={geschlecht} label="Geschlecht" onChange={(e) => setGeschlecht(e.target.value)}>
                <MenuItem value="M">Männlich</MenuItem>
                <MenuItem value="W">Weiblich</MenuItem>
                <MenuItem value="D">Divers</MenuItem>
              </Select>
            </FormControl>
          )}

          {modus === 'gruppe' && (
            <Box display="flex" gap={2}>
              <FormControl sx={{ flex: 1 }}>
                <InputLabel>Geschlecht</InputLabel>
                <Select value={geschlecht} label="Geschlecht" onChange={(e) => setGeschlecht(e.target.value)}>
                  <MenuItem value="M">Männlich</MenuItem>
                  <MenuItem value="W">Weiblich</MenuItem>
                  <MenuItem value="D">Gemischt</MenuItem>
                </Select>
              </FormControl>
              <TextField
                label="Anzahl Personen"
                type="number"
                value={anzahl}
                onChange={(e) => setAnzahl(Math.max(1, Number(e.target.value)))}
                inputProps={{ min: 1, max: 50 }}
                sx={{ flex: 1 }}
              />
            </Box>
          )}

          {modus === 'familie' && (
            <Paper elevation={0} sx={{ p: 2, border: '1px solid #e0e0e0', borderRadius: 2 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
                FAMILIENZUSAMMENSETZUNG
              </Typography>
              <Box display="flex" gap={2} flexWrap="wrap">
                <TextField
                  label="Erwachsene Männer"
                  type="number"
                  value={erwMaenner}
                  onChange={(e) => setErwMaenner(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 20 }}
                  sx={{ flex: 1, minWidth: 140 }}
                />
                <TextField
                  label="Erwachsene Frauen"
                  type="number"
                  value={erwFrauen}
                  onChange={(e) => setErwFrauen(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 20 }}
                  sx={{ flex: 1, minWidth: 140 }}
                />
                <TextField
                  label="Kinder"
                  type="number"
                  value={kinder}
                  onChange={(e) => setKinder(Math.max(0, Number(e.target.value)))}
                  inputProps={{ min: 0, max: 20 }}
                  sx={{ flex: 1, minWidth: 140 }}
                />
              </Box>
              <Box sx={{ mt: 1.5, p: 1.5, bgcolor: '#f3f6fb', borderRadius: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Gesamt: <strong>{totalPersons} Personen</strong> —
                  System sucht zuerst einen gemischten Raum für alle, dann getrennte Lösungen nach Geschlecht.
                </Typography>
              </Box>
            </Paper>
          )}

          {/* Dates */}
          <Box display="flex" gap={2}>
            <TextField
              label="Belegung von"
              type="date"
              value={start}
              onChange={(e) => handleStartChange(e.target.value)}
              InputLabelProps={{ shrink: true }}
              required
              sx={{ flex: 1 }}
              inputProps={{ min: today }}
            />
            <TextField
              label="Belegung bis"
              type="date"
              value={ende}
              onChange={(e) => setEnde(e.target.value)}
              InputLabelProps={{ shrink: true }}
              required
              sx={{ flex: 1 }}
              inputProps={{ min: start }}
              error={!!ende && !!start && ende <= start}
              helperText={ende && start && ende <= start ? '"Bis" muss nach "Von" liegen' : ''}
            />
          </Box>

          {/* Cross-location toggle */}
          <Box display="flex" alignItems="center" justifyContent="space-between"
            sx={{ p: 1.5, border: '1px solid #e0e0e0', borderRadius: 2 }}>
            <Box>
              <Typography variant="body2" fontWeight={600}>Standortübergreifend suchen</Typography>
              <Typography variant="caption" color="text.secondary">
                Zeigt freie Plätze in allen aktiven Einrichtungen an
              </Typography>
            </Box>
            <input type="checkbox" checked={crossLocation} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCrossLocation(e.target.checked)} style={{ width: 20, height: 20, cursor: 'pointer' }} />
          </Box>

          <Box display="flex" gap={2} mt={1}>
            <Button variant="outlined" onClick={() => navigate('/')}>Abbrechen</Button>
            <Button
              variant="contained"
              onClick={handleSearch}
              disabled={!formValid || loading}
              startIcon={loading ? <CircularProgress size={16} /> : <SearchIcon />}
              size="large"
            >
              Freie Plätze suchen
            </Button>
          </Box>
        </Box>
      )}

      {/* Step 2: Results */}
      {activeStep === 1 && suggestion && (
        <Box>
          {/* Summary bar */}
          <Paper elevation={0} sx={{ p: 2, mb: 3, borderRadius: 2, bgcolor: '#f3f6fb', display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip label={`${totalPersons} Person${totalPersons > 1 ? 'en' : ''}`} icon={<PeopleIcon />} size="small" />
            <Chip label={`${start} – ${ende}`} size="small" />
            {crossLocation && <Chip label="Standortübergreifend" size="small" color="info" />}
          </Paper>

          {suggestion.variants.length === 0 ? (
            <Box>
              <Alert severity="warning" sx={{ mb: 2, borderRadius: 2 }}>
                {suggestion.message || 'Keine freien Plätze verfügbar für die gewählten Kriterien.'}
              </Alert>
              <Button variant="outlined" onClick={() => setActiveStep(0)}>Suche anpassen</Button>
            </Box>
          ) : (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {suggestion.variants.length} Option{suggestion.variants.length > 1 ? 'en' : ''} gefunden — bitte auswählen:
              </Typography>
              <Box display="flex" flexDirection="column" gap={2} mb={3}>
                {suggestion.variants.map((v, idx) => {
                  const isSelected = selectedVariant === idx
                  const rooms = [...new Set(v.beds.map((b) => `${crossLocation ? b.location_name + ' · ' : ''}${b.room_name}`))]
                  return (
                    <Card
                      key={idx}
                      elevation={isSelected ? 4 : 1}
                      sx={{
                        border: `2px solid ${isSelected ? '#003366' : 'transparent'}`,
                        borderRadius: 2,
                        transition: 'all 0.15s',
                      }}
                    >
                      <CardActionArea onClick={() => setSelectedVariant(idx)} sx={{ p: 0 }}>
                        <CardContent sx={{ pb: '16px !important' }}>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            {isSelected && <CheckCircleIcon sx={{ color: '#003366', fontSize: 20 }} />}
                            <Typography fontWeight={700} color={isSelected ? '#003366' : 'text.primary'}>
                              Option {idx + 1}
                            </Typography>
                            <Chip
                              label={rooms.length === 1 ? '1 Raum' : `${rooms.length} Räume`}
                              size="small"
                              color={rooms.length === 1 ? 'success' : 'default'}
                            />
                            <Chip label={`${v.beds.length} Bett${v.beds.length > 1 ? 'en' : ''}`} size="small" />
                          </Box>
                          <Box display="flex" flexWrap="wrap" gap={0.8}>
                            {v.beds.map((b) => (
                              <Box
                                key={b.bed_id}
                                sx={{
                                  display: 'flex', alignItems: 'center', gap: 0.5,
                                  px: 1.2, py: 0.5, borderRadius: 1.5,
                                  bgcolor: '#e8f5e9', border: '1px solid #a5d6a7',
                                }}
                              >
                                <BedIcon sx={{ fontSize: 13, color: '#2e7d32' }} />
                                <Typography variant="caption" fontWeight={600} color="#1b5e20">
                                  {crossLocation ? `${b.location_name} · ` : ''}{b.room_name} Bett {b.bett_nummer}
                                </Typography>
                              </Box>
                            ))}
                          </Box>
                        </CardContent>
                      </CardActionArea>
                    </Card>
                  )
                })}
              </Box>
              <Box display="flex" gap={2}>
                <Button variant="outlined" onClick={() => setActiveStep(0)}>Zurück</Button>
                <Button
                  variant="contained"
                  onClick={() => setConfirmOpen(true)}
                  disabled={selectedVariant === null}
                  size="large"
                >
                  Option bestätigen →
                </Button>
                <Button color="error" variant="text" onClick={() => setRejectOpen(true)}>
                  Alle ablehnen
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      )}

      {/* Step 3: Done */}
      {activeStep === 2 && (
        <Box textAlign="center" py={4}>
          <CheckCircleIcon sx={{ fontSize: 64, color: completed ? '#43a047' : '#bdbdbd', mb: 2 }} />
          <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
            {completed ? 'Reservierungsanfrage dokumentiert' : 'Abgeschlossen'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Der Eintrag erscheint im Postkorb zur weiteren Bearbeitung.
          </Typography>
          <Box display="flex" gap={2} justifyContent="center">
            <Button variant="contained" onClick={() => navigate('/tasks')}>Zum Postkorb</Button>
            <Button variant="outlined" onClick={() => navigate('/')}>Zum Dashboard</Button>
          </Box>
        </Box>
      )}

      {/* Confirm Dialog */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>Reservierungsanfrage bestätigen</DialogTitle>
        <DialogContent>
          {suggestion && selectedVariant !== null && (
            <Box>
              <Typography sx={{ mb: 2 }}>
                Option {selectedVariant + 1} mit {suggestion.variants[selectedVariant].beds.length} Bett(en) vormerken:
              </Typography>
              {suggestion.variants[selectedVariant].beds.map((b) => (
                <Box key={b.bed_id} display="flex" alignItems="center" gap={1} mb={0.8}>
                  <BedIcon sx={{ color: '#2e7d32', fontSize: 18 }} />
                  <Typography variant="body2">
                    {crossLocation ? `${b.location_name} · ` : ''}{b.room_name} · Bett {b.bett_nummer}
                  </Typography>
                </Box>
              ))}
              <Alert severity="info" sx={{ mt: 2 }}>
                Die Reservierungsanfrage erscheint im Postkorb und muss von einem Berechtigten endgültig bestätigt werden.
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setConfirmOpen(false)}>Abbrechen</Button>
          <Button variant="contained" onClick={handleAccept} disabled={loading}>
            {loading ? <CircularProgress size={18} /> : 'Jetzt bestätigen'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectOpen} onClose={() => setRejectOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>Anfrage ablehnen</DialogTitle>
        <DialogContent>
          <TextField
            label="Begründung"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            fullWidth
            multiline
            rows={3}
            sx={{ mt: 1 }}
            placeholder="Warum werden alle Optionen abgelehnt?"
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setRejectOpen(false)}>Zurück</Button>
          <Button color="error" variant="contained" onClick={handleReject} disabled={!rejectReason.trim() || loading}>
            Ablehnen
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={5000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
