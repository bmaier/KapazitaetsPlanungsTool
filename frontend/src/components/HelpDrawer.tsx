import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Box,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  Link,
  Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const ROUTE_HELP: Record<string, string> = {
  '/':             '/help/dashboard.md',
  '/reservations': '/help/reservations.md',
  '/tasks':        '/help/tasks.md',
  '/suggestions':  '/help/suggestions.md',
}

function routeToFile(pathname: string): string {
  if (pathname.startsWith('/locations/')) return '/help/drilldown.md'
  return ROUTE_HELP[pathname] ?? '/help/dashboard.md'
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function HelpDrawer({ open, onClose }: Props) {
  const location = useLocation()
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [showHandbuch, setShowHandbuch] = useState(false)

  const file = showHandbuch ? '/help/handbuch.md' : routeToFile(location.pathname)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetch(file)
      .then((r) => (r.ok ? r.text() : Promise.reject()))
      .then(setContent)
      .catch(() => setContent('_Hilfe-Inhalt nicht verfügbar._'))
      .finally(() => setLoading(false))
  }, [open, file])

  function handleClose() {
    setShowHandbuch(false)
    onClose()
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={handleClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 400 }, display: 'flex', flexDirection: 'column' } }}
    >
      {/* Header */}
      <Box sx={{ px: 2.5, py: 2, bgcolor: '#003366', color: 'white', display: 'flex', alignItems: 'center', gap: 1 }}>
        <MenuBookIcon sx={{ fontSize: 22 }} />
        <Typography fontWeight={700} sx={{ flex: 1 }}>
          {showHandbuch ? 'Benutzerhandbuch' : 'Hilfe'}
        </Typography>
        <IconButton onClick={handleClose} sx={{ color: 'white', p: 0.5 }} aria-label="Hilfe schließen">
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', px: 2.5, py: 2 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" pt={6}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{
            '& h1': { fontSize: '1.25rem', fontWeight: 700, color: '#003366', mt: 2.5, mb: 1, borderBottom: '2px solid #e0e0e0', pb: 0.5 },
            '& h2': { fontSize: '1.05rem', fontWeight: 700, color: '#003366', mt: 2, mb: 0.75 },
            '& h3': { fontSize: '0.95rem', fontWeight: 600, color: '#1a3a5c', mt: 1.5, mb: 0.5 },
            '& p': { fontSize: '0.875rem', lineHeight: 1.65, mb: 1, color: '#212121' },
            '& ul, & ol': { pl: 2.5, mb: 1 },
            '& li': { fontSize: '0.875rem', lineHeight: 1.65, mb: 0.25 },
            '& code': { bgcolor: '#f5f5f5', px: 0.5, py: 0.1, borderRadius: 0.5, fontSize: '0.8rem', fontFamily: 'monospace' },
            '& pre': { bgcolor: '#f5f5f5', p: 1.5, borderRadius: 1, overflow: 'auto', mb: 1 },
            '& pre code': { bgcolor: 'transparent', p: 0 },
            '& blockquote': { borderLeft: '3px solid #003366', pl: 1.5, my: 1, color: '#555', fontStyle: 'italic' },
            '& strong': { fontWeight: 700 },
            '& hr': { border: 'none', borderTop: '1px solid #e0e0e0', my: 2 },
            '& table': { width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', mb: 1.5 },
            '& th': { bgcolor: '#f5f7ff', fontWeight: 700, p: 0.75, border: '1px solid #e0e0e0', textAlign: 'left' },
            '& td': { p: 0.75, border: '1px solid #e0e0e0' },
          }}>
            <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
          </Box>
        )}
      </Box>

      {/* Footer */}
      {!showHandbuch && (
        <>
          <Divider />
          <Box sx={{ px: 2.5, py: 1.5, bgcolor: '#f8f9fa' }}>
            <Link
              component="button"
              onClick={() => setShowHandbuch(true)}
              sx={{ fontSize: '0.8rem', color: '#003366', display: 'flex', alignItems: 'center', gap: 0.5 }}
            >
              <MenuBookIcon sx={{ fontSize: 16 }} />
              Vollständiges Benutzerhandbuch öffnen
            </Link>
          </Box>
        </>
      )}
    </Drawer>
  )
}
