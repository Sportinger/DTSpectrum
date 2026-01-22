#!/usr/bin/env python3
"""RF Explorer Live-Spektrumanalyse mit ASCII-Visualisierung"""

import serial
import time
import sys
import os

PORT = '/dev/ttyUSB0'
BAUD = 500000

class RFExplorer:
    def __init__(self, port, baud):
        self.ser = serial.Serial(port, baud, timeout=0.5)
        self.start_freq = 0
        self.end_freq = 0
        self.step_freq = 0
        self.sweep_points = 112
        self.model = ""
        self.firmware = ""

    def read_until_marker(self, marker=b'\r\n', timeout=2):
        """Lese bis Marker gefunden"""
        data = b''
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                data += self.ser.read(self.ser.in_waiting)
                if marker in data:
                    return data
            time.sleep(0.01)
        return data

    def parse_config(self, data):
        """Parse #C2-F Konfigurationsdaten"""
        # Format: #C2-F:Start_Freq,End_Freq,Amp_Top,Amp_Bottom
        if b'#C2-F:' in data:
            try:
                idx = data.find(b'#C2-F:')
                line = data[idx:].split(b'\r\n')[0].decode('ascii', errors='ignore')
                parts = line.replace('#C2-F:', '').split(',')
                if len(parts) >= 2:
                    self.start_freq = int(parts[0]) / 1000  # kHz -> MHz
                    self.end_freq = int(parts[1]) / 1000
                    self.step_freq = (self.end_freq - self.start_freq) / self.sweep_points
                    return True
            except:
                pass
        return False

    def parse_sweep(self, data):
        """Parse $S Sweep-Daten"""
        sweeps = []
        idx = 0
        while True:
            idx = data.find(b'$S', idx)
            if idx == -1:
                break
            if len(data) > idx + 115:
                sweep_data = data[idx+3:idx+115]
                if len(sweep_data) == 112:
                    # Konvertiere zu dBm (jedes Byte = -dBm/2)
                    dbm_values = [-(b / 2.0) for b in sweep_data]
                    sweeps.append(dbm_values)
            idx += 1
        return sweeps[-1] if sweeps else None

    def init_device(self):
        """Initialisiere RF Explorer"""
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        # Lese initiale Daten
        time.sleep(0.5)
        data = self.ser.read(2000)

        # Extrahiere Modell/Firmware
        if b'RF Explorer' in data:
            idx = data.find(b'RF Explorer')
            end = data.find(b'\r\n', idx)
            if end > idx:
                self.firmware = data[idx:end].decode('ascii', errors='ignore')
                print(f"Gerät: {self.firmware}")

        # Request Config
        self.ser.write(b'#\x04C0\r\n')
        time.sleep(0.3)
        data = self.ser.read(1000)

        if self.parse_config(data):
            print(f"Frequenzbereich: {self.start_freq:.1f} - {self.end_freq:.1f} MHz")
            print(f"Schrittweite: {self.step_freq*1000:.1f} kHz")
        else:
            # Default für 2.4G Modul
            self.start_freq = 2400
            self.end_freq = 2500
            self.step_freq = (self.end_freq - self.start_freq) / 112
            print("Verwende Standard 2.4GHz Bereich")

    def draw_spectrum(self, sweep):
        """Zeichne ASCII-Spektrum"""
        if not sweep:
            return

        # Terminal-Breite
        try:
            cols = os.get_terminal_size().columns - 15
        except:
            cols = 80

        # Resample auf Terminal-Breite
        if len(sweep) > cols:
            step = len(sweep) / cols
            resampled = [sweep[int(i * step)] for i in range(cols)]
        else:
            resampled = sweep

        # Finde Peak
        peak_val = max(sweep)
        peak_idx = sweep.index(peak_val)
        peak_freq = self.start_freq + (peak_idx * self.step_freq)

        # Statistiken
        avg_val = sum(sweep) / len(sweep)
        noise_floor = min(sweep)

        # Zeichne Balken (10 Zeilen Höhe)
        height = 10
        min_db = -100
        max_db = -20

        print("\033[H\033[J", end='')  # Clear screen
        print(f"RF Explorer Live | {self.start_freq:.0f}-{self.end_freq:.0f} MHz | Peak: {peak_freq:.1f} MHz @ {peak_val:.1f} dBm")
        print("=" * (cols + 10))

        for row in range(height):
            threshold = max_db - (row * (max_db - min_db) / height)
            line = f"{threshold:5.0f}dBm |"
            for val in resampled:
                if val >= threshold:
                    line += '#'
                else:
                    line += ' '
            print(line)

        # X-Achse
        print(" " * 9 + "+" + "-" * cols)
        print(f"         {self.start_freq:.0f}" + " " * (cols - 15) + f"{self.end_freq:.0f} MHz")
        print()
        print(f"Peak: {peak_val:.1f} dBm @ {peak_freq:.1f} MHz | Avg: {avg_val:.1f} dBm | Noise: {noise_floor:.1f} dBm")

    def run(self):
        """Hauptschleife"""
        self.init_device()
        print("\nStarte Live-Anzeige... (Strg+C zum Beenden)\n")
        time.sleep(1)

        buffer = b''
        last_draw = 0

        try:
            while True:
                if self.ser.in_waiting:
                    buffer += self.ser.read(self.ser.in_waiting)

                    # Begrenze Buffer-Größe
                    if len(buffer) > 5000:
                        buffer = buffer[-2000:]

                    # Parse Sweep
                    sweep = self.parse_sweep(buffer)
                    if sweep and time.time() - last_draw > 0.1:
                        self.draw_spectrum(sweep)
                        last_draw = time.time()

                        # Parse auch Config updates
                        self.parse_config(buffer)

                time.sleep(0.02)

        except KeyboardInterrupt:
            print("\n\nBeendet.")
        finally:
            self.ser.close()


if __name__ == '__main__':
    print("RF Explorer Live-Spektrumanalyse")
    print("-" * 35)
    rf = RFExplorer(PORT, BAUD)
    rf.run()
