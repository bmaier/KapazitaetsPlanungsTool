import { Box, Divider, Link, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'

export default function Footer() {
  const navigate = useNavigate()

  return (
    <Box
      component="footer"
      sx={{
        mt: 'auto',
        borderTop: '1px solid #e0e0e0',
        bgcolor: '#f5f7fa',
        py: 2,
        px: 3,
      }}
    >
      <Box
        display="flex"
        flexDirection={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        gap={1}
        flexWrap="wrap"
      >
        {/* Legal links */}
        <Box display="flex" gap={0.5} alignItems="center" flexWrap="wrap">
          <Link
            component="button"
            variant="caption"
            color="text.secondary"
            underline="hover"
            onClick={() => navigate('/impressum')}
            sx={{ cursor: 'pointer', background: 'none', border: 'none', p: 0 }}
          >
            Impressum
          </Link>
          <Typography variant="caption" color="text.disabled">·</Typography>
          <Link
            component="button"
            variant="caption"
            color="text.secondary"
            underline="hover"
            onClick={() => navigate('/datenschutz')}
            sx={{ cursor: 'pointer', background: 'none', border: 'none', p: 0 }}
          >
            Datenschutz
          </Link>
          <Typography variant="caption" color="text.disabled">·</Typography>
          <Link
            component="button"
            variant="caption"
            color="text.secondary"
            underline="hover"
            onClick={() => navigate('/lizenzen')}
            sx={{ cursor: 'pointer', background: 'none', border: 'none', p: 0 }}
          >
            Open-Source-Lizenzen
          </Link>
        </Box>

        <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', sm: 'block' }, mx: 1 }} />

        {/* OSM attribution — required by ODbL */}
        <Typography variant="caption" color="text.secondary">
          Kartendaten ©{' '}
          <Link
            href="https://www.openstreetmap.org/copyright"
            target="_blank"
            rel="noopener noreferrer"
            variant="caption"
            underline="hover"
          >
            OpenStreetMap contributors
          </Link>
          , ODbL
        </Typography>

        <Box flexGrow={1} />

        <Typography variant="caption" color="text.disabled">
          © {new Date().getFullYear()} Bundesamt für Migration und Flüchtlinge (BAMF)
        </Typography>
      </Box>
    </Box>
  )
}
