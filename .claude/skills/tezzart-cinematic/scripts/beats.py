"""Find the beat grid and the audible hits in a track, so titles/cuts can land on them.
usage: python3 -I beats.py <audio_or_video>     (needs: pip install librosa; ffmpeg on PATH)"""
import os, subprocess, sys, tempfile
import numpy as np, librosa
src = sys.argv[1]
with tempfile.TemporaryDirectory() as d:
    wav = os.path.join(d, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "22050", "-y", wav], check=True)
    y, sr = librosa.load(wav, sr=22050)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
rms = librosa.feature.rms(y=y, frame_length=sr // 2, hop_length=sr // 2)[0]
print("duration_s", round(len(y) / sr, 3))
print("tempo_bpm", np.round(tempo, 1))
print("beats", np.round(librosa.frames_to_time(beats, sr=sr), 2).tolist())
print("onsets (audible hits — put title slams here)", np.round(onsets, 2).tolist())
print("loudness per 0.5s (dB)", np.round(20 * np.log10(rms + 1e-9), 0).astype(int).tolist())
