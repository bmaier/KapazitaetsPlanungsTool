import { Box, Chip, Divider, Link, Paper, Typography } from '@mui/material'
import BalanceIcon from '@mui/icons-material/Balance'

interface LibEntry {
  name: string
  version: string
  license: string
  url: string
  note?: string
}

const FRONTEND_LIBS: LibEntry[] = [
  { name: 'React', version: '18.x', license: 'MIT', url: 'https://github.com/facebook/react' },
  { name: 'React DOM', version: '18.x', license: 'MIT', url: 'https://github.com/facebook/react' },
  { name: 'React Router', version: '6.x', license: 'MIT', url: 'https://github.com/remix-run/react-router' },
  { name: 'MUI (Material-UI)', version: '5.x', license: 'MIT', url: 'https://github.com/mui/material-ui' },
  { name: '@emotion/react', version: '11.x', license: 'MIT', url: 'https://github.com/emotion-js/emotion' },
  { name: '@emotion/styled', version: '11.x', license: 'MIT', url: 'https://github.com/emotion-js/emotion' },
  { name: 'MUI Icons Material', version: '5.x', license: 'MIT', url: 'https://github.com/mui/material-ui' },
  { name: 'Vite', version: '5.x', license: 'MIT', url: 'https://github.com/vitejs/vite' },
  { name: 'TypeScript', version: '5.x', license: 'Apache-2.0', url: 'https://github.com/microsoft/TypeScript' },
  { name: 'keycloak-js', version: '24.x', license: 'Apache-2.0', url: 'https://github.com/keycloak/keycloak' },
  { name: 'Leaflet', version: '1.x', license: 'BSD-2-Clause', url: 'https://github.com/Leaflet/Leaflet' },
  { name: 'React Leaflet', version: '4.x', license: 'Hippocratic-2.1', url: 'https://github.com/PaulLeCam/react-leaflet' },
  { name: 'react-markdown', version: '10.x', license: 'MIT', url: 'https://github.com/remarkjs/react-markdown' },
  { name: 'remark-gfm', version: '4.x', license: 'MIT', url: 'https://github.com/remarkjs/remark-gfm' },
  { name: '@microsoft/fetch-event-source', version: '2.x', license: 'MIT', url: 'https://github.com/Azure/fetch-event-source' },
]

const BACKEND_LIBS: LibEntry[] = [
  { name: 'Python', version: '3.11', license: 'PSF-2.0', url: 'https://www.python.org' },
  { name: 'FastAPI', version: '0.111.x', license: 'MIT', url: 'https://github.com/tiangolo/fastapi' },
  { name: 'SQLAlchemy', version: '2.x', license: 'MIT', url: 'https://github.com/sqlalchemy/sqlalchemy' },
  { name: 'asyncpg', version: '0.29.x', license: 'Apache-2.0', url: 'https://github.com/MagicStack/asyncpg' },
  { name: 'Alembic', version: '1.13.x', license: 'MIT', url: 'https://github.com/sqlalchemy/alembic' },
  { name: 'Pydantic', version: '2.x', license: 'MIT', url: 'https://github.com/pydantic/pydantic' },
  { name: 'pydantic-settings', version: '2.x', license: 'MIT', url: 'https://github.com/pydantic/pydantic-settings' },
  { name: 'Uvicorn', version: '0.29.x', license: 'BSD-3-Clause', url: 'https://github.com/encode/uvicorn' },
  { name: 'python-jose', version: '3.x', license: 'MIT', url: 'https://github.com/mpdavis/python-jose' },
  { name: 'httpx', version: '0.27.x', license: 'BSD-3-Clause', url: 'https://github.com/encode/httpx' },
  { name: 'APScheduler', version: '3.x', license: 'MIT', url: 'https://github.com/agronholm/apscheduler' },
  { name: 'WeasyPrint', version: '62.x', license: 'BSD-3-Clause', url: 'https://github.com/Kozea/WeasyPrint' },
]

const INFRA_LIBS: LibEntry[] = [
  { name: 'PostgreSQL', version: '16', license: 'PostgreSQL License', url: 'https://www.postgresql.org' },
  { name: 'Keycloak', version: '24', license: 'Apache-2.0', url: 'https://github.com/keycloak/keycloak' },
  { name: 'Nginx', version: '1.27', license: 'BSD-2-Clause', url: 'https://nginx.org' },
  { name: 'Docker / Podman', version: '—', license: 'Apache-2.0', url: 'https://www.docker.com' },
  { name: 'Mailpit (Dev)', version: 'latest', license: 'MIT', url: 'https://github.com/axllent/mailpit' },
]

const MAP_LIBS: LibEntry[] = [
  {
    name: 'OpenStreetMap',
    version: '—',
    license: 'ODbL 1.0',
    url: 'https://www.openstreetmap.org/copyright',
    note: '© OpenStreetMap contributors. Kartendaten stehen unter der Open Database Licence (ODbL).',
  },
  {
    name: 'Tileserver GL',
    version: 'latest',
    license: 'BSD-2-Clause',
    url: 'https://github.com/maptiler/tileserver-gl',
  },
]

const LICENSE_COLORS: Record<string, string> = {
  'MIT': '#2e7d32',
  'Apache-2.0': '#1565c0',
  'BSD-2-Clause': '#6a1b9a',
  'BSD-3-Clause': '#6a1b9a',
  'PSF-2.0': '#e65100',
  'PostgreSQL License': '#01579b',
  'ODbL 1.0': '#b71c1c',
  'Hippocratic-2.1': '#00695c',
}

function LicChip({ license }: { license: string }) {
  const color = LICENSE_COLORS[license] ?? '#555'
  return (
    <Chip label={license} size="small"
      sx={{ bgcolor: color + '18', color, fontWeight: 700, height: 20, fontSize: 10 }} />
  )
}

function LibTable({ libs }: { libs: LibEntry[] }) {
  return (
    <Box>
      {libs.map((lib, i) => (
        <Box key={lib.name}>
          {i > 0 && <Divider />}
          <Box display="flex" alignItems="flex-start" gap={2} py={1.5} flexWrap="wrap">
            <Box flex={1} minWidth={200}>
              <Link href={lib.url} target="_blank" rel="noopener noreferrer"
                fontWeight={700} color="#003366" underline="hover">
                {lib.name}
              </Link>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                {lib.version}
              </Typography>
              {lib.note && (
                <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.3 }}>
                  {lib.note}
                </Typography>
              )}
            </Box>
            <LicChip license={lib.license} />
          </Box>
        </Box>
      ))}
    </Box>
  )
}

export default function Lizenzen() {
  return (
    <Box sx={{ p: 3, maxWidth: 860, mx: 'auto' }}>
      <Box display="flex" alignItems="center" gap={1.5} mb={3}>
        <BalanceIcon sx={{ color: '#003366', fontSize: 28 }} />
        <Box>
          <Typography variant="h5" fontWeight={700} sx={{ color: '#003366' }}>
            Open-Source-Lizenzen
          </Typography>
          <Typography variant="body2" color="text.secondary">
            BAMF BorderCapControl verwendet die folgenden Open-Source-Komponenten.
          </Typography>
        </Box>
      </Box>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Hinweis</Typography>
        <Typography variant="body2">
          Diese Anwendung basiert auf quelloffener Software. Gemäß den jeweiligen Lizenzen
          werden alle verwendeten Bibliotheken hier aufgeführt. Die vollständigen Lizenztexte
          sind über die angegebenen Links abrufbar. Alle Rechte an den verwendeten Bibliotheken
          verbleiben bei den jeweiligen Rechteinhabern.
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Frontend (Browser)</Typography>
        <LibTable libs={FRONTEND_LIBS} />
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Backend (Server)</Typography>
        <LibTable libs={BACKEND_LIBS} />
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Infrastruktur</Typography>
        <LibTable libs={INFRA_LIBS} />
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2, border: '1px solid #e57373' }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Kartenmaterial — OpenStreetMap
        </Typography>
        <LibTable libs={MAP_LIBS} />
        <Box sx={{ mt: 2, p: 2, bgcolor: '#fff3e0', borderRadius: 1.5 }}>
          <Typography variant="body2" fontWeight={700} gutterBottom>
            Pflichtnennung gemäß ODbL 1.0:
          </Typography>
          <Typography variant="body2">
            Kartendaten © <Link href="https://www.openstreetmap.org/copyright"
              target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</Link>,
            lizenziert unter der{' '}
            <Link href="https://opendatacommons.org/licenses/odbl/" target="_blank" rel="noopener noreferrer">
              Open Database Licence (ODbL)
            </Link>.
            Kartendarstellung © <Link href="https://www.openstreetmap.org" target="_blank" rel="noopener noreferrer">
              OpenStreetMap
            </Link> und Mitwirkende,{' '}
            <Link href="https://creativecommons.org/licenses/by-sa/2.0/" target="_blank" rel="noopener noreferrer">
              CC BY-SA 2.0
            </Link>.
          </Typography>
        </Box>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Lizenzübersicht (Kurzform)
        </Typography>
        <Box display="flex" gap={1} flexWrap="wrap">
          {Object.entries(LICENSE_COLORS).map(([lic]) => (
            <LicChip key={lic} license={lic} />
          ))}
        </Box>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
          MIT / Apache-2.0 / BSD: Permissive Lizenzen — freie Nutzung, Pflicht zur Nennung.
          ODbL: Open Database License — Kartendaten frei nutzbar, Änderungen müssen unter ODbL
          veröffentlicht werden.
        </Typography>
      </Paper>
    </Box>
  )
}
