# RelayWorks AI Content Brain

RelayWorks AI Content Brain is a local Python pipeline for generating short-form video assets. It can create a script with OpenAI, generate SRT captions, produce an ElevenLabs voiceover, build a simple vertical MP4, create local test audio, and log successful runs to `memory/logs.json`.

The current project is intentionally local-first. It does not upload to YouTube, schedule posts, add stock footage, burn captions into video, run analytics, or perform topic research.

## Current Pipeline Status

The pipeline currently supports these CLI modes:

- `script`: generates and saves a script only.
- `captions`: generates a script and SRT captions.
- `voiceover`: generates a script and ElevenLabs audio.
- `test-audio`: creates a local test MP3 without API calls.
- `video`: builds an MP4 from an existing audio file.
- `full`: generates script, captions, audio, video, and logs the run.

The default topic is:

```text
How people are making money with AI in 2026
```

You can override it with `--topic "your topic here"`.

## Local Setup On Mac

From the repo root:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then add your local API values to `.env`.

Do not commit `.env`.

## Environment Variables

`.env.example` documents the expected variables:

```bash
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
YOUTUBE_API_KEY=your_key_here
```

- `OPENAI_API_KEY`: required for modes that generate scripts: `script`, `captions`, `voiceover`, and `full`.
- `ELEVENLABS_API_KEY`: required for modes that generate ElevenLabs audio: `voiceover` and `full`.
- `ELEVENLABS_VOICE_ID`: optional voice selection for ElevenLabs. The code keeps a fallback voice if this is missing.
- `YOUTUBE_API_KEY`: placeholder for future use. The current pipeline does not upload to YouTube.

Never commit real API keys, real private values, or `.env`.

## CLI Usage

Generate and save a script only:

```bash
python main.py --mode script
```

Generate a script and SRT captions:

```bash
python main.py --mode captions
```

Generate a script and ElevenLabs voiceover:

```bash
python main.py --mode voiceover
```

Create a local test MP3 without OpenAI or ElevenLabs:

```bash
python main.py --mode test-audio
```

Build a vertical MP4 from an existing audio file:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

Run the full local pipeline:

```bash
python main.py --mode full
```

Use a custom topic with any mode that accepts the topic as input:

```bash
python main.py --mode script --topic "How small businesses use AI assistants"
```

## Output Folders

Generated outputs are written under `outputs/`:

- `outputs/scripts/`: generated `.txt` scripts.
- `outputs/captions/`: generated `.srt` caption files.
- `outputs/audio/`: generated ElevenLabs or local test `.mp3` audio.
- `outputs/videos/`: generated `.mp4` videos.

Generated `.txt`, `.srt`, `.mp3`, and `.mp4` files are ignored by Git and should not be committed.

## Logging Behavior

Successful CLI runs are logged to:

```text
memory/logs.json
```

The log file should always contain a JSON array. Each successful run appends one entry with:

- `timestamp`
- `topic`
- `mode`
- `outputs`

Example shape:

```json
[
  {
    "timestamp": "2026-04-28T12:00:00+00:00",
    "topic": "How people are making money with AI in 2026",
    "mode": "test-audio",
    "outputs": {
      "audio": "outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3"
    }
  }
]
```

Failed runs are not logged. Local test log entries should not be committed. Before committing, reset `memory/logs.json` back to:

```json
[]
```

## Troubleshooting

If `script`, `captions`, `voiceover`, or `full` fails with an OpenAI API error, confirm `OPENAI_API_KEY` is set in `.env`.

If `voiceover` or `full` fails with an ElevenLabs error, confirm `ELEVENLABS_API_KEY` is set and that your ElevenLabs account, plan, and voice ID can generate audio.

If you want to test video creation without API calls, run:

```bash
python main.py --mode test-audio
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

If `video` mode fails with a missing audio path, provide `--audio-path` pointing to an existing `.mp3` file.

If `memory/logs.json` errors during logging, make sure the file contains valid JSON and that the top-level value is an array.
