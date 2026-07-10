# App assets

`tutorial_walkthrough.wav` is narrated from `tutorial_transcript.md` using the
speech synthesizer built into Windows, so the walkthrough can be regenerated
offline whenever the transcript changes:

```powershell
$text = (Get-Content app/assets/tutorial_transcript.md -Raw) -replace '(?s)^.*?---', ''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.SetOutputToWaveFile("app/assets/tutorial_walkthrough.wav")
$synth.Speak(($text -replace '\s+', ' ').Trim())
$synth.Dispose()
```

The transcript is the source of truth and doubles as the accessible text
version shown in the interface.
