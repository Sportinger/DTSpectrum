# DTSpectrum - Claude Anweisungen

## Projekt

RF Explorer Live-Spektrumanalyse für Dwarf Connection Videofunkstrecken (5.1-5.9 GHz).

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `rfexplorer_gui.py` | Matplotlib GUI mit Spektrum + Waterfall |
| `rfexplorer_live.py` | ASCII Terminal-Version |

## Hardware

- **RF Explorer**: 240-6100 MHz Modell
- **Port**: `/dev/ttyUSB0`
- **Baudrate**: 500000

## Frequenzbereiche

| Band | Start | Ende | Verwendung |
|------|-------|------|------------|
| Dwarf Connection | 5100 MHz | 5900 MHz | Videofunkstrecke |
| WiFi 2.4 GHz | 2400 MHz | 2500 MHz | WLAN |
| WiFi 5 GHz | 5150 MHz | 5850 MHz | WLAN |

## Wichtige Hinweise

- Frequenz muss **manuell am RF Explorer** eingestellt werden
- Remote-Frequenzsteuerung über Serial funktioniert nicht zuverlässig
- GUI liest nur Sweep-Daten, setzt keine Frequenz

## Starten

```bash
# GUI
python rfexplorer_gui.py

# Terminal
python rfexplorer_live.py
```

## Dependencies

```bash
pip install pyserial matplotlib numpy
```
