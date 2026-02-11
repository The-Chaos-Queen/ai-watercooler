"""
voice_input.py — Speech-to-Text using faster-whisper
Records from microphone and transcribes locally using Whisper.

Usage:
    python voice_input.py                  # Record until Enter is pressed, then transcribe
    python voice_input.py path/to/audio.mp3  # Transcribe an existing audio file

Requirements:
    pip install faster-whisper sounddevice soundfile
"""

import sys
import time
import threading
from pathlib import Path

# Check for required packages
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("[ERROR] faster-whisper not installed. Run: pip install faster-whisper")
    sys.exit(1)


# --- Configuration ---
MODEL_SIZE = "base"       # Options: tiny, base, small, medium, large-v3
DEVICE = "auto"           # auto, cpu, cuda
COMPUTE_TYPE = "int8"     # int8 (fast, good enough), float16 (GPU), float32 (CPU fallback)
LANGUAGE = None           # None = auto-detect, or "en", "de", etc.
SAMPLE_RATE = 16000


def transcribe_file(filepath: str, model_size: str = MODEL_SIZE) -> str:
    """Transcribe an audio file and return the text."""
    print(f"[WHISPER] Loading model '{model_size}'...")
    model = WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)
    
    print(f"[WHISPER] Transcribing: {filepath}")
    start = time.time()
    
    segments, info = model.transcribe(
        filepath,
        language=LANGUAGE,
        beam_size=5,
        vad_filter=True,        # Voice Activity Detection - skips silence
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )
    
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())
        print(f"  [{segment.start:.1f}s - {segment.end:.1f}s] {segment.text.strip()}")
    
    elapsed = time.time() - start
    full_text = " ".join(text_parts)
    
    print(f"\n[WHISPER] Done in {elapsed:.1f}s")
    print(f"[WHISPER] Language detected: {info.language} ({info.language_probability:.0%})")
    print(f"\n--- Full Transcription ---")
    print(full_text)
    
    return full_text


def record_and_transcribe(model_size: str = MODEL_SIZE):
    """Record from microphone, then transcribe."""
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        print("[ERROR] Recording requires: pip install sounddevice soundfile")
        print("[TIP] You can also transcribe existing files: python voice_input.py path/to/audio.mp3")
        sys.exit(1)
    
    import numpy as np
    
    print("[MIC] Recording... Press Enter to stop.")
    
    recording = []
    is_recording = True
    
    def callback(indata, frames, time_info, status):
        if is_recording:
            recording.append(indata.copy())
    
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32',
        callback=callback,
    )
    
    with stream:
        input()  # Wait for Enter
        is_recording = False
    
    if not recording:
        print("[MIC] No audio recorded.")
        return ""
    
    audio_data = np.concatenate(recording, axis=0)
    
    # Save to temp file
    temp_path = Path("_temp_recording.wav")
    sf.write(str(temp_path), audio_data, SAMPLE_RATE)
    print(f"[MIC] Recorded {len(audio_data)/SAMPLE_RATE:.1f}s of audio.")
    
    # Transcribe
    result = transcribe_file(str(temp_path), model_size)
    
    # Cleanup
    temp_path.unlink(missing_ok=True)
    
    return result


def main():
    args = sys.argv[1:]
    
    if args:
        # Transcribe existing file
        filepath = args[0]
        if not Path(filepath).exists():
            print(f"[ERROR] File not found: {filepath}")
            sys.exit(1)
        transcribe_file(filepath)
    else:
        # Record from microphone
        record_and_transcribe()


if __name__ == "__main__":
    main()
