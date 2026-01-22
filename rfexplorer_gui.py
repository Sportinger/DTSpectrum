#!/usr/bin/env python3
"""RF Explorer Live-Spektrumanalyse mit Kanal-Auswahl für Dwarf Connection"""

import serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Button
from collections import deque
import numpy as np

PORT = '/dev/ttyUSB0'
BAUD = 500000

# Frequenz-Presets für Dwarf Connection
PRESETS = {
    'Kanal 4': (5500, 5700),
    'Kanal 8': (5600, 5800),
    'Kanal 4+8': (5450, 5850),
    'Full Band': (5100, 5900),
}

class RFExplorerGUI:
    def __init__(self, port, baud):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self.start_freq = 5500
        self.end_freq = 5700
        self.sweep_points = 112
        self.frequencies = np.linspace(self.start_freq, self.end_freq, self.sweep_points)

        self.history = deque(maxlen=50)
        self.current_sweep = np.full(self.sweep_points, -100.0)
        self.peak_hold = np.full(self.sweep_points, -120.0)
        self.buffer = b''
        self.connected = False
        self.sweep_count = 0
        self.last_sweep_time = time.time()
        self.sweeps_per_sec = 0

    def set_frequency(self, start_mhz, end_mhz):
        """Setze Frequenzbereich am RF Explorer"""
        start_khz = int(start_mhz * 1000)
        end_khz = int(end_mhz * 1000)
        cmd = f"C2-F:{start_khz:07d},{end_khz:07d},0000,-120"
        full = "#" + chr(len(cmd) + 2) + cmd
        self.ser.write(full.encode())

        self.start_freq = start_mhz
        self.end_freq = end_mhz
        self.frequencies = np.linspace(start_mhz, end_mhz, self.sweep_points)
        self.peak_hold = np.full(self.sweep_points, -120.0)
        self.history.clear()
        self.buffer = b''

        print(f"Frequenz: {start_mhz:.0f}-{end_mhz:.0f} MHz")

    def parse_sweep(self, data):
        """Parse Sweep-Daten"""
        idx = data.rfind(b'$S')
        if idx >= 0 and len(data) > idx + 115:
            sweep_data = data[idx+3:idx+115]
            if len(sweep_data) == 112:
                return np.array([-(b / 2.0) for b in sweep_data])
        return None

    def read_data(self):
        """Lese serielle Daten - optimiert für Geschwindigkeit"""
        updated = False

        # Lese ALLE verfügbaren Daten
        while self.ser.in_waiting:
            new_data = self.ser.read(min(self.ser.in_waiting, 4096))
            self.buffer += new_data

        if len(self.buffer) > 8000:
            self.buffer = self.buffer[-4000:]

        # Parse ALLE Sweeps im Buffer
        idx = 0
        while True:
            idx = self.buffer.find(b'$S', idx)
            if idx == -1 or len(self.buffer) < idx + 115:
                break

            sweep_data = self.buffer[idx+3:idx+115]
            if len(sweep_data) == 112:
                sweep = np.array([-(b / 2.0) for b in sweep_data])
                self.current_sweep = sweep
                self.peak_hold = np.maximum(self.peak_hold, sweep)
                self.history.append(sweep.copy())
                self.sweep_count += 1
                updated = True
            idx += 116

        # Entferne verarbeitete Daten
        if idx > 0:
            self.buffer = self.buffer[idx:]

        if updated:
            self.connected = True
            now = time.time()
            if now - self.last_sweep_time >= 1.0:
                self.sweeps_per_sec = self.sweep_count
                self.sweep_count = 0
                self.last_sweep_time = now

        return updated

    def init_device(self):
        """Initialisiere Gerät"""
        self.ser.reset_input_buffer()
        time.sleep(0.3)
        self.set_frequency(5500, 5700)

    def run(self):
        """Starte GUI"""
        self.init_device()

        plt.style.use('dark_background')
        fig = plt.figure(figsize=(14, 9))

        ax1 = plt.subplot2grid((3, 5), (0, 0), colspan=4, rowspan=2)
        ax2 = plt.subplot2grid((3, 5), (2, 0), colspan=4)

        fig.suptitle(f'Dwarf Connection | {self.start_freq:.0f}-{self.end_freq:.0f} MHz',
                    fontsize=14, color='cyan')

        # Spektrum
        line_current, = ax1.plot(self.frequencies, self.current_sweep, 'c-', lw=1.5, label='Aktuell')
        line_peak, = ax1.plot(self.frequencies, self.peak_hold, 'r-', lw=1, alpha=0.7, label='Peak Hold')
        ax1.set_xlim(self.start_freq, self.end_freq)
        ax1.set_ylim(-110, -20)
        ax1.set_xlabel('Frequenz (MHz)')
        ax1.set_ylabel('dBm')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')

        peak_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes, va='top',
                            fontsize=11, color='yellow', family='monospace',
                            bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

        status_text = ax1.text(0.98, 0.98, '', transform=ax1.transAxes, va='top', ha='right',
                              fontsize=12, color='lime', family='monospace')

        # Waterfall
        waterfall_data = np.full((50, self.sweep_points), -100.0)
        waterfall = ax2.imshow(waterfall_data, aspect='auto', cmap='viridis',
                               extent=[self.start_freq, self.end_freq, 50, 0],
                               vmin=-100, vmax=-40)
        ax2.set_xlabel('Frequenz (MHz)')
        ax2.set_ylabel('Zeit')
        plt.colorbar(waterfall, ax=ax2, label='dBm', shrink=0.8)

        # Buttons
        buttons = []
        btn_y = 0.82
        for name, (start, end) in PRESETS.items():
            ax_btn = plt.axes([0.82, btn_y, 0.15, 0.06])
            btn = Button(ax_btn, name, color='darkblue', hovercolor='blue')

            def make_cb(s, e, n):
                def cb(event):
                    self.set_frequency(s, e)
                    ax1.set_xlim(s, e)
                    fig.suptitle(f'Dwarf Connection | {n} ({s:.0f}-{e:.0f} MHz)',
                               fontsize=14, color='cyan')
                return cb
            btn.on_clicked(make_cb(start, end, name))
            buttons.append(btn)
            btn_y -= 0.08

        # Reset Peak
        ax_reset = plt.axes([0.82, btn_y - 0.02, 0.15, 0.06])
        btn_reset = Button(ax_reset, 'Reset Peak', color='darkred', hovercolor='red')
        btn_reset.on_clicked(lambda e: self.peak_hold.fill(-120))

        def update(frame):
            self.read_data()

            line_current.set_xdata(self.frequencies)
            line_peak.set_xdata(self.frequencies)
            line_current.set_ydata(self.current_sweep)
            line_peak.set_ydata(self.peak_hold)

            if ax1.get_xlim() != (self.start_freq, self.end_freq):
                ax1.set_xlim(self.start_freq, self.end_freq)
                waterfall.set_extent([self.start_freq, self.end_freq, 50, 0])

            # Dynamische Y-Achse
            peak_val = np.max(self.current_sweep)
            noise_val = np.min(self.current_sweep)
            peak_hold_max = np.max(self.peak_hold)

            # Y-Limits mit Padding (5 dB oben/unten)
            y_max = min(-20, peak_hold_max + 5)
            y_min = max(-110, noise_val - 5)
            ax1.set_ylim(y_min, y_max)

            # Waterfall auch anpassen
            waterfall.set_clim(vmin=y_min, vmax=y_max)

            peak_idx = np.argmax(self.current_sweep)
            peak_freq = self.frequencies[peak_idx]
            avg_val = np.mean(self.current_sweep)
            snr = peak_val - noise_val

            peak_text.set_text(f'Peak: {peak_val:.1f} dBm @ {peak_freq:.0f} MHz\n'
                             f'Noise: {noise_val:.1f} dBm | SNR: {snr:.0f} dB')

            status_text.set_text(f'{self.sweeps_per_sec}/s')

            if len(self.history) > 0:
                wf_data = np.array(list(self.history))
                if len(wf_data) < 50:
                    padding = np.full((50 - len(wf_data), self.sweep_points), -100.0)
                    wf_data = np.vstack([padding, wf_data])
                waterfall.set_data(wf_data)

            return line_current, line_peak, waterfall, peak_text, status_text

        ani = animation.FuncAnimation(fig, update, interval=16, blit=False, cache_frame_data=False)  # ~60 FPS
        plt.tight_layout()
        plt.show()
        self.ser.close()


if __name__ == '__main__':
    print("Dwarf Connection Spektrumanalyse")
    print("=" * 35)
    gui = RFExplorerGUI(PORT, BAUD)
    gui.run()
