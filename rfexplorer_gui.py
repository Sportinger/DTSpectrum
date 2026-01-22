#!/usr/bin/env python3
"""RF Explorer Live-Spektrumanalyse - Liest aktuelle Geräteeinstellung"""

import serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button
from collections import deque
import numpy as np

PORT = '/dev/ttyUSB0'
BAUD = 500000

class RFExplorerGUI:
    def __init__(self, port, baud):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        # DWARF Connection: 5100-5900 MHz (fest)
        self.start_freq = 5100
        self.end_freq = 5900
        self.sweep_points = 112
        self.frequencies = np.linspace(self.start_freq, self.end_freq, self.sweep_points)

        self.history = deque(maxlen=50)
        self.current_sweep = np.full(self.sweep_points, -100.0)
        self.peak_hold = np.full(self.sweep_points, -120.0)
        self.buffer = b''
        self.connected = False

    def parse_config(self, data):
        """Parse Konfiguration vom Gerät - DEAKTIVIERT, feste Dwarf-Frequenz"""
        # Frequenz ist fest auf 5100-5900 MHz (Dwarf Connection)
        # Config vom Gerät wird ignoriert
        return False

    def parse_sweep(self, data):
        """Parse Sweep-Daten"""
        idx = data.rfind(b'$S')
        if idx >= 0 and len(data) > idx + 115:
            sweep_data = data[idx+3:idx+115]
            if len(sweep_data) == 112:
                return np.array([-(b / 2.0) for b in sweep_data])
        return None

    def read_data(self):
        """Lese serielle Daten"""
        if self.ser.in_waiting:
            new_data = self.ser.read(self.ser.in_waiting)
            self.buffer += new_data

            if len(self.buffer) > 5000:
                self.buffer = self.buffer[-2000:]

            # Parse Config wenn vorhanden
            self.parse_config(self.buffer)

            # Parse Sweep
            sweep = self.parse_sweep(self.buffer)
            if sweep is not None:
                self.connected = True
                self.current_sweep = sweep
                self.peak_hold = np.maximum(self.peak_hold, sweep)
                self.history.append(sweep.copy())
                return True
        return False

    def init_device(self):
        """Initialisiere Gerät"""
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.3)

        # Request Config
        self.ser.write(b'#\x04C0\r\n')
        time.sleep(0.5)

        data = self.ser.read(2000)
        self.buffer = data

        if b'RF Explorer' in data:
            idx = data.find(b'RF Explorer')
            end = data.find(b'\r\n', idx)
            if end > idx:
                fw = data[idx:end].decode('ascii', errors='ignore')
                print(f"Gerät: {fw}")

        self.parse_config(data)
        print(f"Aktueller Bereich: {self.start_freq:.0f} - {self.end_freq:.0f} MHz")
        print("\nHINWEIS: Frequenzbereich am RF Explorer selbst einstellen!")
        print("Die GUI liest automatisch die aktuelle Einstellung.\n")

    def run(self):
        """Starte GUI"""
        self.init_device()

        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [2, 1]})

        fig.suptitle(f'RF Explorer Live | {self.start_freq:.0f}-{self.end_freq:.0f} MHz',
                    fontsize=14, color='cyan')

        # Spektrum-Plot
        line_current, = ax1.plot(self.frequencies, self.current_sweep, 'c-', lw=1.5, label='Aktuell')
        line_peak, = ax1.plot(self.frequencies, self.peak_hold, 'r-', lw=1, alpha=0.7, label='Peak Hold')
        ax1.set_xlim(self.start_freq, self.end_freq)
        ax1.set_ylim(-110, -20)
        ax1.set_xlabel('Frequenz (MHz)', fontsize=10)
        ax1.set_ylabel('Signalstärke (dBm)', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')

        peak_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes, va='top',
                            fontsize=11, color='yellow', family='monospace',
                            bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

        status_text = ax1.text(0.98, 0.98, '', transform=ax1.transAxes, va='top', ha='right',
                              fontsize=10, color='lime', family='monospace')

        # Waterfall-Plot
        waterfall_data = np.full((50, self.sweep_points), -100.0)
        waterfall = ax2.imshow(waterfall_data, aspect='auto', cmap='viridis',
                               extent=[self.start_freq, self.end_freq, 50, 0],
                               vmin=-100, vmax=-40)
        ax2.set_xlabel('Frequenz (MHz)')
        ax2.set_ylabel('Zeit')
        plt.colorbar(waterfall, ax=ax2, label='dBm', shrink=0.8)

        # Reset Button
        ax_btn = plt.axes([0.8, 0.01, 0.15, 0.04])
        btn_reset = Button(ax_btn, 'Reset Peak', color='darkred', hovercolor='red')

        def reset_peak(event):
            self.peak_hold = np.full(self.sweep_points, -120.0)

        btn_reset.on_clicked(reset_peak)

        frame_count = [0]

        def update(frame):
            self.read_data()
            frame_count[0] += 1

            # Update Achsen wenn Frequenz sich ändert
            if ax1.get_xlim() != (self.start_freq, self.end_freq):
                ax1.set_xlim(self.start_freq, self.end_freq)
                fig.suptitle(f'RF Explorer Live | {self.start_freq:.0f}-{self.end_freq:.0f} MHz',
                           fontsize=14, color='cyan')

            # Update Spektrum
            line_current.set_xdata(self.frequencies)
            line_peak.set_xdata(self.frequencies)
            line_current.set_ydata(self.current_sweep)
            line_peak.set_ydata(self.peak_hold)

            # Peak-Info
            peak_val = np.max(self.current_sweep)
            peak_idx = np.argmax(self.current_sweep)
            peak_freq = self.frequencies[peak_idx]
            avg_val = np.mean(self.current_sweep)
            noise_floor = np.min(self.current_sweep)

            peak_text.set_text(f'Peak: {peak_val:.1f} dBm @ {peak_freq:.1f} MHz\n'
                             f'Avg: {avg_val:.1f} dBm | Noise: {noise_floor:.1f} dBm')

            # Status
            if self.connected:
                status_text.set_text('LIVE')
                status_text.set_color('lime')
            else:
                status_text.set_text('WARTE...')
                status_text.set_color('yellow')

            # Update Waterfall
            if len(self.history) > 0:
                wf_data = np.array(list(self.history))
                if len(wf_data) < 50:
                    padding = np.full((50 - len(wf_data), self.sweep_points), -100.0)
                    wf_data = np.vstack([padding, wf_data])
                waterfall.set_data(wf_data)
                waterfall.set_extent([self.start_freq, self.end_freq, 50, 0])

            return line_current, line_peak, waterfall, peak_text, status_text

        ani = animation.FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)

        plt.tight_layout()
        plt.show()

        self.ser.close()


if __name__ == '__main__':
    print("RF Explorer Live-Spektrumanalyse")
    print("=" * 40)
    print("Frequenz am RF Explorer einstellen!")
    print("GUI liest automatisch die Einstellung.")
    print()
    gui = RFExplorerGUI(PORT, BAUD)
    gui.run()
