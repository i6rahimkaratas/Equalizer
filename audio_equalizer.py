import numpy as np
import sounddevice as sd
from scipy import signal
import tkinter as tk
from tkinter import ttk

class AudioEqualizer:
    def __init__(self):
        self.sample_rate = 44100
        self.block_size = 2048
        self.is_running = False
        
        # Equalizer bantları (Hz cinsinden)
        self.bands = {
            '60 Hz': 60,
            '170 Hz': 170,
            '310 Hz': 310,
            '600 Hz': 600,
            '1 kHz': 1000,
            '3 kHz': 3000,
            '6 kHz': 6000,
            '12 kHz': 12000,
            '14 kHz': 14000,
            '16 kHz': 16000
        }
        
        # Her bant için kazanç değerleri (dB)
        self.gains = {band: 0.0 for band in self.bands}
        
        # Filtre parametreleri
        self.q_factor = 1.0  # Bant genişliği
        
    def create_peak_filter(self, center_freq, gain_db, q_factor):
        """Belirli bir frekans için peak/notch filtresi oluşturur"""
        gain = 10 ** (gain_db / 20)  # dB'den lineer kazanca çevir
        
        w0 = 2 * np.pi * center_freq / self.sample_rate
        alpha = np.sin(w0) / (2 * q_factor)
        
        A = gain
        
        # Biquad filtre katsayıları
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A
        
        # Normalize et
        b = np.array([b0/a0, b1/a0, b2/a0])
        a = np.array([1, a1/a0, a2/a0])
        
        return b, a
    
    def apply_equalizer(self, audio_data):
        """Equalizer filtrelerini ses verisine uygula"""
        output = audio_data.copy()
        
        for band_name, center_freq in self.bands.items():
            gain_db = self.gains[band_name]
            
            if abs(gain_db) > 0.1:  # Sadece önemli kazançları uygula
                b, a = self.create_peak_filter(center_freq, gain_db, self.q_factor)
                
                # Her kanal için filtreleme
                if len(output.shape) == 1:  # Mono
                    output = signal.lfilter(b, a, output)
                else:  # Stereo
                    for ch in range(output.shape[1]):
                        output[:, ch] = signal.lfilter(b, a, output[:, ch])
        
        # Clipping önleme
        output = np.clip(output, -1.0, 1.0)
        
        return output
    
    def audio_callback(self, indata, outdata, frames, time, status):
        """Ses akışı callback fonksiyonu"""
        if status:
            print(f'Status: {status}')
        
        # Equalizer uygula
        processed = self.apply_equalizer(indata.copy())
        outdata[:] = processed
    
    def start_stream(self):
        """Ses akışını başlat"""
        try:
            self.stream = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=2,
                callback=self.audio_callback
            )
            self.stream.start()
            self.is_running = True
            print("Equalizer başlatıldı!")
        except Exception as e:
            print(f"Hata: {e}")
    
    def stop_stream(self):
        """Ses akışını durdur"""
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
            self.is_running = False
            print("Equalizer durduruldu!")
    
    def set_gain(self, band_name, gain_db):
        """Belirli bir bant için kazanç ayarla"""
        if band_name in self.gains:
            self.gains[band_name] = gain_db


class EqualizerGUI:
    def __init__(self):
        self.eq = AudioEqualizer()
        self.window = tk.Tk()
        self.window.title("Ses Equalizer")
        self.window.geometry("600x550")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Başlık
        title = tk.Label(self.window, text="10 Bantlı Equalizer", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Equalizer bantları frame
        bands_frame = tk.Frame(self.window)
        bands_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        self.sliders = {}
        self.labels = {}
        
        # Her bant için slider oluştur
        for i, (band_name, freq) in enumerate(self.eq.bands.items()):
            frame = tk.Frame(bands_frame)
            frame.grid(row=i//5, column=i%5, padx=5, pady=5)
            
            # Bant ismi
            label = tk.Label(frame, text=band_name, font=("Arial", 9))
            label.pack()
            
            # Gain değeri etiketi
            value_label = tk.Label(frame, text="0 dB", font=("Arial", 8))
            value_label.pack()
            self.labels[band_name] = value_label
            
            # Slider
            slider = tk.Scale(
                frame,
                from_=12,
                to=-12,
                resolution=0.5,
                orient=tk.VERTICAL,
                length=150,
                command=lambda val, name=band_name: self.on_slider_change(name, val)
            )
            slider.set(0)
            slider.pack()
            self.sliders[band_name] = slider
        
        # Kontrol butonları
        control_frame = tk.Frame(self.window)
        control_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            control_frame,
            text="Başlat",
            command=self.toggle_equalizer,
            bg="green",
            fg="white",
            font=("Arial", 12, "bold"),
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(
            control_frame,
            text="Sıfırla",
            command=self.reset_all,
            bg="orange",
            fg="white",
            font=("Arial", 12, "bold"),
            width=15
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Durum bilgisi
        self.status_label = tk.Label(
            self.window,
            text="Durum: Durduruldu",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=5)
        
    def on_slider_change(self, band_name, value):
        """Slider değiştiğinde"""
        gain = float(value)
        self.eq.set_gain(band_name, gain)
        self.labels[band_name].config(text=f"{gain:+.1f} dB")
    
    def toggle_equalizer(self):
        """Equalizer'ı başlat/durdur"""
        if not self.eq.is_running:
            self.eq.start_stream()
            self.start_btn.config(text="Durdur", bg="red")
            self.status_label.config(text="Durum: Çalışıyor")
        else:
            self.eq.stop_stream()
            self.start_btn.config(text="Başlat", bg="green")
            self.status_label.config(text="Durum: Durduruldu")
    
    def reset_all(self):
        """Tüm bantları sıfırla"""
        for band_name, slider in self.sliders.items():
            slider.set(0)
            self.eq.set_gain(band_name, 0)
            self.labels[band_name].config(text="0 dB")
    
    def run(self):
        """GUI'yi çalıştır"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()
    
    def on_closing(self):
        """Pencere kapatılırken"""
        self.eq.stop_stream()
        self.window.destroy()


if __name__ == "__main__":
    # Gerekli kütüphaneleri kontrol et
    try:
        app = EqualizerGUI()
        app.run()
    except Exception as e:
        print(f"Hata: {e}")
        print("\nGerekli kütüphaneleri yüklemek için:")
        print("pip install numpy sounddevice scipy")
