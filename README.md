# DTSpectrum

RF Explorer Live-Spektrumanalyse für Dwarf Connection Videofunkstrecken.

## Features

- Live-Spektrumanzeige mit matplotlib GUI
- Waterfall-Diagramm
- Peak Hold Funktion
- Optimiert für Dwarf Connection (5.1-5.9 GHz)
- ASCII-Terminal Version verfügbar

## Hardware

- RF Explorer (240-6100 MHz Modell)
- USB-Verbindung

## Installation

```bash
pip install pyserial matplotlib numpy
```

## Verwendung

**GUI Version:**
```bash
python rfexplorer_gui.py
```

**Terminal Version:**
```bash
python rfexplorer_live.py
```

## Frequenzbereiche

| Gerät | Frequenzbereich |
|-------|-----------------|
| Dwarf Connection | 5100-5900 MHz |
| WiFi 2.4 GHz | 2400-2500 MHz |
| WiFi 5 GHz | 5150-5850 MHz |

## Lizenz

MIT
