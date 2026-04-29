# RelayWorks AI Content Brain

RelayWorks AI Content Brain is a local Python pipeline for generating short-form video assets. It can create a script with OpenAI, generate SRT captions, produce an ElevenLabs voiceover, build a simple vertical MP4 with optional burned-in captions, create local test audio, organize successful run outputs, and log successful runs to `memory/logs.json`.

The current project is intentionally local-first. It is focused on the local asset-generation pipeline only.

## Current Pipeline Status

The pipeline currently supports these CLI modes:

- `script`: generates and saves a script only.
- `captions`: generates a script and SRT captions.
- `voiceover`: generates a script and ElevenLabs audio.
- `test-audio`: creates a local test MP3 without API calls.
- `video`: builds an MP4 from an existing audio file, optionally with burned-in captions when `--captions-path` is provided.
- `full`: generates a script, captions, ElevenLabs audio, a burned-in caption video, and logs the run.

The pipeline also supports:

- `--captions-path`: supplies an existing `.srt` file for `video` mode so captions can be burned into the generated MP4.
- `--organize`: copies successful run outputs into a timestamped folder under `outputs/runs/`.

The default topic is:

```text
How people are making money with AI in 2026
```

You can override it with `--topic "your topic here"` for modes that generate topic-based assets.

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
- `ELEVENLABS_VOICE_ID`: required for ElevenLabs voice generation. It must match a valid voice available to the configured ElevenLabs account.
- `YOUTUBE_API_KEY`: placeholder for future use. The current pipeline does not upload to YouTube.

Never commit real API keys, private values, or `.env`.

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

Create a local test MP3 without OpenAI or ElevenLabs API calls:

```bash
python main.py --mode test-audio
```

Build a vertical MP4 from an existing audio file:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

Build a vertical MP4 from an existing audio file and burn in captions from an existing SRT file:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt
```

Run the full local pipeline:

```bash
python main.py --mode full
```

Run the full local pipeline and organize successful outputs into a timestamped run folder:

```bash
python main.py --mode full --organize
```

Generate captions and organize successful outputs into a timestamped run folder:

```bash
python main.py --mode captions --organize
```

Build a captioned video from existing audio and captions, then organize successful outputs into a timestamped run folder:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --organize
```

Use a custom topic with any mode that accepts the topic as input:

```bash
python main.py --mode script --topic "How small businesses use AI assistants"
```

## Burned-In Captions

`tools/captions.py` saves generated SRT captions under `outputs/captions/`.

`tools/video_builder.py` can burn captions into generated MP4 videos when a valid SRT file is provided with `--captions-path`.

Caption burn-in is available in:

- `video` mode when `--captions-path` points to an existing `.srt` file.
- `full` mode as part of the generated script, caption, audio, and video flow.

If `--captions-path` is not provided in `video` mode, the video is built from the audio file without burned-in captions.

## Run-Folder Organization

The optional `--organize` flag copies successful run outputs into a timestamped folder under:

```text
outputs/runs/
```

Run-folder organization is handled by `tools/run_folder.py`. It copies the outputs from the successful command into a run-specific folder so the generated assets for that run can be reviewed together.

The original generated files remain in their standard output folders. The run folder is an organized copy, not the only location where the generated assets are stored.

Generated run folders are ignored by Git and should not be committed. The placeholder file `outputs/runs/.gitkeep` should stay tracked so the folder exists in fresh clones.

## Output Folders

Generated outputs are written under `outputs/`:

- `outputs/scripts/`: generated `.txt` scripts from `tools/file_writer.py`.
- `outputs/captions/`: generated `.srt` captions from `tools/captions.py`.
- `outputs/audio/`: generated ElevenLabs `.mp3` audio from `tools/voiceover.py` and local test `.mp3` files from `tools/test_audio.py`.
- `outputs/videos/`: generated `.mp4` videos from `tools/video_builder.py`.
- `outputs/runs/`: timestamped organized copies of successful run outputs from `tools/run_folder.py`.

Generated `.txt`, `.srt`, `.mp3`, `.mp4`, and generated run folders are ignored by Git and should not be committed.

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

Failed runs are not logged. Local test log entries should not be committed. Before committing, make sure `memory/logs.json` is still a valid JSON array and that local test entries are not staged.

## Troubleshooting

If `script`, `captions`, `voiceover`, or `full` fails with an OpenAI API error, confirm `OPENAI_API_KEY` is set in `.env`.

If `voiceover` or `full` fails with an ElevenLabs API error, confirm `ELEVENLABS_API_KEY` is set in `.env`.

If ElevenLabs audio generation fails because the voice cannot be found or used, confirm `ELEVENLABS_VOICE_ID` is set and matches a valid voice available to the configured ElevenLabs account.

If `video` mode fails with a missing audio path, provide `--audio-path` pointing to an existing `.mp3` file.

If caption burn-in fails, confirm `--captions-path` points to an existing valid `.srt` file.

If generated files do not appear in `git status`, that is expected. Generated outputs and generated run folders are ignored by Git.

If `memory/logs.json` errors during logging, make sure the file contains valid JSON and that the top-level value is an array.

If you want to test video creation without API calls, run:

```bash
python main.py --mode test-audio
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

## Current Limitations / Not Built Yet

- No YouTube upload yet.
- No stock footage yet.
- No scheduling yet.
- No topic research yet.
- No analytics yet.
