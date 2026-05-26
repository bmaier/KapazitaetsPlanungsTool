import { useState } from 'react'
import {
  AppBar, Badge, Box, Button, Chip, CircularProgress, Dialog, DialogContent,
  DialogTitle, Divider, IconButton, InputAdornment, Paper, TextField, Toolbar,
  Tooltip, Typography,
} from '@mui/material'
import InboxIcon from '@mui/icons-material/Inbox'
import DashboardIcon from '@mui/icons-material/Dashboard'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import SearchIcon from '@mui/icons-material/Search'
import LogoutIcon from '@mui/icons-material/Logout'
import BedIcon from '@mui/icons-material/Hotel'
import { useLocation, useNavigate } from 'react-router-dom'
import { useKeycloak } from '../auth/KeycloakProvider'
import { useSseNotifications } from '../hooks/useSseNotifications'
import { useApiClient } from '../api/client'

const NAV_LINKS = [
  { label: 'Dashboard', path: '/', Icon: DashboardIcon },
  { label: 'Reservierungen', path: '/reservations', Icon: SwapHorizIcon },
  { label: 'Reservierungsanfrage', path: '/suggestions', Icon: SearchIcon },
]

interface OccupantResult {
  occupancy_id: string
  azr_id: string
  alias_id?: string
  geschlecht: string
  belegung_start: string
  belegung_ende: string
  bed_id: string
  bett_nummer: string
  bett_typ: string
  room_id: string
  room_name: string
  geschlechts_designation: string
  location_id: string
  location_name: string
}

const ROLE_LABELS: Record<string, string> = {
  'system-admin': 'System-Admin',
  'location-admin': 'Standort-Admin',
  'writer': 'Schreiber',
  'reader': 'Leser',
}

function getRoleLabel(roles: string[]): string {
  for (const key of ['system-admin', 'location-admin', 'writer', 'reader']) {
    if (roles.includes(key)) return ROLE_LABELS[key]
  }
  return roles[0] ?? 'Nutzer'
}

export default function NavBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { keycloak, locationId } = useKeycloak()
  const { count } = useSseNotifications()
  const { get } = useApiClient()
  const tokenParsed = keycloak?.tokenParsed as Record<string, unknown> | undefined
  const username = tokenParsed?.preferred_username as string | undefined
  const roles = ((tokenParsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [])
  const roleLabel = getRoleLabel(roles)

  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState<OccupantResult[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function handleSearch() {
    if (!searchQ.trim()) return
    setSearchLoading(true)
    setSearched(false)
    try {
      const results = await get<OccupantResult[]>(`/api/occupants/search?q=${encodeURIComponent(searchQ.trim())}`)
      setSearchResults(results)
    } catch {
      setSearchResults([])
    } finally {
      setSearchLoading(false)
      setSearched(true)
    }
  }

  function openLocation(locationId: string, bedId?: string) {
    setSearchOpen(false)
    setSearchQ('')
    setSearchResults([])
    setSearched(false)
    const url = bedId ? `/locations/${locationId}?highlight_bed=${bedId}` : `/locations/${locationId}`
    navigate(url)
  }

  const gLabel = (g: string) => g === 'M' ? 'Männer' : g === 'W' ? 'Frauen' : 'Divers'
  const gColor = (g: string) => g === 'M' ? '#1565c0' : g === 'W' ? '#880e4f' : '#4a148c'

  return (
    <>
      <AppBar position="sticky" elevation={0} sx={{ bgcolor: '#002147', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <Toolbar sx={{ gap: 0.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 3, cursor: 'pointer' }}
            onClick={() => navigate('/')}>
            <Box sx={{ width: 32, height: 32, borderRadius: 1, bgcolor: '#ffd700', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography sx={{ fontWeight: 900, color: '#002147', fontSize: 16, lineHeight: 1 }}>B</Typography>
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: '-0.5px', display: { xs: 'none', sm: 'block' } }}>
              BorderCapControl
            </Typography>
          </Box>

          {NAV_LINKS.map((link) => {
            const active = location.pathname === link.path
            return (
              <Button key={link.path} color="inherit" onClick={() => navigate(link.path)}
                startIcon={<link.Icon sx={{ fontSize: 18 }} />}
                sx={{
                  fontWeight: active ? 700 : 400,
                  bgcolor: active ? 'rgba(255,255,255,0.12)' : 'transparent',
                  borderRadius: 1.5, px: 1.5,
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.08)' }, fontSize: 13,
                }}>
                {link.label}
              </Button>
            )
          })}

          <Box sx={{ flexGrow: 1 }} />

          {/* AZR-Suche */}
          <Tooltip title="Person nach AZR-ID oder Alias suchen">
            <IconButton color="inherit" onClick={() => setSearchOpen(true)} sx={{ borderRadius: 1.5 }}>
              <SearchIcon />
            </IconButton>
          </Tooltip>

          {/* Postkorb */}
          <Tooltip title="Postkorb">
            <IconButton color="inherit" onClick={() => navigate('/tasks')}
              sx={{ bgcolor: location.pathname === '/tasks' ? 'rgba(255,255,255,0.12)' : 'transparent', borderRadius: 1.5 }}>
              <Badge badgeContent={count} color="error" aria-label={`${count} neue Aufgaben`}>
                <InboxIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {username && (
            <Tooltip title={`${username} · ${roleLabel}${locationId ? ` · Standort ${locationId.slice(0, 8)}…` : ''}`}
              arrow>
              <Box sx={{ display: { xs: 'none', md: 'flex' }, flexDirection: 'column', alignItems: 'flex-end', mx: 1.5, cursor: 'default' }}>
                <Typography variant="caption" sx={{ opacity: 0.9, fontWeight: 600, lineHeight: 1.2 }}>
                  {username}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.55, fontSize: 10, lineHeight: 1.2 }}>
                  {roleLabel}{locationId ? ` · ${locationId.slice(0, 8)}…` : ''}
                </Typography>
              </Box>
            </Tooltip>
          )}

          <Tooltip title="Abmelden">
            <IconButton color="inherit" onClick={() => keycloak?.logout()} aria-label="Abmelden" size="small">
              <LogoutIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* AZR-Suchdialog */}
      <Dialog open={searchOpen} onClose={() => { setSearchOpen(false); setSearchQ(''); setSearchResults([]); setSearched(false) }}
        maxWidth="sm" fullWidth>
        <DialogTitle fontWeight={700}>
          <Box display="flex" alignItems="center" gap={1}>
            <SearchIcon sx={{ color: '#003366' }} />
            Person suchen (AZR-ID / Alias)
          </Box>
        </DialogTitle>
        <DialogContent sx={{ pb: 3 }}>
          <Box display="flex" gap={1} mb={2} mt={0.5}>
            <TextField
              fullWidth
              size="small"
              placeholder="z.B. AZR-2024-0001-M01 oder AL-M-001"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              InputProps={{
                startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 18, color: '#888' }} /></InputAdornment>,
              }}
            />
            <Button variant="contained" onClick={handleSearch} disabled={!searchQ.trim() || searchLoading}>
              {searchLoading ? <CircularProgress size={18} /> : 'Suchen'}
            </Button>
          </Box>

          {searchLoading && <Box display="flex" justifyContent="center" py={3}><CircularProgress /></Box>}

          {searched && !searchLoading && searchResults.length === 0 && (
            <Typography color="text.secondary" textAlign="center" py={2}>
              Keine aktiven Belegungen für „{searchQ}" gefunden.
            </Typography>
          )}

          {searchResults.length > 0 && (
            <Box display="flex" flexDirection="column" gap={1.5}>
              {searchResults.map((r) => (
                <Paper key={r.occupancy_id} elevation={1} sx={{ p: 2, borderRadius: 2, cursor: 'pointer', '&:hover': { bgcolor: '#f5f8ff' }, borderLeft: `4px solid ${gColor(r.geschlecht)}` }}
                  onClick={() => openLocation(r.location_id, r.bed_id)}>
                  <Box display="flex" alignItems="center" gap={1} mb={0.5} flexWrap="wrap">
                    <BedIcon sx={{ fontSize: 18, color: '#003366' }} />
                    <Typography fontWeight={700} fontFamily="monospace">{r.azr_id}</Typography>
                    {r.alias_id && <Typography variant="caption" color="text.secondary">· {r.alias_id}</Typography>}
                    <Chip label={gLabel(r.geschlecht)} size="small"
                      sx={{ bgcolor: gColor(r.geschlecht) + '15', color: gColor(r.geschlecht), height: 20 }} />
                  </Box>
                  <Divider sx={{ my: 0.5 }} />
                  <Box display="flex" gap={2} flexWrap="wrap">
                    <Box>
                      <Typography variant="caption" color="text.secondary">Einrichtung</Typography>
                      <Typography variant="body2" fontWeight={600}>{r.location_name}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Raum / Bett</Typography>
                      <Typography variant="body2" fontWeight={600}>{r.room_name} · Bett {r.bett_nummer}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Zeitraum</Typography>
                      <Typography variant="body2" fontWeight={600}>{r.belegung_start} – {r.belegung_ende}</Typography>
                    </Box>
                  </Box>
                  <Typography variant="caption" sx={{ color: '#003366', mt: 0.5, display: 'block' }}>
                    → Klicken zum Öffnen der Einrichtung
                  </Typography>
                </Paper>
              ))}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
