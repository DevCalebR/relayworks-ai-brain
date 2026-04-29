# RelayWorks AI Content Brain

RelayWorks AI Content Brain is a local Python pipeline for generating short-form video assets. It can create a script with OpenAI, generate SRT captions, create YouTube-ready metadata JSON, produce an ElevenLabs voiceover, build a simple vertical MP4 with optional burned-in captions, create local test audio, organize successful run outputs, and log successful runs to `memory/logs.json`.

The current project is intentionally local-first. It prepares assets for a future YouTube workflow, but it does not upload, schedule, research topics, add stock footage, or analyze performance yet.

## Current Pipeline Status

The pipeline currently supports these CLI modes:

- `script`: generates and saves a script only.
- `captions`: generates a script and SRT captions.
- `metadata`: generates a script and YouTube-ready metadata JSON.
- `voiceover`: generates a script and ElevenLabs audio.
- `test-audio`: creates a local test MP3 without API calls.
- `video`: builds an MP4 from an existing audio file, optionally with burned-in captions when `--captions-path` is provided.
- `full`: generates a script, captions, metadata, ElevenLabs audio, a burned-in caption video, and logs the run.

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

- `OPENAI_API_KEY`: required for modes that generate scripts: `script`, `captions`, `metadata`, `voiceover`, and `full`.
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

Generate a script and local YouTube-ready metadata JSON:

```bash
python main.py --mode metadata
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

Generate metadata and organize successful outputs into a timestamped run folder:

```bash
python main.py --mode metadata --organize
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

## Metadata Generation

`metadata` mode generates a script and saves a local YouTube-ready metadata JSON file under:

```text
outputs/metadata/
```

Metadata files are created by `tools/metadata.py` and include:

- `title`
- `description`
- `tags`
- `hashtags`
- `topic`
- `generated_from`

The metadata is local only for now. It prepares the project for future YouTube upload work, but it does not upload anything, authenticate with YouTube, or schedule publishing.

Generated metadata JSON files are ignored by Git and should not be committed. The placeholder file `outputs/metadata/.gitkeep` should stay tracked so the folder exists in fresh clones.

## Burned-In Captions

`tools/captions.py` saves generated SRT captions under `outputs/captions/`.

`tools/video_builder.py` can burn captions into generated MP4 videos when a valid SRT file is provided with `--captions-path`.

Caption burn-in is available in:

- `video` mode when `--captions-path` points to an existing `.srt` file.
- `full` mode as part of the generated script, caption, metadata, audio, and video flow.

If `--captions-path` is not provided in `video` mode, the video is built from the audio file without burned-in captions.

## Run-Folder Organization

The optional `--organize` flag copies successful run outputs into a timestamped folder under:

```text
outputs/runs/
```

Run-folder organization is handled by `tools/run_folder.py`. It copies the outputs from the successful command into a run-specific folder so the generated assets for that run can be reviewed together.

The original generated files remain in their standard output folders. The run folder is an organized copy, not the only location where the generated assets are stored.

Organized full runs can contain:

- `script.txt`
- `captions.srt`
- `metadata.json`
- `audio.mp3`
- `video.mp4`

Generated run folders are ignored by Git and should not be committed. The placeholder file `outputs/runs/.gitkeep` should stay tracked so the folder exists in fresh clones.

## Output Folders

Generated outputs are written under `outputs/` and `memory/`:

- `outputs/scripts/`: generated `.txt` scripts from `tools/file_writer.py`.
- `outputs/captions/`: generated `.srt` captions from `tools/captions.py`.
- `outputs/metadata/`: generated `.json` metadata files from `tools/metadata.py`.
- `outputs/audio/`: generated ElevenLabs `.mp3` audio from `tools/voiceover.py` and local test `.mp3` files from `tools/test_audio.py`.
- `outputs/videos/`: generated `.mp4` videos from `tools/video_builder.py`.
- `outputs/runs/`: timestamped organized copies of successful run outputs from `tools/run_folder.py`.
- `memory/logs.json`: successful run log maintained by `tools/logger.py`.

Generated `.txt`, `.srt`, `.json`, `.mp3`, `.mp4`, and generated run folders are ignored by Git and should not be committed.

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
    "mode": "metadata",
    "outputs": {
      "script": "outputs/scripts/how_people_are_making_money_with_ai_in_2026.txt",
      "metadata": "outputs/metadata/how-people-are-making-money-with-ai-in-2026.json"
    }
  }
]
```

Failed runs are not logged. Local test log entries should not be committed. Before committing, make sure `memory/logs.json` is still a valid JSON array and that local test entries are not staged.

## Troubleshooting

If `script`, `captions`, `metadata`, `voiceover`, or `full` fails with an OpenAI API error, confirm `OPENAI_API_KEY` is set in `.env`.

If `voiceover` or `full` fails with an ElevenLabs API error, confirm `ELEVENLABS_API_KEY` is set in `.env`.

If ElevenLabs audio generation fails because the voice cannot be found or used, confirm `ELEVENLABS_VOICE_ID` is set and matches a valid voice available to the configured ElevenLabs account.

If `video` mode fails with a missing audio path, provide `--audio-path` pointing to an existing `.mp3` file.

If caption burn-in fails, confirm `--captions-path` points to an existing valid `.srt` file.

If generated metadata JSON files do not appear in `git status`, that is expected. Files under `outputs/metadata/*.json` are ignored by Git.

If generated files do not appear in `git status`, that is expected. Generated outputs and generated run folders are ignored by Git.

If `memory/logs.json` errors during logging, make sure the file contains valid JSON and that the top-level value is an array.

If you want to test video creation without API calls, run:

```bash
python main.py --mode test-audio
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

## Current Limitations / Not Built Yet

- No YouTube upload yet.
- No YouTube OAuth yet.
- No stock footage yet.
- No scheduling yet.
- No topic research yet.
- No analytics yet.
- No automatic performance feedback loop yet.

## Suggested Next Milestones

These are future options only and are not implemented yet:

- Improve video styling/templates.
- Add stock footage or background media.
- Add topic research.
- Add YouTube upload preparation checks.
- Add YouTube OAuth and upload.
- Add scheduling.
- Add analytics and performance logging.
