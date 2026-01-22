# DTSpectrum - Claude Anweisungen

## Projekt

RF Explorer Live-Spektrumanalyse für Dwarf Connection Videofunkstrecken (5.1-5.9 GHz).

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `rfexplorer_gui.py` | Matplotlib GUI mit Spektrum + Waterfall + Kanal-Buttons |
| `rfexplorer_live.py` | ASCII Terminal-Version |
| `rfexplorer_record.py` | Langzeit-Aufzeichnung mit Analyse-Report |

## Hardware

- **RF Explorer**: 240-6100 MHz Modell (Firmware 03.45)
- **Port**: `/dev/ttyUSB0`
- **Baudrate**: 500000

## Features

- **Live-Spektrum** mit Peak Hold
- **Waterfall-Diagramm**
- **Dynamische Y-Achse** (passt sich automatisch an)
- **SNR-Anzeige** (Signal-Rausch-Abstand)
- **Kanal-Presets** per Button umschaltbar
- **Remote-Frequenzsteuerung** funktioniert!
- **Langzeit-Recording** mit CSV-Export und Analyse

## Kanal-Presets

| Preset | Frequenz | Beschreibung |
|--------|----------|--------------|
| Kanal 4 | 5500-5700 MHz | Dwarf Kanal 4 |
| Kanal 8 | 5600-5800 MHz | Dwarf Kanal 8 |
| Kanal 4+8 | 5450-5850 MHz | Beide Kanäle |
| Full Band | 5100-5900 MHz | Ganzes Dwarf-Band (langsamer) |

## Starten

```bash
# GUI mit Kanal-Buttons
python rfexplorer_gui.py

# Langzeit-Aufzeichnung (10 Min)
python rfexplorer_record.py -d 10

# Terminal-Version
python rfexplorer_live.py
```

## Recording-Optionen

```bash
python rfexplorer_record.py -d 30        # 30 Minuten aufzeichnen
python rfexplorer_record.py -i 0.5       # Alle 0.5 Sekunden messen
python rfexplorer_record.py -o test.csv  # Eigener Dateiname
```

## Dependencies

```bash
pip install pyserial matplotlib numpy
```

## Protokoll-Notizen

- Frequenz setzen: `#<len+2>C2-F:StartKHz,EndKHz,Top,Bottom`
- Config lesen: `#\x04C0`
- Sweep-Daten: `$Sp` + 112 Bytes (je Byte = -dBm/2)
