import { useEffect, useRef, useState } from 'react'
import {
  Autocomplete,
  Box,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import LocalOfferIcon from '@mui/icons-material/LocalOffer'
import LockIcon from '@mui/icons-material/Lock'
import AddIcon from '@mui/icons-material/Add'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import { useApiClient } from '../api/client'

export interface LabelCatalogEntry {
  name: string
  category: string
  entity_types: string[]
  color: string
  is_system?: boolean
}

interface Props {
  labels: string[]
  entityType: 'ROOM' | 'BED' | 'OCCUPANCY' | 'LOCATION'
  entityId: string
  readOnly?: boolean
  compact?: boolean
  onSaved?: (labels: string[]) => void
  /** Labels that cannot be removed (shown with lock icon + tooltip) */
  lockedLabels?: string[]
  lockedTooltip?: string
}

// Farben pro Kategorie (Fallback wenn kein Catalog-Entry vorhanden)
const CATEGORY_COLORS: Record<string, string> = {
  Ausstattung: '#1565c0',
  Eignung: '#6a1b9a',
  Position: '#e65100',
  Typ: '#00695c',
  Schutz: '#b71c1c',
  Sprache: '#00796b',
  Hinweis: '#558b2f',
  Gruppe: '#455a64',
  Sonstige: '#757575',
}

function getLabelColor(name: string, catalog: LabelCatalogEntry[]): string {
  const entry = catalog.find((e) => e.name === name)
  if (entry) return entry.color
  return '#757575'
}

function getLabelBg(color: string): string {
  return color + '18'
}

export default function LabelChips({ labels, entityType, entityId, readOnly = false, compact = false, onSaved, lockedLabels = [], lockedTooltip }: Props) {
  const { get, patch } = useApiClient()
  const [catalog, setCatalog] = useState<LabelCatalogEntry[]>([])
  const [editing, setEditing] = useState(false)
  const [current, setCurrent] = useState<string[]>(labels)
  const [inputVal, setInputVal] = useState('')
  const [saving, setSaving] = useState(false)
  const catalogLoaded = useRef(false)

  useEffect(() => { setCurrent(labels) }, [labels])

  async function loadCatalog() {
    if (catalogLoaded.current) return
    try {
      const res = await get<{ items: LabelCatalogEntry[] }>('/api/labels')
      setCatalog(res.items.filter((e) => e.entity_types.includes(entityType)))
      catalogLoaded.current = true
    } catch { /* ignore */ }
  }

  // Load catalog on mount so chip colors are correct even before user starts editing
  useEffect(() => { loadCatalog() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function startEdit() {
    loadCatalog()
    setEditing(true)
  }

  function addLabel(label: string) {
    const trimmed = label.trim()
    if (!trimmed || current.includes(trimmed)) return
    setCurrent((prev) => [...prev, trimmed])
    setInputVal('')
  }

  function removeLabel(label: string) {
    setCurrent((prev) => prev.filter((l) => l !== label))
  }

  const [saveError, setSaveError] = useState('')

  async function save() {
    // entityId="new" → nur lokal speichern, kein API-Call
    if (entityId === 'new') {
      onSaved?.(current)
      setEditing(false)
      return
    }
    setSaving(true)
    setSaveError('')
    try {
      const pathMap: Record<string, string> = {
        ROOM: `/api/rooms/${entityId}/labels`,
        BED: `/api/beds/${entityId}/labels`,
        OCCUPANCY: `/api/occupancy/${entityId}/labels`,
        LOCATION: `/api/locations/${entityId}/labels`,
      }
      await patch(pathMap[entityType], { labels: current })
      onSaved?.(current)
      setEditing(false)
    } catch (e: unknown) {
      const msg = (e as { detail?: { detail?: string } })?.detail?.detail ?? 'Labels konnten nicht gespeichert werden.'
      setSaveError(msg)
    } finally {
      setSaving(false)
    }
  }

  function cancel() {
    setCurrent(labels)
    setEditing(false)
  }

  const catalogOptions = catalog.map((e) => e.name).filter((n) => !current.includes(n))

  // DSGVO-Hinweis für Belegungs-Labels
  const showDsgvoHint = entityType === 'OCCUPANCY' && editing

  if (!editing) {
    return (
      <Box display="flex" alignItems="center" gap={0.5} flexWrap="wrap">
        {current.map((label) => {
          const color = getLabelColor(label, catalog)
          return (
            <Chip
              key={label}
              icon={<LocalOfferIcon sx={{ fontSize: '12px !important', color: `${color} !important` }} />}
              label={label}
              size="small"
              sx={{
                bgcolor: getLabelBg(color),
                color,
                height: compact ? 20 : 24,
                fontSize: compact ? 10 : 11,
                fontWeight: 600,
                '& .MuiChip-icon': { ml: 0.5 },
              }}
            />
          )
        })}
        {!readOnly && (
          <Tooltip title="Labels bearbeiten">
            <IconButton size="small" onClick={startEdit}
              sx={{ width: compact ? 20 : 24, height: compact ? 20 : 24, color: '#888' }}>
              <AddIcon sx={{ fontSize: compact ? 12 : 14 }} />
            </IconButton>
          </Tooltip>
        )}
        {current.length === 0 && readOnly && (
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            Keine Labels
          </Typography>
        )}
      </Box>
    )
  }

  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f8f9fa', borderRadius: 1.5, border: '1px solid #e0e0e0' }}>
      {showDsgvoHint && (
        <Typography variant="caption" color="text.secondary"
          sx={{ display: 'block', mb: 1, fontStyle: 'italic', fontSize: 10 }}>
          ⚠ Labels sind operative Hinweise — nicht AZR-relevant, nicht rechtlich bindend.
        </Typography>
      )}

      {/* Aktuelle Labels */}
      <Box display="flex" flexWrap="wrap" gap={0.5} mb={current.length > 0 ? 1.5 : 0}>
        {current.map((label) => {
          const color = getLabelColor(label, catalog)
          const catalogEntry = catalog.find((e) => e.name === label)
          const isSystemLabel = catalogEntry?.is_system === true
          const isLocked = lockedLabels.includes(label) || isSystemLabel
          const lockTitle = isSystemLabel
            ? 'Pflicht-Label — kann nicht entfernt werden'
            : (lockedTooltip ?? 'Label kann nicht entfernt werden')
          const chip = (
            <Chip
              key={label}
              label={label}
              size="small"
              icon={isLocked ? <LockIcon sx={{ fontSize: '12px !important', color: `${color} !important` }} /> : undefined}
              onDelete={isLocked ? undefined : () => removeLabel(label)}
              sx={{ bgcolor: getLabelBg(color), color, height: 24, fontWeight: 600, fontSize: 11, opacity: isLocked ? 0.75 : 1 }}
            />
          )
          return isLocked ? (
            <Tooltip key={label} title={lockTitle} arrow>
              <span>{chip}</span>
            </Tooltip>
          ) : chip
        })}
      </Box>

      {/* Autocomplete-Eingabe */}
      <Autocomplete
        freeSolo
        options={catalogOptions}
        groupBy={(option) => catalog.find((e) => e.name === option)?.category ?? 'Sonstige'}
        inputValue={inputVal}
        onInputChange={(_, v) => setInputVal(v)}
        onChange={(_, v) => { if (v) addLabel(v as string) }}
        renderInput={(params) => (
          <TextField
            {...params}
            size="small"
            placeholder="Label hinzufügen oder eingeben…"
            onKeyDown={(e) => { if (e.key === 'Enter' && inputVal.trim()) { addLabel(inputVal); e.preventDefault() } }}
            sx={{ bgcolor: 'white' }}
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {params.InputProps.endAdornment}
                  {inputVal.trim() && (
                    <Tooltip title="Hinzufügen">
                      <IconButton size="small" onClick={() => addLabel(inputVal)}>
                        <AddIcon sx={{ fontSize: 16 }} />
                      </IconButton>
                    </Tooltip>
                  )}
                </>
              ),
            }}
          />
        )}
        sx={{ mb: 1.5 }}
      />

      {/* Schnellauswahl aus Katalog */}
      {catalogOptions.length > 0 && (
        <Box mb={1.5}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
            Vorschläge:
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={0.5}>
            {catalogOptions.slice(0, 12).map((opt) => {
              const color = getLabelColor(opt, catalog)
              return (
                <Chip
                  key={opt}
                  label={opt}
                  size="small"
                  variant="outlined"
                  onClick={() => addLabel(opt)}
                  sx={{
                    borderColor: color + '80',
                    color,
                    height: 22,
                    fontSize: 10,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: getLabelBg(color) },
                  }}
                />
              )
            })}
          </Box>
        </Box>
      )}

      {/* Speichern / Abbrechen */}
      <Box display="flex" gap={1} alignItems="center">
        <Tooltip title="Speichern">
          <IconButton size="small" color="primary" onClick={save} disabled={saving}>
            {saving ? <CircularProgress size={16} /> : <CheckIcon sx={{ fontSize: 18 }} />}
          </IconButton>
        </Tooltip>
        <Tooltip title="Abbrechen">
          <IconButton size="small" onClick={cancel}>
            <CloseIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
        {saveError
          ? <Typography variant="caption" color="error" sx={{ ml: 0.5 }}>{saveError}</Typography>
          : <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5, lineHeight: '30px' }}>Enter oder Klick zum Hinzufügen</Typography>
        }
      </Box>
    </Paper>
  )
}

/** Minimale Anzeige für Tooltips / kompakte Ansichten */
export function LabelList({ labels, catalog = [] }: { labels: string[]; catalog?: LabelCatalogEntry[] }) {
  if (labels.length === 0) return null
  return (
    <Box display="flex" flexWrap="wrap" gap={0.4}>
      {labels.map((l) => {
        const color = getLabelColor(l, catalog)
        return (
          <Chip key={l} label={l} size="small"
            sx={{ bgcolor: getLabelBg(color), color, height: 18, fontSize: 9, fontWeight: 700 }} />
        )
      })}
    </Box>
  )
}

export { CATEGORY_COLORS }
