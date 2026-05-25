import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet'
import {
  Box,
  Button,
  Chip,
  Divider,
  LinearProgress,
  Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import WarningIcon from '@mui/icons-material/Warning'
import ErrorIcon from '@mui/icons-material/Error'

export interface LocationSummary {
  id: string
  name: string
  kontingent: number
  belegungsgrad_pct: number
  is_active: boolean
  belegt?: number
  notbett_kapazitaet?: number
}

interface MapViewProps {
  locations: LocationSummary[]
  visible?: boolean
}

const LOCATION_COORDS: Record<string, [number, number]> = {
  Frankfurt: [50.037, 8.562],
  München:   [48.354, 11.786],
  Passau:    [48.566, 13.467],
  Hamburg:   [53.630, 10.006],
}

function getCoords(name: string): [number, number] {
  const key = Object.keys(LOCATION_COORDS).find((k) => name.includes(k))
  return key ? LOCATION_COORDS[key] : [51.1, 10.4]
}

interface AmpelCfg {
  color: string; bg: string; border: string; label: string; Icon: typeof CheckCircleIcon
}

function ampelCfg(pct: number): AmpelCfg {
  if (pct >= 90) return { color: '#b71c1c', bg: '#ffebee', border: '#ef9a9a', label: 'Kritisch', Icon: ErrorIcon }
  if (pct >= 70) return { color: '#e65100', bg: '#fff3e0', border: '#ffcc80', label: 'Begrenzt', Icon: WarningIcon }
  return { color: '#1b5e20', bg: '#e8f5e9', border: '#a5d6a7', label: 'Verfügbar', Icon: CheckCircleIcon }
}

function markerColor(pct: number): string {
  if (pct >= 90) return '#d32f2f'
  if (pct >= 70) return '#f57c00'
  return '#388e3c'
}

function createDivIcon(name: string, pct: number): L.DivIcon {
  const shortName = name.replace('Flughafen ', '').replace('Grenzübergang ', 'GÜ ')
  const color = markerColor(pct)
  const html = `<div style="background:${color};border:3px solid white;border-radius:50%;width:56px;height:56px;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 3px 12px rgba(0,0,0,0.35);cursor:pointer;color:white;font-family:Roboto,sans-serif;text-align:center;line-height:1.1">
    <span style="font-size:10px;font-weight:700;padding:0 2px">${shortName}</span>
    <span style="font-size:14px;font-weight:900">${Math.round(pct)}%</span>
  </div>`
  return L.divIcon({ html, className: '', iconSize: [56, 56], iconAnchor: [28, 28], popupAnchor: [0, -32] })
}

// Beim Sichtbarwerden Größe invalidieren und Bounds setzen
function MapController({ locations, visible }: { locations: LocationSummary[]; visible: boolean }) {
  const map = useMap()
  const fitted = useRef(false)
  const prevVisible = useRef(false)

  useEffect(() => {
    if (!visible) { prevVisible.current = false; return }
    const justBecameVisible = !prevVisible.current
    prevVisible.current = true

    const t = setTimeout(() => {
      map.invalidateSize()
      if (justBecameVisible || !fitted.current) {
        const points = locations.filter((l) => l.is_active).map((l) => getCoords(l.name))
        if (points.length > 0) {
          map.fitBounds(points as L.LatLngBoundsExpression, { padding: [60, 60], maxZoom: 9 })
          fitted.current = true
        }
      }
    }, 100)
    return () => clearTimeout(t)
  }, [visible, locations, map])

  useMapEvents({ zoomend: () => map.invalidateSize() })
  return null
}

export default function MapView({ locations, visible = true }: MapViewProps) {
  const navigate = useNavigate()
  const active = locations.filter((l) => l.is_active)

  return (
    <Box sx={{ position: 'relative', height: '75vh', width: '100%', borderRadius: 2, overflow: 'hidden', boxShadow: 2 }}>
      <MapContainer
        center={[51.1, 10.4]}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
        attributionControl={true}
      >
        {/* OpenStreetMap als zuverlässige Kartengrundlage bei allen Zoomstufen */}
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>'
          maxZoom={19}
          minZoom={2}
        />

        <MapController locations={active} visible={visible} />

        {active.map((loc) => {
          const coords = getCoords(loc.name)
          const cfg = ampelCfg(loc.belegungsgrad_pct)
          const belegt = loc.belegt ?? Math.round((loc.belegungsgrad_pct / 100) * loc.kontingent)
          const AmpelIcon = cfg.Icon

          return (
            <Marker key={loc.id} position={coords} icon={createDivIcon(loc.name, loc.belegungsgrad_pct)}>
              <Popup minWidth={230} closeButton>
                <Box sx={{ pb: 0.5 }}>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#003366', lineHeight: 1.3, mb: 0.5 }}>
                    {loc.name}
                  </Typography>
                  <Chip
                    icon={<AmpelIcon sx={{ fontSize: '14px !important' }} />}
                    label={cfg.label}
                    size="small"
                    sx={{ bgcolor: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`, fontWeight: 600, fontSize: 11, height: 22 }}
                  />
                </Box>

                <Divider sx={{ my: 1 }} />

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.4, mb: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">Kontingent</Typography>
                    <Typography variant="caption" fontWeight={600}>{loc.kontingent} Plätze</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">Belegt</Typography>
                    <Typography variant="caption" fontWeight={600}>{belegt} Plätze</Typography>
                  </Box>
                  {loc.notbett_kapazitaet !== undefined && (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">Notbetten</Typography>
                      <Typography variant="caption" fontWeight={600}>{loc.notbett_kapazitaet}</Typography>
                    </Box>
                  )}
                </Box>

                <Box sx={{ mb: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                    <Typography variant="caption" color="text.secondary">Auslastung</Typography>
                    <Typography variant="caption" fontWeight={700} sx={{ color: cfg.color }}>
                      {loc.belegungsgrad_pct.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(loc.belegungsgrad_pct, 100)}
                    sx={{ height: 6, borderRadius: 3, bgcolor: cfg.border + '55', '& .MuiLinearProgress-bar': { bgcolor: cfg.color, borderRadius: 3 } }}
                  />
                </Box>

                <Button
                  variant="contained" size="small" fullWidth
                  onClick={() => navigate(`/locations/${loc.id}`)}
                  sx={{ bgcolor: '#003366', fontSize: 12, py: 0.6, '&:hover': { bgcolor: '#1a5276' } }}
                >
                  Details & Betten öffnen →
                </Button>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>

      <Box sx={{ position: 'absolute', bottom: 24, right: 16, zIndex: 1000, bgcolor: 'rgba(255,255,255,0.95)', borderRadius: 2, p: 1.5, boxShadow: 2, minWidth: 130 }}>
        <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>Ampelstatus</Typography>
        {([
          { color: '#388e3c', label: '< 70 % — Grün' },
          { color: '#f57c00', label: '70–90 % — Gelb' },
          { color: '#d32f2f', label: '> 90 % — Rot' },
        ] as const).map(({ color, label }) => (
          <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.8, mb: 0.3 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: color, flexShrink: 0 }} />
            <Typography variant="caption" color="text.secondary">{label}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
