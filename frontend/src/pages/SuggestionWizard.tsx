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
  bed_labels: string[]
}
interface OccupantSearchResult {
  azr_id: string
  occ_labels: string[] | null
  geschlecht: string
  location_name: string
  location_id: string
  room_type: string
  room_name: string
  belegung_ende: string
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

function SearchResultList({ results, locationId, pendingAzrIds, onSelect }: {
  results: OccupantSearchResult[]
  locationId: string | null
  pendingAzrIds: Set<string>
  onSelect: (p: OccupantSearchResult) => void
}) {
  const ownWb = locationId ? results.filter(p => p.location_id === locationId && p.room_type === 'WARTEBEREICH') : []
  const ownOther = locationId ? results.filter(p => p.location_id === locationId && p.room_type !== 'WARTEBEREICH') : []
  const external = locationId ? results.filter(p => p.location_id !== locationId) : results

  const renderGroup = (persons: OccupantSearchResult[], label: string, borderColor: string) => {
    if (persons.length === 0) return null
    return (
      <Box mb={0.5}>
        <Typography variant="overline" sx={{ fontSize: 9, color: borderColor, fontWeight: 700, display: 'block', lineHeight: 1.6 }}>{label}</Typography>
        <Box display="flex" flexDirection="column" gap={0.4}>
          {persons.map((person, pi) => (
            <Box
              key={`${person.azr_id}-${pi}`}
              onClick={() => onSelect(person)}
              sx={{
                p: 0.8, borderRadius: 1, border: '1px solid #e0e0e0',
                borderLeft: `3px solid ${borderColor}`, cursor: 'pointer', bgcolor: 'white',
                '&:hover': { bgcolor: '#f5f5f5', borderColor: borderColor },
              }}
            >
              <Box display="flex" alignItems="center" gap={0.6} flexWrap="wrap">
                <Typography variant="body2" fontWeight={700} fontFamily="monospace" fontSize={12}>{person.azr_id}</Typography>
                <GenderChip g={person.geschlecht} />
                {person.room_name && <Typography variant="caption" color="text.secondary">· {person.room_name}</Typography>}
                {person.location_name && <Typography variant="caption" color="text.secondary">({person.location_name})</Typography>}
                {person.belegung_ende && <Typography variant="caption" color="text.secondary">bis {new Date(person.belegung_ende).toLocaleDateString('de-DE')}</Typography>}
                {pendingAzrIds.has(person.azr_id.trim()) && (
                  <Chip label="⚠ Anfrage läuft" size="small" sx={{ height: 16, fontSize: 9, bgcolor: '#fff8e1', color: '#e65100', fontWeight: 700 }} />
                )}
              </Box>
              {(person.occ_labels ?? []).length > 0 && (
                <Box mt={0.3} display="flex" gap={0.3} flexWrap="wrap">
                  {(person.occ_labels ?? []).map(lbl => (
                    <Chip key={lbl} label={lbl} size="small" sx={{ height: 14, fontSize: 9, fontWeight: 600, bgcolor: '#ede7f6', color: '#6a1b9a' }} />
                  ))}
                </Box>
              )}
            </Box>
          ))}
        </Box>
      </Box>
    )
  }

  return (
    <Box mt={0.8} sx={{ maxHeight: 260, overflowY: 'auto', pr: 0.5 }}>
      {renderGroup(ownWb, 'Wartebereich — eigene Einrichtung', '#2e7d32')}
      {renderGroup(ownOther, 'Eigene Einrichtung', '#1565c0')}
      {renderGroup(external, 'Andere Einrichtungen', '#757575')}
    </Box>
  )
}

export default function SuggestionWizard() {
  const { post, get, patch } = useApiClient()
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

  // Per-bed assignments for "Belegung vormerken" (no person context)
  interface BedAssignment {
    bed_id: string; azr_id: string; geschlecht: string; labels: string[];
    searching: boolean; searchDone: boolean; searchFound: boolean
    foundLocation?: string; foundEnde?: string; foundLocationId?: string
    searchResults: OccupantSearchResult[]
    warteplatzOpen: boolean; warteplatzGeschlecht: string; warteplatzLabels: string[]
    warteplatzEnde: string; warteplatzFreeBedId?: string; warteplatzLoading: boolean
    warteplatzCreated?: boolean
  }
  const [bedAssignments, setBedAssignments] = useState<BedAssignment[]>([])
  // Person labels for hasPerson confirm dialog
  const [confirmPersonLabels, setConfirmPersonLabels] = useState<string[]>([])
  const [groupPersonLabels, setGroupPersonLabels] = useState<Record<string, string[]>>({})
  // Pending reservation AZR-IDs for active-request warning
  const [pendingReservationAzrIds, setPendingReservationAzrIds] = useState<Set<string>>(new Set())
  // Label catalog for occupant labels (Warteplatz)
  const [occLabelCatalog, setOccLabelCatalog] = useState<string[]>([])

  useEffect(() => {
    get<{ items: Array<{ name: string; entity_types: string[] }> }>('/api/labels')
      .then((res) => {
        setRoomLabelCatalog(res.items.filter((e) => e.entity_types.includes('ROOM')).map((e) => e.name))
        setOccLabelCatalog(res.items.filter((e) => e.entity_types.includes('OCCUPANT')).map((e) => e.name))
      })
      .catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (hasPerson) return
    get<Array<{ azr_id: string }>>('/api/reservations?status=PENDING')
      .then((res) => setPendingReservationAzrIds(new Set(res.map((r) => r.azr_id))))
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

  async function handleOpenConfirm() {
    if (!selectedVariantData) return
    if (!hasPerson) {
      setBedAssignments(selectedVariantData.beds.map(b => ({
        bed_id: b.bed_id, azr_id: '', geschlecht: 'M', labels: [],
        searching: false, searchDone: false, searchFound: false, searchResults: [],
        warteplatzOpen: false, warteplatzGeschlecht: 'M', warteplatzLabels: [],
        warteplatzEnde: in30, warteplatzLoading: false, warteplatzCreated: false,
      })))
    } else if (isGroupMode && modus !== 'einzeln') {
      const map: Record<string, string[]> = {}
      for (const person of preGroup) {
        try {
          type OccRes = { azr_id: string; occ_labels: string[] }
          const res = await get<OccRes[]>(`/api/occupants/search?q=${encodeURIComponent(person.azr_id)}`)
          const found = res.find(r => r.azr_id === person.azr_id)
          if (found) map[person.azr_id] = (found.occ_labels as string[]) ?? []
        } catch {}
      }
      setGroupPersonLabels(map)
    } else if (currentPerson) {
      try {
        type OccRes = { azr_id: string; occ_labels: string[] }
        const res = await get<OccRes[]>(`/api/occupants/search?q=${encodeURIComponent(currentPerson.azr_id)}`)
        const found = res.find(r => r.azr_id === currentPerson.azr_id)
        setConfirmPersonLabels((found?.occ_labels as string[]) ?? [])
      } catch { setConfirmPersonLabels([]) }
    }
    setConfirmOpen(true)
  }

  async function searchPersonForBed(idx: number) {
    const azrId = bedAssignments[idx]?.azr_id.trim()
    // Leeres Feld → Wildcard-Suche (*) — zeigt alle aktiven Personen
    const searchQuery = azrId || '*'
    setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, searching: true, searchDone: false } : a))
    try {
      const res = await get<OccupantSearchResult[]>(`/api/occupants/search?q=${encodeURIComponent(searchQuery)}`)
      const exact = azrId ? res.find(r => r.azr_id.toLowerCase() === azrId.toLowerCase()) : null
      if (exact) {
        setBedAssignments(prev => prev.map((a, i) => i === idx ? {
          ...a,
          labels: Array.isArray(exact.occ_labels) ? exact.occ_labels : [],
          geschlecht: exact.geschlecht || a.geschlecht,
          foundLocation: exact.location_name,
          foundEnde: exact.belegung_ende,
          foundLocationId: exact.location_id,
          searching: false, searchDone: true, searchFound: true, searchResults: [],
        } : a))
      } else if (res.length > 0) {
        setBedAssignments(prev => prev.map((a, i) => i === idx ? {
          ...a, labels: [], searching: false, searchDone: true, searchFound: false,
          foundLocation: undefined, foundEnde: undefined, searchResults: res,
        } : a))
      } else {
        setBedAssignments(prev => prev.map((a, i) => i === idx ? {
          ...a, labels: [], searching: false, searchDone: true, searchFound: false,
          foundLocation: undefined, foundEnde: undefined, searchResults: [],
        } : a))
      }
    } catch {
      setBedAssignments(prev => prev.map((a, i) => i === idx ? {
        ...a, searching: false, searchDone: true, searchFound: false, searchResults: [],
      } : a))
    }
  }

  async function handleOpenWarteplatz(idx: number) {
    if (!locationId) return
    setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, warteplatzLoading: true } : a))
    try {
      type BedStatusRoom = { room_type: string; beds: Array<{ bed_id: string; bett_nummer: string; status: string }> }
      const rooms = await get<BedStatusRoom[]>(`/api/locations/${locationId}/bed-status`)
      const freeBed = rooms
        .filter((r) => r.room_type === 'WARTEBEREICH')
        .flatMap((r) => r.beds.filter((b) => b.status === 'FREI'))
        .sort((a, b) => a.bett_nummer.localeCompare(b.bett_nummer, undefined, { numeric: true }))[0]
      if (!freeBed) {
        setSnackbar({ open: true, message: 'Kein freier Warteplatz verfügbar — Person bitte manuell einbuchen.', severity: 'error' })
        setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, warteplatzLoading: false } : a))
        return
      }
      setBedAssignments(prev => prev.map((a, i) => i === idx ? {
        ...a, warteplatzLoading: false, warteplatzOpen: true, warteplatzFreeBedId: freeBed.bed_id,
      } : a))
    } catch {
      setSnackbar({ open: true, message: 'Bett-Status konnte nicht geladen werden.', severity: 'error' })
      setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, warteplatzLoading: false } : a))
    }
  }

  async function handleSubmitWarteplatz(idx: number) {
    const a = bedAssignments[idx]
    if (!a?.warteplatzFreeBedId || !a.azr_id.trim()) return
    setBedAssignments(prev => prev.map((b, i) => i === idx ? { ...b, warteplatzLoading: true } : b))
    try {
      type OccResp = { id: string; azr_id: string; geschlecht: string }
      const occ = await post<OccResp>(`/api/beds/${a.warteplatzFreeBedId}/occupancy`, {
        azr_id: a.azr_id.trim(),
        geschlecht: a.warteplatzGeschlecht,
        belegung_start: today,
        belegung_ende: a.warteplatzEnde,
      })
      if (a.warteplatzLabels.length > 0) {
        await patch(`/api/occupancy/${occ.id}/labels`, { labels: a.warteplatzLabels })
      }
      setBedAssignments(prev => prev.map((b, i) => i === idx ? {
        ...b,
        geschlecht: a.warteplatzGeschlecht,
        labels: a.warteplatzLabels,
        searchDone: true, searchFound: true, searching: false,
        // warteplatzCreated-Flag verhindert Doppelbelegung des Zielbetts in handleAccept
        foundLocation: 'Wartebereich', foundLocationId: locationId ?? undefined,
        warteplatzOpen: false, warteplatzLoading: false, warteplatzCreated: true,
      } : b))
      setSnackbar({ open: true, message: `Warteplatz für ${a.azr_id.trim()} angelegt. Person kann jetzt verlegt werden.`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Warteplatz-Anlage fehlgeschlagen.', severity: 'error' })
      setBedAssignments(prev => prev.map((b, i) => i === idx ? { ...b, warteplatzLoading: false } : b))
    }
  }

  async function handleAccept() {
    if (!suggestion || selectedVariant === null) return
    const variant = suggestion.variants[selectedVariant]
    setLoading(true)

    if (hasPerson && !currentPerson && !(isGroupMode && modus !== 'einzeln')) {
      setSnackbar({ open: true, message: 'Person hat kein aktives Bett — bitte zuerst im Wartebereich einbuchen.', severity: 'error' })
      setLoading(false)
      return
    }

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
            geburtsjahr: new Date().getFullYear() - 30,
            herkunftsland: 'UNK',
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
          geburtsjahr: new Date().getFullYear() - 30,
          herkunftsland: 'UNK',
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
      // No person context: Belegung vormerken / Verlegungsanfrage
      try {
        type BedStatusRoom = { room_type: string; beds: Array<{ bed_id: string; bett_nummer: string; status: string }> }

        const hasPerson = bedAssignments.some(a => a.azr_id.trim())
        if (!hasPerson) {
          // Kein Personenbezug → Suggestion vormerken (lokale Belegungsvormerkung)
          await post(`/api/suggestions/${suggestion.suggestion_id}/accept`, { variant_index: selectedVariant })
        } else {
          for (let i = 0; i < bedAssignments.length; i++) {
            const a = bedAssignments[i]
            if (!a.azr_id.trim()) continue
            const targetBed = variant.beds[i] ?? variant.beds[0]
            const isCrossLocation = !!targetBed?.location_id && targetBed.location_id !== locationId

            if (a.warteplatzCreated) {
              // Person bereits manuell im Wartebereich eingebucht → Reservation senden wenn cross-location
              if (isCrossLocation && targetBed?.location_id) {
                await post('/api/reservations', {
                  target_location_id: targetBed.location_id,
                  azr_id: a.azr_id.trim(),
                  geschlecht: a.geschlecht,
                  geburtsjahr: new Date().getFullYear() - 30,
                  herkunftsland: 'UNK',
                  belegung_start: start,
                  belegung_ende: ende,
                  suggested_bed_id: targetBed.bed_id ?? null,
                })
              }
            } else if (a.searchDone && !a.searchFound && isCrossLocation && locationId) {
              // Neue Person (nicht im System) + Cross-Location:
              // 1. Freies Wartebereich-Bett finden und Person dort einbuchen
              // 2. Dann Verlegungsanfrage an Zieleinrichtung senden
              const rooms = await get<BedStatusRoom[]>(`/api/locations/${locationId}/bed-status`)
              const freeBed = rooms
                .filter(r => r.room_type === 'WARTEBEREICH')
                .flatMap(r => r.beds.filter(b => b.status === 'FREI'))
                .sort((x, y) => x.bett_nummer.localeCompare(y.bett_nummer, undefined, { numeric: true }))[0]
              if (!freeBed) {
                setSnackbar({ open: true, message: `Kein freier Warteplatz für ${a.azr_id.trim()} verfügbar — bitte manuell einbuchen.`, severity: 'error' })
                setLoading(false)
                return
              }
              await post(`/api/beds/${freeBed.bed_id}/occupancy`, {
                azr_id: a.azr_id.trim(),
                geschlecht: a.geschlecht,
                belegung_start: today,
                belegung_ende: ende,
              })
              if (targetBed?.location_id) {
                await post('/api/reservations', {
                  target_location_id: targetBed.location_id,
                  azr_id: a.azr_id.trim(),
                  geschlecht: a.geschlecht,
                  geburtsjahr: new Date().getFullYear() - 30,
                  herkunftsland: 'UNK',
                  belegung_start: start,
                  belegung_ende: ende,
                  suggested_bed_id: targetBed.bed_id ?? null,
                })
              }
            } else {
              // Bekannte Person ODER lokales Zielbett → direkte Buchung
              await post(`/api/beds/${a.bed_id}/occupancy`, {
                azr_id: a.azr_id.trim(),
                geschlecht: a.geschlecht,
                belegung_start: today,
                belegung_ende: ende,
              })
            }
          }
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
                  <Button variant="contained" onClick={handleOpenConfirm}
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
      <Dialog
        open={confirmOpen}
        onClose={() => { setConfirmOpen(false); setBedAssignments([]); setConfirmPersonLabels([]); setGroupPersonLabels({}) }}
        maxWidth="sm" fullWidth
      >
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

          {/* ── hasPerson: Gruppe (alle Personen auf einmal) ── */}
          {hasPerson && isGroupMode && modus !== 'einzeln' && selectedVariantData && (
            <>
              <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
                <Typography variant="caption" fontWeight={700} color="#6a1b9a" sx={{ display: 'block', mb: 1 }}>
                  Gruppe ({preGroup.length} Personen) → {selectedVariantData.location_name || selectedVariantData.beds[0]?.location_name}
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  {preGroup.map((p, i) => {
                    const bed = selectedVariantData.beds[i]
                    const pLabels = groupPersonLabels[p.azr_id] ?? []
                    return (
                      <Box key={p.azr_id} sx={{ p: 1, border: '1px solid #ce93d8', borderRadius: 1, bgcolor: 'white' }}>
                        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                          <PersonIcon sx={{ fontSize: 16, color: '#6a1b9a' }} />
                          <Typography variant="body2" fontWeight={700} fontFamily="monospace">{p.azr_id}</Typography>
                          <GenderChip g={p.geschlecht} />
                          {bed && (
                            <>
                              <Typography variant="caption" color="text.secondary">→</Typography>
                              <BedIcon sx={{ fontSize: 14, color: '#2e7d32' }} />
                              <Typography variant="body2" fontWeight={600}>{bed.room_name} · {bed.bett_nummer}</Typography>
                            </>
                          )}
                        </Box>
                        {pLabels.length > 0 && (
                          <Box mt={0.5} display="flex" gap={0.4} flexWrap="wrap">
                            {pLabels.map(lbl => <Chip key={lbl} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#ede7f6', color: '#6a1b9a' }} />)}
                          </Box>
                        )}
                        {bed && (bed.room_labels ?? []).length > 0 && (
                          <Box mt={0.4} display="flex" gap={0.4} flexWrap="wrap">
                            {bed.room_labels.map(lbl => <Chip key={lbl} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#e3f2fd', color: '#1565c0' }} />)}
                          </Box>
                        )}
                        {bed && (bed.bed_labels ?? []).length > 0 && (
                          <Box mt={0.3} display="flex" gap={0.4} flexWrap="wrap">
                            {bed.bed_labels.map(lbl => <Chip key={`bl-${lbl}`} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#f3e5f5', color: '#6a1b9a' }} />)}
                          </Box>
                        )}
                      </Box>
                    )
                  })}
                </Box>
              </Paper>
            </>
          )}

          {/* ── hasPerson: Einzelperson ── */}
          {hasPerson && currentPerson && (!isGroupMode || modus === 'einzeln') && (
            <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f3e5f5', borderRadius: 1.5, border: '1px solid #ce93d8' }}>
              <Typography variant="caption" fontWeight={700} color="#6a1b9a" sx={{ display: 'block', mb: 0.5 }}>
                Person
              </Typography>
              <Box display="flex" gap={1.5} alignItems="center" flexWrap="wrap">
                <Typography fontWeight={700} fontFamily="monospace">{currentPerson.azr_id}</Typography>
                <GenderChip g={currentPerson.geschlecht} />
              </Box>
              {confirmPersonLabels.length > 0 && (
                <Box mt={0.8} display="flex" gap={0.5} flexWrap="wrap">
                  {confirmPersonLabels.map(lbl => (
                    <Chip key={lbl} label={lbl} size="small" sx={{ height: 18, fontSize: 10, fontWeight: 600, bgcolor: '#ede7f6', color: '#6a1b9a' }} />
                  ))}
                </Box>
              )}
            </Paper>
          )}

          {/* ── hasPerson: Ziel-Einrichtung + Betten mit Labels ── */}
          {hasPerson && (!isGroupMode || modus === 'einzeln') && selectedVariantData && (
            <Box>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <LocationOnIcon sx={{ color: '#6a1b9a', fontSize: 18 }} />
                <Typography fontWeight={700} color="#6a1b9a">
                  {selectedVariantData.location_name || selectedVariantData.beds[0]?.location_name}
                </Typography>
              </Box>
              {selectedVariantData.beds.map((b) => (
                <Box key={b.bed_id} mb={0.8}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <BedIcon sx={{ color: '#2e7d32', fontSize: 18 }} />
                    <Typography variant="body2">{b.room_name} · Bett {b.bett_nummer}</Typography>
                  </Box>
                  {(b.room_labels ?? []).length > 0 && (
                    <Box ml={3.5} mt={0.3} display="flex" gap={0.4} flexWrap="wrap">
                      {b.room_labels.map(lbl => <Chip key={lbl} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#e3f2fd', color: '#1565c0' }} />)}
                    </Box>
                  )}
                  {(b.bed_labels ?? []).length > 0 && (
                    <Box ml={3.5} mt={0.2} display="flex" gap={0.4} flexWrap="wrap">
                      {b.bed_labels.map(lbl => <Chip key={`bl-${lbl}`} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#f3e5f5', color: '#6a1b9a' }} />)}
                    </Box>
                  )}
                </Box>
              ))}
            </Box>
          )}

          {/* ── !hasPerson: Pro-Bett-Zuweisung ── */}
          {!hasPerson && selectedVariantData && (
            <>
              <Box display="flex" alignItems="center" gap={1}>
                <LocationOnIcon sx={{ color: '#003366', fontSize: 18 }} />
                <Typography fontWeight={700} color="#003366">
                  {selectedVariantData.location_name || selectedVariantData.beds[0]?.location_name}
                </Typography>
              </Box>
              {bedAssignments.map((assignment, idx) => {
                const bed = selectedVariantData.beds[idx]
                if (!bed) return null
                return (
                  <Paper key={assignment.bed_id} elevation={0} sx={{ p: 1.5, border: '1px solid #e0e0e0', borderRadius: 1.5 }}>
                    {/* Bett-Info + Raum-Labels + Bett-Labels */}
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <BedIcon sx={{ color: '#2e7d32', fontSize: 18 }} />
                      <Typography variant="body2" fontWeight={700}>{bed.room_name} · Bett {bed.bett_nummer}</Typography>
                    </Box>
                    {(bed.room_labels ?? []).length > 0 && (
                      <Box mb={0.4} display="flex" gap={0.4} flexWrap="wrap">
                        {bed.room_labels.map(lbl => <Chip key={lbl} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#e3f2fd', color: '#1565c0' }} />)}
                      </Box>
                    )}
                    {(bed.bed_labels ?? []).length > 0 && (
                      <Box mb={1} display="flex" gap={0.4} flexWrap="wrap">
                        {bed.bed_labels.map(lbl => <Chip key={`bl-${lbl}`} label={lbl} size="small" sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: '#f3e5f5', color: '#6a1b9a' }} />)}
                      </Box>
                    )}
                    {/* AZR + Geschlecht + Suche */}
                    <Box display="flex" gap={1} alignItems="flex-start" flexWrap="wrap">
                      <TextField
                        label="AZR-ID" size="small" value={assignment.azr_id}
                        onChange={(e) => setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, azr_id: e.target.value, searchDone: false, searchFound: false, labels: [], foundLocation: undefined, foundEnde: undefined, foundLocationId: undefined, searchResults: [], warteplatzOpen: false } : a))}
                        onKeyDown={(e) => { if (e.key === 'Enter') searchPersonForBed(idx) }}
                        placeholder="AZR-2024-0001-M01"
                        sx={{ flex: 2, minWidth: 150 }}
                      />
                      <FormControl size="small" sx={{ flex: 1, minWidth: 100 }}>
                        <InputLabel>Geschlecht</InputLabel>
                        <Select value={assignment.geschlecht} label="Geschlecht"
                          onChange={(e) => setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, geschlecht: e.target.value as string } : a))}>
                          <MenuItem value="M">Männlich</MenuItem>
                          <MenuItem value="W">Weiblich</MenuItem>
                          <MenuItem value="D">Divers</MenuItem>
                        </Select>
                      </FormControl>
                      <Button size="small" variant="outlined" onClick={() => searchPersonForBed(idx)}
                        disabled={assignment.searching}
                        startIcon={assignment.searching ? <CircularProgress size={14} /> : <SearchIcon />}
                        sx={{ mt: 0.5, whiteSpace: 'nowrap' }}>
                        {assignment.azr_id.trim() ? 'Suchen' : 'Alle anzeigen'}
                      </Button>
                    </Box>
                    {/* Suchergebnis-Feedback */}
                    {assignment.searchDone && assignment.searchFound && (
                      <Box mt={0.8} sx={{ p: 0.8, bgcolor: assignment.warteplatzCreated ? '#fff3e0' : '#f1f8e9', border: `1px solid ${assignment.warteplatzCreated ? '#ffb74d' : '#a5d6a7'}`, borderRadius: 1 }}>
                        <Box display="flex" alignItems="center" gap={0.5} flexWrap="wrap">
                          <CheckCircleIcon sx={{ fontSize: 14, color: assignment.warteplatzCreated ? '#f57c00' : '#2e7d32' }} />
                          <Typography variant="caption" fontWeight={700} color={assignment.warteplatzCreated ? '#f57c00' : '#2e7d32'}>
                            {assignment.warteplatzCreated ? 'Warteplatz angelegt' : 'Person gefunden'}
                          </Typography>
                          {assignment.foundLocation && (
                            <Typography variant="caption" color="text.secondary">
                              · {assignment.warteplatzCreated ? 'in' : 'aktuell:'} {assignment.foundLocation}
                              {!assignment.warteplatzCreated && assignment.foundEnde && ` bis ${assignment.foundEnde}`}
                            </Typography>
                          )}
                        </Box>
                        {assignment.warteplatzCreated && (
                          <Typography variant="caption" sx={{ display: 'block', mt: 0.4, color: '#e65100' }}>
                            Das vorgeschlagene Bett wird nicht direkt gebucht — Person per Verlegungsanfrage zuweisen.
                          </Typography>
                        )}
                        {assignment.labels.length > 0 ? (
                          <Box mt={0.4} display="flex" gap={0.4} flexWrap="wrap">
                            {assignment.labels.map(lbl => <Chip key={lbl} label={lbl} size="small" sx={{ height: 17, fontSize: 9, fontWeight: 600, bgcolor: '#ede7f6', color: '#6a1b9a' }} />)}
                          </Box>
                        ) : (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.3 }}>
                            Keine Labels hinterlegt
                          </Typography>
                        )}
                      </Box>
                    )}
                    {/* Banners: externe Person + aktive Anfrage */}
                    {assignment.searchFound && locationId && assignment.foundLocationId && assignment.foundLocationId !== locationId && (
                      <Box mt={0.8} sx={{ p: 0.8, bgcolor: '#e3f2fd', border: '1px solid #90caf9', borderRadius: 1, display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                        <Typography variant="caption" color="#1565c0" fontWeight={600}>ℹ Diese Person ist in einer Fremdeinrichtung eingebucht — eine Verlegung muss vorab abgestimmt sein.</Typography>
                      </Box>
                    )}
                    {assignment.searchFound && pendingReservationAzrIds.has(assignment.azr_id.trim()) && (
                      <Box mt={0.8} sx={{ p: 0.8, bgcolor: '#fff8e1', border: '1px solid #ffe082', borderRadius: 1, display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                        <Typography variant="caption" color="#e65100" fontWeight={600}>⚠ Für diese Person läuft bereits eine Anfrage dieser Einrichtung.</Typography>
                      </Box>
                    )}
                    {/* Gruppierte Trefferliste */}
                    {assignment.searchDone && !assignment.searchFound && assignment.searchResults.length > 0 && (
                      <SearchResultList
                        results={assignment.searchResults}
                        locationId={locationId}
                        pendingAzrIds={pendingReservationAzrIds}
                        onSelect={(person) => setBedAssignments(prev => prev.map((a, i) => i === idx ? {
                          ...a,
                          azr_id: person.azr_id,
                          labels: Array.isArray(person.occ_labels) ? person.occ_labels : [],
                          geschlecht: person.geschlecht || a.geschlecht,
                          foundLocation: person.location_name,
                          foundEnde: person.belegung_ende,
                          foundLocationId: person.location_id,
                          searchDone: true, searchFound: true, searching: false,
                          searchResults: [],
                        } : a))}
                      />
                    )}
                    {/* Keine Treffer: Warteplatz anlegen */}
                    {assignment.searchDone && !assignment.searchFound && assignment.searchResults.length === 0 && assignment.azr_id.trim() && (
                      <Box mt={0.8}>
                        <Box sx={{ p: 1, bgcolor: '#fff3e0', border: '1px solid #ffb74d', borderRadius: 1, mb: 0.8 }}>
                          <Typography variant="caption" color="#e65100" fontWeight={700} sx={{ display: 'block', mb: 0.4 }}>
                            AZR-ID „{assignment.azr_id.trim()}" ist noch nicht im System bekannt.
                          </Typography>
                          <Typography variant="caption" color="#bf360c" sx={{ display: 'block' }}>
                            Es wird automatisch ein Warteplatz in Ihrer Einrichtung angelegt. Von dort kann die Person anschließend über eine Verlegungsanfrage einem Bett zugewiesen werden. Bitte AZR-ID prüfen, falls es sich um einen Tippfehler handelt.
                          </Typography>
                        </Box>
                        {!assignment.warteplatzOpen && (
                          <Box display="flex" gap={1} flexWrap="wrap">
                            <Button size="small" variant="outlined" color="warning"
                              disabled={assignment.warteplatzLoading}
                              startIcon={assignment.warteplatzLoading ? <CircularProgress size={12} /> : undefined}
                              onClick={() => handleOpenWarteplatz(idx)}
                              sx={{ fontSize: 11 }}>
                              Warteplatz anlegen für {assignment.azr_id.trim()}
                            </Button>
                            <Button size="small" variant="text" color="inherit"
                              onClick={() => setBedAssignments(prev => prev.map((a, i) => i === idx ? {
                                ...a, azr_id: '', searchDone: false, searchFound: false, searchResults: [],
                                foundLocation: undefined, foundEnde: undefined, foundLocationId: undefined,
                              } : a))}
                              sx={{ fontSize: 11, color: '#888' }}>
                              AZR korrigieren
                            </Button>
                          </Box>
                        )}
                        {assignment.warteplatzOpen && (
                          <Box sx={{ p: 1, border: '1px solid #a5d6a7', borderRadius: 1, bgcolor: '#f1f8e9', mt: 0.5 }}>
                            <Typography variant="caption" fontWeight={700} color="#2e7d32" sx={{ display: 'block', mb: 1 }}>
                              Warteplatz anlegen — {assignment.azr_id.trim()}
                            </Typography>
                            <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
                              <FormControl size="small" sx={{ minWidth: 110 }}>
                                <InputLabel>Geschlecht *</InputLabel>
                                <Select value={assignment.warteplatzGeschlecht} label="Geschlecht *"
                                  disabled={assignment.warteplatzLoading}
                                  onChange={(e) => setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, warteplatzGeschlecht: e.target.value } : a))}>
                                  <MenuItem value="M">Männlich</MenuItem>
                                  <MenuItem value="W">Weiblich</MenuItem>
                                  <MenuItem value="D">Divers</MenuItem>
                                </Select>
                              </FormControl>
                              <TextField size="small" label="Bis (Datum)" type="date" value={assignment.warteplatzEnde}
                                disabled={assignment.warteplatzLoading}
                                onChange={(e) => setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, warteplatzEnde: e.target.value } : a))}
                                InputLabelProps={{ shrink: true }} sx={{ minWidth: 140 }} />
                            </Box>
                            {occLabelCatalog.length > 0 && (
                              <Box mb={1}>
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.3 }}>Labels (optional):</Typography>
                                <Box display="flex" gap={0.4} flexWrap="wrap">
                                  {occLabelCatalog.map(lbl => {
                                    const sel = assignment.warteplatzLabels.includes(lbl)
                                    return (
                                      <Chip key={lbl} label={lbl} size="small" clickable={!assignment.warteplatzLoading}
                                        onClick={() => !assignment.warteplatzLoading && setBedAssignments(prev => prev.map((a, i) => i === idx ? {
                                          ...a, warteplatzLabels: sel ? a.warteplatzLabels.filter(l => l !== lbl) : [...a.warteplatzLabels, lbl]
                                        } : a))}
                                        sx={{ height: 20, fontSize: 10, bgcolor: sel ? '#ede7f6' : '#f5f5f5', color: sel ? '#6a1b9a' : 'text.secondary', fontWeight: sel ? 700 : 400 }} />
                                    )
                                  })}
                                </Box>
                              </Box>
                            )}
                            <Box display="flex" gap={1}>
                              <Button size="small" variant="contained" color="success"
                                disabled={assignment.warteplatzLoading || !assignment.warteplatzGeschlecht || !assignment.warteplatzEnde}
                                startIcon={assignment.warteplatzLoading ? <CircularProgress size={12} /> : undefined}
                                onClick={() => handleSubmitWarteplatz(idx)}
                                sx={{ fontSize: 11 }}>
                                Warteplatz bestätigen
                              </Button>
                              <Button size="small" variant="text"
                                onClick={() => setBedAssignments(prev => prev.map((a, i) => i === idx ? { ...a, warteplatzOpen: false } : a))}
                                sx={{ fontSize: 11 }}>
                                Abbrechen
                              </Button>
                            </Box>
                          </Box>
                        )}
                      </Box>
                    )}
                    {!assignment.searchDone && !assignment.searching && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block', fontStyle: 'italic' }}>
                        {assignment.azr_id.trim()
                          ? '→ „Suchen" klicken oder Enter drücken um Person zu laden'
                          : '→ „Alle anzeigen" klicken oder * eingeben für Wildcard-Suche'}
                      </Typography>
                    )}
                  </Paper>
                )
              })}
              {bedAssignments.some(a => a.azr_id.trim()) && (
                <Alert severity="info" sx={{ py: 0.5, fontSize: 12 }}>
                  Eingebuchte Belegungen werden direkt im Protokoll erfasst.
                </Alert>
              )}
            </>
          )}

          <Box display="flex" gap={2}>
            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>Zeitraum:</Typography>
            <Typography variant="body2" fontWeight={600}>{start} – {ende}</Typography>
          </Box>

          {hasPerson && (
            <Alert severity="info" sx={{ py: 0.5, fontSize: 12 }}>
              Die Anfrage erscheint im Postkorb der Ziel-Einrichtung und muss dort bestätigt werden.
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => { setConfirmOpen(false); setBedAssignments([]); setConfirmPersonLabels([]); setGroupPersonLabels({}) }}>
            Abbrechen
          </Button>
          <Button variant="contained" onClick={handleAccept}
            disabled={loading}
            sx={hasPerson ? { bgcolor: '#6a1b9a', '&:hover': { bgcolor: '#4a148c' } } : {}}>
            {loading ? <CircularProgress size={18} /> : hasPerson
              ? 'Verlegungsanfrage senden'
              : bedAssignments.some(a => a.azr_id.trim() && !a.warteplatzCreated)
                ? 'Jetzt einbuchen'
                : bedAssignments.some(a => a.warteplatzCreated)
                  ? 'Abschließen'
                  : 'Jetzt vormerken'}
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
