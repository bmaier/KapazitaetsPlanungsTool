import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import { Box, CircularProgress, CssBaseline } from '@mui/material'
import { KeycloakProvider, useKeycloak } from './auth/KeycloakProvider'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import Dashboard from './pages/Dashboard'
import Drilldown from './pages/Drilldown'
import Reservations from './pages/Reservations'
import SuggestionWizard from './pages/SuggestionWizard'
import TaskInbox from './pages/TaskInbox'
import AuditLog from './pages/AuditLog'
import Impressum from './pages/Impressum'
import Datenschutz from './pages/Datenschutz'
import Lizenzen from './pages/Lizenzen'
import { SseNotificationsProvider } from './hooks/SseNotificationsProvider'

const theme = createTheme({
  palette: {
    primary: { main: '#003366', dark: '#002147' },
    secondary: { main: '#5b7fa6' },
    background: { default: '#f0f2f5' },
    success: { main: '#2e7d32' },
    error: { main: '#c62828' },
    warning: { main: '#e65100' },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600 },
        contained: { boxShadow: 'none', '&:hover': { boxShadow: '0 2px 8px rgba(0,0,0,0.15)' } },
      },
    },
    MuiCard: { styleOverrides: { root: { borderRadius: 12 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
  },
})

function AppRoutes() {
  const { initialized } = useKeycloak()

  if (!initialized) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <BrowserRouter>
      <SseNotificationsProvider>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <NavBar />
          <Box sx={{ flex: 1 }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/locations/:id" element={<Drilldown />} />
              <Route path="/reservations" element={<Reservations />} />
              <Route path="/tasks" element={<TaskInbox />} />
              <Route path="/suggestions" element={<SuggestionWizard />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/impressum" element={<Impressum />} />
              <Route path="/datenschutz" element={<Datenschutz />} />
              <Route path="/lizenzen" element={<Lizenzen />} />
            </Routes>
          </Box>
          <Footer />
        </Box>
      </SseNotificationsProvider>
    </BrowserRouter>
  )
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <KeycloakProvider>
        <AppRoutes />
      </KeycloakProvider>
    </ThemeProvider>
  )
}
