import { Box, Link, Paper, Typography } from '@mui/material'
import SecurityIcon from '@mui/icons-material/Security'

export default function Datenschutz() {
  return (
    <Box sx={{ p: 3, maxWidth: 860, mx: 'auto' }}>
      <Box display="flex" alignItems="center" gap={1.5} mb={3}>
        <SecurityIcon sx={{ color: '#003366', fontSize: 28 }} />
        <Typography variant="h5" fontWeight={700} sx={{ color: '#003366' }}>
          Datenschutzerklärung
        </Typography>
      </Box>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>1. Verantwortliche Stelle</Typography>
        <Typography variant="body2">
          Bundesamt für Migration und Flüchtlinge (BAMF)<br />
          Frankenstraße 210, 90461 Nürnberg<br />
          E-Mail: <Link href="mailto:bamf@bamf.bund.de">bamf@bamf.bund.de</Link>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          2. Behördliche Datenschutzbeauftragte / Behördlicher Datenschutzbeauftragter
        </Typography>
        <Typography variant="body2">
          Bundesamt für Migration und Flüchtlinge<br />
          Behördliche Datenschutzbeauftragte/r<br />
          Frankenstraße 210, 90461 Nürnberg<br />
          E-Mail: <Link href="mailto:datenschutz@bamf.bund.de">datenschutz@bamf.bund.de</Link>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>3. Verarbeitete Daten</Typography>
        <Typography variant="body2" gutterBottom>
          Diese Anwendung verarbeitet folgende personenbezogene Daten:
        </Typography>
        <Typography variant="body2" component="div">
          <ul>
            <li>
              <strong>Nutzerdaten:</strong> Benutzername, E-Mail-Adresse, Vorname, Nachname,
              zugewiesene Rolle und Einrichtungszuordnung (gespeichert in Keycloak).
            </li>
            <li>
              <strong>Belegungsdaten:</strong> AZR-Identifikationsnummern (kein Klarname),
              Alias-IDs, Geschlecht, Geburtsjahr, Herkunftsland, Belegungszeitraum und
              Bett-/Raumzuordnung.
            </li>
            <li>
              <strong>Audit-Protokoll:</strong> Fachlich relevante Aktionen (Belegungen,
              Verlegungen) werden mit Zeitstempel, Nutzerkennung und Rolle protokolliert.
            </li>
            <li>
              <strong>Technische Verbindungsdaten:</strong> Server-Logs enthalten IP-Adresse,
              Zeitstempel und HTTP-Anfragepfade (keine dauerhafte Speicherung über 30 Tage).
            </li>
          </ul>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>4. Rechtsgrundlagen</Typography>
        <Typography variant="body2" component="div">
          <ul>
            <li>
              <strong>Art. 6 Abs. 1 lit. e DSGVO</strong> in Verbindung mit den Vorschriften
              des Aufenthaltsgesetzes (AufenthG) und des Asylgesetzes (AsylG): Verarbeitung
              zur Wahrnehmung einer Aufgabe im öffentlichen Interesse.
            </li>
            <li>
              <strong>Art. 6 Abs. 1 lit. b DSGVO:</strong> Verarbeitung zur Erfüllung eines
              Vertrags (Nutzerkonto für Mitarbeitende).
            </li>
            <li>
              <strong>Art. 6 Abs. 1 lit. c DSGVO:</strong> Verarbeitung zur Erfüllung einer
              rechtlichen Verpflichtung (Audit-Log nach § 67 BDSG, DSGVO Art. 5 Abs. 2).
            </li>
          </ul>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          5. Keine Weitergabe an Dritte / Auftragsverarbeitung
        </Typography>
        <Typography variant="body2">
          Personenbezogene Daten werden nicht an Dritte weitergegeben, soweit keine gesetzliche
          Pflicht dazu besteht. Die technische Infrastruktur wird ausschließlich auf Servern
          innerhalb der Bundesrepublik Deutschland betrieben. Soweit Auftragsverarbeiter
          eingesetzt werden, sind diese nach Art. 28 DSGVO vertraglich gebunden.
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          6. Speicherdauer und Löschfristen
        </Typography>
        <Typography variant="body2" component="div">
          <ul>
            <li><strong>Nutzerdaten (Keycloak):</strong> Solange das Dienstverhältnis besteht; Löschung nach Ausscheiden.</li>
            <li><strong>Belegungsdaten:</strong> Entsprechend den gesetzlichen Aufbewahrungsfristen nach AufenthG / AsylG.</li>
            <li><strong>Audit-Log:</strong> 10 Jahre (Mindestaufbewahrungsfrist für Behördenakten gemäß GGO); danach Löschung möglich über Admin-Funktion.</li>
            <li><strong>Server-Logs:</strong> 30 Tage, dann automatische Löschung.</li>
          </ul>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>7. Ihre Rechte</Typography>
        <Typography variant="body2" gutterBottom>
          Als betroffene Person haben Sie folgende Rechte gegenüber dem BAMF:
        </Typography>
        <Typography variant="body2" component="div">
          <ul>
            <li><strong>Auskunft</strong> (Art. 15 DSGVO)</li>
            <li><strong>Berichtigung</strong> (Art. 16 DSGVO)</li>
            <li><strong>Löschung</strong> (Art. 17 DSGVO) — soweit keine gesetzliche Aufbewahrungspflicht entgegensteht</li>
            <li><strong>Einschränkung der Verarbeitung</strong> (Art. 18 DSGVO)</li>
            <li><strong>Datenübertragbarkeit</strong> (Art. 20 DSGVO)</li>
            <li><strong>Widerspruch</strong> (Art. 21 DSGVO)</li>
          </ul>
        </Typography>
        <Typography variant="body2">
          Anfragen richten Sie bitte an:{' '}
          <Link href="mailto:datenschutz@bamf.bund.de">datenschutz@bamf.bund.de</Link>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          8. Beschwerderecht bei der Aufsichtsbehörde
        </Typography>
        <Typography variant="body2">
          Sie haben das Recht, sich bei der zuständigen Datenschutzaufsichtsbehörde zu beschweren.
          Zuständig ist der Bundesbeauftragte für den Datenschutz und die Informationsfreiheit (BfDI):
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Graurheindorfer Str. 153, 53117 Bonn<br />
          <Link href="https://www.bfdi.bund.de" target="_blank" rel="noopener noreferrer">
            www.bfdi.bund.de
          </Link>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>9. Cookies und Sitzungsdaten</Typography>
        <Typography variant="body2">
          Diese Anwendung verwendet ausschließlich technisch notwendige Sitzungscookies (Session-Tokens)
          zur Authentifizierung über Keycloak. Es werden keine Tracking-Cookies oder
          Analyse-Cookies eingesetzt. Eine Einwilligung nach § 25 TDDDG ist für rein
          technisch notwendige Cookies nicht erforderlich.
        </Typography>
      </Paper>
    </Box>
  )
}
