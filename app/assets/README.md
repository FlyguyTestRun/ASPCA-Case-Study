# App assets

## Audio walkthrough

`tutorial_walkthrough.wav` is the narrated tour played by the review app's
sidebar toggle. `tutorial_transcript.md` is its source of truth and doubles
as the accessible text version shown in the interface.

### Recording the narration (preferred)

The current file is a synthesized placeholder. To replace it with a human
recording:

1. Open `tutorial_transcript.md` and read everything below the `---` line.
   It runs about 90 seconds at a comfortable pace.
2. Record in a quiet room on any decent microphone (a phone voice-memo app
   is fine). One take is enough; conversational beats polished.
3. Save or convert to WAV or MP3 and drop it in this folder as
   `tutorial_walkthrough.wav` (or `.mp3`, and update the file name in
   `app/review_app.py`).
4. Optional cleanup with ffmpeg, normalizing loudness and trimming silence:

```
ffmpeg -i raw_recording.m4a -af "loudnorm=I=-16:TP=-1.5,silenceremove=start_periods=1:start_threshold=-45dB" -ar 22050 -ac 1 tutorial_walkthrough.wav
```

If the transcript changes, re-record; the transcript and the audio must say
the same thing.

### Synthesized fallback

The placeholder was generated offline with the speech synthesizer built into
Windows, so a stand-in can always be regenerated without any account or
network access:

```powershell
$text = (Get-Content app/assets/tutorial_transcript.md -Raw) -split '---', 2 | Select-Object -Last 1
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.SetOutputToWaveFile("app/assets/tutorial_walkthrough.wav")
$synth.Speak((($text -replace '\s+', ' ')).Trim())
$synth.Dispose()
```
