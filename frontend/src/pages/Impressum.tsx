import { Box, Divider, Link, Paper, Typography } from '@mui/material'
import GavelIcon from '@mui/icons-material/Gavel'

export default function Impressum() {
  return (
    <Box sx={{ p: 3, maxWidth: 860, mx: 'auto' }}>
      <Box display="flex" alignItems="center" gap={1.5} mb={3}>
        <GavelIcon sx={{ color: '#003366', fontSize: 28 }} />
        <Typography variant="h5" fontWeight={700} sx={{ color: '#003366' }}>
          Impressum
        </Typography>
      </Box>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Anbieter</Typography>
        <Typography variant="body1" gutterBottom>
          Bundesamt für Migration und Flüchtlinge (BAMF)
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Frankenstraße 210<br />
          90461 Nürnberg<br />
          Deutschland
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="body2" gutterBottom>
          <strong>Telefon:</strong>{' '}
          <Link href="tel:+4991194300">+49 (0)911 943-0</Link>
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>E-Mail:</strong>{' '}
          <Link href="mailto:bamf@bamf.bund.de">bamf@bamf.bund.de</Link>
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Internet:</strong>{' '}
          <Link href="https://www.bamf.de" target="_blank" rel="noopener noreferrer">
            www.bamf.de
          </Link>
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Rechtsform und Aufsicht</Typography>
        <Typography variant="body2" gutterBottom>
          Das Bundesamt für Migration und Flüchtlinge ist eine Bundesbehörde der Bundesrepublik
          Deutschland im Geschäftsbereich des Bundesministeriums des Innern und für Heimat (BMI).
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Aufsichtsbehörde:</strong><br />
          Bundesministerium des Innern und für Heimat (BMI)<br />
          Alt-Moabit 140, 10557 Berlin
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Umsatzsteuer-Identifikationsnummer:</strong> gemäß § 27 a UStG<br />
          Als Bundesbehörde ist das BAMF nicht umsatzsteuerpflichtig.
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Verantwortlich für den Inhalt gemäß § 55 Abs. 2 RStV
        </Typography>
        <Typography variant="body2">
          Bundesamt für Migration und Flüchtlinge<br />
          Frankenstraße 210<br />
          90461 Nürnberg
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Technischer Betrieb</Typography>
        <Typography variant="body2">
          BAMF BorderCapControl ist eine interne Fachanwendung des BAMF zur Belegungsplanung
          und Kapazitätsverwaltung von Aufnahmeeinrichtungen. Sie ist ausschließlich für
          autorisierte Mitarbeitende zugänglich.
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>Haftungsausschluss</Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Haftung für Inhalte:</strong> Die Inhalte dieser Anwendung wurden mit größter
          Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität der Inhalte
          übernimmt das BAMF keine Gewähr.
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Haftung für Links:</strong> Diese Anwendung enthält Links zu externen Webseiten
          Dritter, auf deren Inhalte das BAMF keinen Einfluss hat. Für die Inhalte der verlinkten
          Seiten ist stets der jeweilige Anbieter verantwortlich.
        </Typography>
        <Typography variant="body2">
          <strong>Urheberrecht:</strong> Die durch das BAMF erstellten Inhalte und Werke dieser
          Anwendung unterliegen dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung,
          Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechts bedürfen
          der schriftlichen Zustimmung des BAMF.
        </Typography>
      </Paper>

      <Paper elevation={1} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Barrierefreiheit (BITV 2.0 / WCAG 2.1)
        </Typography>
        <Typography variant="body2" gutterBottom>
          Das BAMF ist bemüht, diese Anwendung barrierefrei zugänglich zu machen. Diese
          Anwendung befindet sich in kontinuierlicher Weiterentwicklung und wird schrittweise
          an die Anforderungen der Barrierefreien-Informationstechnik-Verordnung (BITV 2.0)
          angepasst.
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Bekannte Einschränkungen:</strong> Einige interaktive Komponenten (Karten,
          komplexe Dialoge) sind möglicherweise noch nicht vollständig barrierefrei. Die
          Behebung wird priorisiert.
        </Typography>
        <Typography variant="body2">
          <strong>Feedback:</strong> Wenn Sie auf Barrieren stoßen oder Verbesserungen
          vorschlagen möchten, wenden Sie sich bitte an:{' '}
          <Link href="mailto:bamf@bamf.bund.de">bamf@bamf.bund.de</Link>
        </Typography>
      </Paper>
    </Box>
  )
}
