# stt_module.py

import torch
torch.set_num_threads(1)
import time
import numpy as np
import pyaudio
import threading
import queue
from faster_whisper import WhisperModel
from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)
SAMPLE_SIZE = 512

# Initialize Whisper Model
model_size = "Systran/faster-distil-whisper-medium.en"
faster_whisper_model = WhisperModel(model_size, device="cuda", compute_type="bfloat16")

# Shared resources
transcription_queue = queue.Queue()
stop_event = threading.Event()
continue_recording = False
recording_thread = None
audio = None
final_transcription_text = ""
start_transcription_time = 0
cumulative_transcription_time = 0
recording_time_limit = 30.0
temp_transcription_length = 0

# ---------------------------- Helper Functions ----------------------------

def initialize_audio():
    global audio
    if audio is None:
        audio = pyaudio.PyAudio()

def close_audio():
    global audio
    if audio is not None:
        audio.terminate()
        audio = None

def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1 / 32768
    return sound.squeeze()

def transcribe_and_queue(audio_buffer):
    global final_transcription_text

    if len(audio_buffer) == 0:
        transcription_queue.put("No audio data to transcribe.")
        return ""

    transcription = ''
    segments, _ = faster_whisper_model.transcribe(
        audio_buffer,
        task="transcribe",
        language='en',
        vad_filter = True,
        without_timestamps=True
    )
    for segment in segments:
        transcription += segment.text

    transcription_queue.put(transcription)
    final_transcription_text = transcription
    return transcription


# ---------------------------- State Management Functions ----------------------------

def set_recording_state():
    global continue_recording, start_transcription_time, cumulative_transcription_time
    start_transcription_time = time.time()
    continue_recording = True
    cumulative_transcription_time = 0

    # Change the border color back to white when recording stops
    if window:
        window.change_border_color("#EEEEEE")


def reset_recording_state():
    global continue_recording, start_transcription_time, cumulative_transcription_time
    continue_recording = False
    cumulative_transcription_time = 0
    start_transcription_time = 0

    # Change the border color back to white when recording stops
    if window:
        window.change_border_color("#EEEEEE")

# ---------------------------- PyQt Floating Window ----------------------------

class FloatingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transcription")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.8)
        self.setGeometry(1600, 200, 800, 300)

        # Define the initial color used for the text and the border
        self.text_color = "#EEEEEE"
        self.border_color = self.text_color

        # Create the QLabel with the updated style sheet
        self.label = QLabel("Start speaking...", self)
        self.update_label_style()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setFixedSize(800, 300)

        # Timer for updating the transcription text
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_transcription)
        self.timer.start(100)

    def update_label_style(self):
        """Update the style sheet of the QLabel."""
        self.label.setStyleSheet(
            f"""
            color: {self.text_color};
            background-color: #222222;
            font-size: 22px;
            padding: 20px;
            border: 4px solid {self.border_color};
            """
        )

    def change_border_color(self, color: str):
        """Change the color of the border."""
        self.border_color = color
        self.update_label_style()

    def update_transcription(self):
        global continue_recording
        if cumulative_transcription_time >= recording_time_limit:
            continue_recording = False
        try:
            while True:
                transcription = transcription_queue.get_nowait()
                self.label.setText(transcription)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[ERROR] Exception in update_transcription: {e}")

    def closeEvent(self, event):
        """
        Override the close event to ensure transcription stops when the window is closed.
        """
        from main import stt_module  # Avoid circular import
        stt_module.stop_record_and_transcription()
        event.accept()

# ---------------------------- Recording and Control ----------------------------

def start_recording():
    global continue_recording, cumulative_transcription_time, start_transcription_time
    start_transcription_time = time.time()

    initialize_audio()
    continue_recording = True

    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        close_audio()
        return

    audio_data = []
    last_transcription_time = time.time()

    print("Recording started. Speak into the microphone...")
    start_transcription_time = time.time()

    try:
        while continue_recording:
            if stream.is_active():
                audio_chunk = stream.read(SAMPLE_SIZE, exception_on_overflow=False)
                audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_float32 = int2float(audio_int16)
                audio_data.append(audio_float32)

                current_time = time.time()
                cumulative_transcription_time = current_time - start_transcription_time
                if current_time - last_transcription_time >= 1.0:
                    cumulative_audio = np.concatenate(audio_data, axis=0)
                    transcribe_and_queue(cumulative_audio)
                    last_transcription_time = current_time
            else:
                time.sleep(0.1)
    except Exception as e:
        print(f"Recording error: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        close_audio()

        if len(audio_data) > 0:
            final_audio = np.concatenate(audio_data, axis=0)
            transcribe_and_queue(final_audio)
        stop_event.set()
        print("Recording stopped and final transcription completed.")
        print('Final transcription:', final_transcription_text)
        if window:
            window.change_border_color("#AA0000")


def start_record_and_transcription():
    global recording_thread, start_transcription_time, continue_recording

    stop_event.clear()
    initialize_audio()
    set_recording_state()

    # Start the recording thread
    recording_thread = threading.Thread(target=start_recording, daemon=True)
    recording_thread.start()

def stop_record_and_transcription():
    reset_recording_state()
    stop_event.set()

    if recording_thread is not None:
        recording_thread.join()

    close_audio()
    print("Recording stopped.")
    print('start trans time:', start_transcription_time)
    print('cumulative trans time:', cumulative_transcription_time)
    print('continue_recording = ', continue_recording)

# ---------------------------- Window Initialization ----------------------------

window = None

def init_window():
    global window
    if window is None:
        window = FloatingWindow()
