# Kapazitätsübersicht (Dashboard)

## Was zeigt das Dashboard?

Die Startseite gibt eine Übersicht aller Einrichtungen mit ihrem aktuellen Belegungsstand. Ihre eigene Einrichtung erscheint zuerst und ist blau umrandet. Standard-Ansicht ist die **Kartenansicht**.

## Ampelfarben

| Farbe | Bedeutung | Auslastung |
|-------|-----------|-----------|
| 🟢 Grün | Kapazität verfügbar | unter 70 % |
| 🟡 Gelb | Kapazität begrenzt | 70–90 % |
| 🔴 Rot | Kapazität kritisch | über 90 % |

## Ansicht wechseln

Mit den Schaltflächen oben rechts wechseln Sie zwischen **Rasteransicht** (Kacheln) und **Kartenansicht** (Leaflet-Karte mit Farbmarkierungen je nach Auslastung). Standard ist die Kartenansicht.

## Einrichtungskachel (Rasteransicht)

Jede Kachel zeigt Auslastung, belegte und freie Plätze. Erscheint ein orangener Chip **„Endet in X Tagen"**, läuft der Gültigkeitszeitraum der Einrichtung demnächst ab.

## Schnellzugriff eigene Einrichtung

Das **Gebäude-Symbol** in der Navigationsleiste (nur sichtbar für einrichtungsgebundene Nutzer, nicht für System-Admins) springt direkt zur eigenen Einrichtungsdetail-Ansicht.

## Meine Reservierungen (Schnellzugriff)

Laufende Verlegungsanfragen Ihrer Einrichtung (eingehend und ausgehend) erscheinen als kleine Chips mit AZR-ID und Richtungspfeil (← eingehend / → ausgehend). Ein Klick auf einen Chip oder auf **„Alle anzeigen →"** öffnet die Verlegungsanfragen-Übersicht. Es werden max. 5 der aktuellsten Anfragen angezeigt.

## Neue Einrichtung anlegen (Administratoren)

Der Button „Neue Einrichtung" erscheint nur für Nutzer mit der Rolle **location-admin** oder **system-admin**. Nach dem Anlegen können Räume, Betten und ein Wartebereich in der Einrichtungsdetail-Ansicht verwaltet werden.

**Kontingent** — Anzahl der EU-quotenrelevanten Betten. Jede Belegung startet einen 12-Wochen-Timer.

**Notbett-Kapazität** — Temporäre Plätze für max. 1 Nacht (nicht EU-quotenrelevant).

## Kontingent-Reporting (nur System-Admin)

Unterhalb der Einrichtungsübersicht sehen System-Admins ein **Kontingent-Reporting-Panel**:

| Kenngröße | Bedeutung |
|-----------|-----------|
| EU-Gesamtquote | Nationale Vorgabe für die Gesamtkapazität Deutschlands |
| Summe Kontingente | Summe der eingetragenen Einrichtungskontingente |
| Reguläre Betten | Tatsächlich im System erfasste Kontingentbetten |
| Abweichung gesamt | Differenz Kontingent minus reale Betten |

**Positive Abweichung (orange)** — mehr Kontingent als Betten; Betten müssen noch angelegt werden.
**Negative Abweichung (rot)** — mehr Betten als Kontingent; EU-Reporting zeigt Überkapazität.

Die Tabelle darunter schlüsselt die Abweichung pro Einrichtung auf.
