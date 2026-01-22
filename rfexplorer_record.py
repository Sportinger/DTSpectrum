#!/usr/bin/env python3
"""
RF Explorer Langzeit-Aufzeichnung und Analyse
Zeichnet Spektrumdaten auf und erstellt einen Analyse-Report.
"""

import serial
import time
import csv
import os
from datetime import datetime
import numpy as np

PORT = '/dev/ttyUSB0'
BAUD = 500000

# Dwarf Connection Frequenzbereich
START_FREQ = 5100  # MHz
END_FREQ = 5900    # MHz
SWEEP_POINTS = 112

class RFRecorder:
    def __init__(self, port, baud):
        self.ser = serial.Serial(port, baud, timeout=0.5)
        self.frequencies = np.linspace(START_FREQ, END_FREQ, SWEEP_POINTS)
        self.recordings = []
        self.start_time = None

    def parse_sweep(self, data):
        """Parse Sweep-Daten"""
        idx = data.rfind(b'$S')
        if idx >= 0 and len(data) > idx + 115:
            sweep_data = data[idx+3:idx+115]
            if len(sweep_data) == 112:
                return np.array([-(b / 2.0) for b in sweep_data])
        return None

    def record(self, duration_minutes=10, interval_seconds=1):
        """Aufnahme für bestimmte Dauer"""
        self.start_time = datetime.now()
        total_seconds = duration_minutes * 60

        print(f"=== RF Explorer Aufzeichnung ===")
        print(f"Frequenzbereich: {START_FREQ}-{END_FREQ} MHz")
        print(f"Dauer: {duration_minutes} Minuten")
        print(f"Intervall: {interval_seconds}s")
        print(f"Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 40)

        self.ser.reset_input_buffer()
        buffer = b''

        try:
            elapsed = 0
            last_record = 0

            while elapsed < total_seconds:
                # Daten lesen
                if self.ser.in_waiting:
                    buffer += self.ser.read(self.ser.in_waiting)
                    if len(buffer) > 5000:
                        buffer = buffer[-2000:]

                # Sweep parsen
                sweep = self.parse_sweep(buffer)

                current_time = time.time()
                if sweep is not None and (current_time - last_record) >= interval_seconds:
                    timestamp = datetime.now()

                    # Statistiken
                    peak_val = np.max(sweep)
                    peak_idx = np.argmax(sweep)
                    peak_freq = self.frequencies[peak_idx]
                    avg_val = np.mean(sweep)

                    # Speichern
                    self.recordings.append({
                        'timestamp': timestamp,
                        'elapsed_sec': elapsed,
                        'sweep': sweep.copy(),
                        'peak_dbm': peak_val,
                        'peak_freq': peak_freq,
                        'avg_dbm': avg_val
                    })

                    print(f"[{elapsed:4.0f}s] Peak: {peak_val:6.1f} dBm @ {peak_freq:.0f} MHz | Avg: {avg_val:.1f} dBm")

                    last_record = current_time
                    elapsed = (datetime.now() - self.start_time).total_seconds()

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n\nAufzeichnung abgebrochen.")

        print(f"\n{len(self.recordings)} Messungen aufgezeichnet.")
        return self.recordings

    def save_csv(self, filename=None):
        """Speichere Rohdaten als CSV"""
        if not filename:
            filename = f"rf_recording_{self.start_time.strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            header = ['timestamp', 'elapsed_sec', 'peak_dbm', 'peak_freq_mhz', 'avg_dbm']
            header += [f'{freq:.1f}MHz' for freq in self.frequencies]
            writer.writerow(header)

            # Daten
            for rec in self.recordings:
                row = [
                    rec['timestamp'].isoformat(),
                    rec['elapsed_sec'],
                    rec['peak_dbm'],
                    rec['peak_freq'],
                    rec['avg_dbm']
                ]
                row += list(rec['sweep'])
                writer.writerow(row)

        print(f"Daten gespeichert: {filepath}")
        return filepath

    def analyze(self):
        """Analysiere aufgezeichnete Daten und erstelle Report"""
        if not self.recordings:
            print("Keine Daten zum Analysieren.")
            return

        print("\n" + "=" * 60)
        print("RF SPEKTRUM ANALYSE - DWARF CONNECTION BAND (5.1-5.9 GHz)")
        print("=" * 60)

        # Zeitraum
        duration = (self.recordings[-1]['timestamp'] - self.recordings[0]['timestamp']).total_seconds()
        print(f"\nAufzeichnungszeitraum: {duration/60:.1f} Minuten")
        print(f"Anzahl Messungen: {len(self.recordings)}")

        # Alle Sweeps als Matrix
        all_sweeps = np.array([r['sweep'] for r in self.recordings])
        all_peaks = np.array([r['peak_dbm'] for r in self.recordings])
        all_peak_freqs = np.array([r['peak_freq'] for r in self.recordings])
        all_avgs = np.array([r['avg_dbm'] for r in self.recordings])

        # ===== GESAMTSTATISTIK =====
        print("\n--- GESAMTSTATISTIK ---")
        print(f"Peak Maximum:     {np.max(all_peaks):.1f} dBm")
        print(f"Peak Durchschnitt:{np.mean(all_peaks):.1f} dBm")
        print(f"Peak Minimum:     {np.min(all_peaks):.1f} dBm")
        print(f"Noise Floor:      {np.min(all_sweeps):.1f} dBm")
        print(f"Durchschn. Level: {np.mean(all_avgs):.1f} dBm")

        # ===== FREQUENZANALYSE =====
        print("\n--- FREQUENZANALYSE ---")

        # Durchschnittliches Spektrum
        avg_spectrum = np.mean(all_sweeps, axis=0)
        max_spectrum = np.max(all_sweeps, axis=0)

        # Finde die aktivsten Frequenzen
        top_indices = np.argsort(max_spectrum)[-5:][::-1]
        print("\nAktivste Frequenzen (höchste gemessene Pegel):")
        for i, idx in enumerate(top_indices):
            freq = self.frequencies[idx]
            max_val = max_spectrum[idx]
            avg_val = avg_spectrum[idx]
            print(f"  {i+1}. {freq:.0f} MHz: Max {max_val:.1f} dBm, Avg {avg_val:.1f} dBm")

        # ===== ZEITLICHE ANALYSE =====
        print("\n--- ZEITLICHE ANALYSE ---")

        # Aktivitätsphasen erkennen
        threshold = np.mean(all_peaks) + 5  # 5 dB über Durchschnitt
        active_periods = all_peaks > threshold
        active_count = np.sum(active_periods)
        active_percent = (active_count / len(all_peaks)) * 100

        print(f"Aktivitätsschwelle: {threshold:.1f} dBm")
        print(f"Aktive Perioden:    {active_count} von {len(all_peaks)} ({active_percent:.1f}%)")

        # ===== DWARF CONNECTION INTERPRETATION =====
        print("\n--- INTERPRETATION FÜR DWARF CONNECTION ---")
        print()

        # Signalqualität bewerten
        avg_peak = np.mean(all_peaks)
        if avg_peak > -50:
            quality = "AUSGEZEICHNET"
            desc = "Sehr starkes Signal, optimale Übertragung möglich."
        elif avg_peak > -60:
            quality = "GUT"
            desc = "Gutes Signal, stabile Übertragung erwartet."
        elif avg_peak > -70:
            quality = "MITTEL"
            desc = "Akzeptables Signal, gelegentliche Störungen möglich."
        elif avg_peak > -80:
            quality = "SCHWACH"
            desc = "Schwaches Signal, Verbindungsabbrüche wahrscheinlich."
        else:
            quality = "SEHR SCHWACH / KEIN SIGNAL"
            desc = "Kaum Signal erkennbar, Verbindung nicht möglich."

        print(f"Signalqualität: {quality}")
        print(f"Bewertung: {desc}")
        print()

        # Störanalyse
        noise_floor = np.min(all_sweeps)
        snr = avg_peak - noise_floor
        print(f"Signal-Rausch-Abstand (SNR): {snr:.1f} dB")

        if snr > 30:
            print("  -> Hervorragender SNR, sehr klare Signaltrennung")
        elif snr > 20:
            print("  -> Guter SNR, ausreichend für HD-Video")
        elif snr > 10:
            print("  -> Akzeptabler SNR, SD-Video möglich")
        else:
            print("  -> Niedriger SNR, starke Interferenzen")

        # Frequenzstabilität
        freq_std = np.std(all_peak_freqs)
        print(f"\nFrequenzstabilität: ±{freq_std:.1f} MHz")
        if freq_std < 10:
            print("  -> Sehr stabil, feste Sendefrequenz")
        elif freq_std < 50:
            print("  -> Normale Variation, möglicherweise Frequency Hopping")
        else:
            print("  -> Hohe Variation, mehrere Quellen oder instabiler Sender")

        # Kanalempfehlung
        print("\n--- KANALEMPFEHLUNG ---")
        # Finde ruhigste Frequenzbereiche (niedrigste Durchschnittspegel)
        quiet_indices = np.argsort(avg_spectrum)[:5]
        print("Ruhigste Frequenzen (für minimale Interferenz):")
        for idx in quiet_indices:
            freq = self.frequencies[idx]
            avg_val = avg_spectrum[idx]
            print(f"  {freq:.0f} MHz: Avg {avg_val:.1f} dBm")

        print("\n" + "=" * 60)
        print("ANALYSE ABGESCHLOSSEN")
        print("=" * 60)

    def close(self):
        self.ser.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='RF Explorer Langzeit-Aufzeichnung')
    parser.add_argument('-d', '--duration', type=int, default=5,
                        help='Aufnahmedauer in Minuten (default: 5)')
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                        help='Messintervall in Sekunden (default: 1.0)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Ausgabe-CSV-Datei')

    args = parser.parse_args()

    print("RF Explorer Langzeit-Aufzeichnung")
    print("-" * 40)

    recorder = RFRecorder(PORT, BAUD)

    try:
        # Aufzeichnen
        recorder.record(duration_minutes=args.duration, interval_seconds=args.interval)

        # Speichern
        recorder.save_csv(args.output)

        # Analysieren
        recorder.analyze()

    finally:
        recorder.close()


if __name__ == '__main__':
    main()
