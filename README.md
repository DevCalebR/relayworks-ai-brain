# RelayWorks AI Content Brain

RelayWorks AI Content Brain is a local Python pipeline for generating short-form video assets. It can create a script with OpenAI, generate SRT captions, create YouTube-ready metadata JSON, produce an ElevenLabs voiceover, build a simple vertical MP4 with optional burned-in captions, use local or OpenAI-generated images as the main video visual layer, create local test audio, organize successful run outputs, validate upload readiness, manually upload a validated run folder to YouTube, and log successful generation runs to `memory/logs.json`.

The project is intentionally local-first. It can perform a manual OAuth-based YouTube upload from an existing organized run folder, but it does not schedule, research topics, add stock footage, download internet images, or analyze performance yet.

## Current Pipeline Status

The pipeline currently supports these CLI modes:

- `script`: generates and saves a script only.
- `captions`: generates a script and SRT captions.
- `metadata`: generates a script and YouTube-ready metadata JSON.
- `voiceover`: generates a script and ElevenLabs audio.
- `test-audio`: creates a local test MP3 without API calls.
- `video`: builds an MP4 from an existing audio file, optionally using burned-in captions and local image inputs.
- `full`: generates a script, captions, metadata, ElevenLabs audio, a burned-in caption video, and optional OpenAI-generated scene images.
- `upload-check`: validates an organized run folder before manual upload.
- `upload`: manually uploads `video.mp4` from an organized run folder using `metadata.json` after upload-check validation passes.

The pipeline also supports:

- `--template`: selects a built-in local video template.
- `--captions-path`: supplies an existing `.srt` file for `video` mode so captions can be burned into the generated MP4.
- `--images-dir`: uses supported local images from a folder.
- `--image-paths`: uses explicit local image file paths.
- `--use-ai-images`: generates OpenAI scene images during `full` mode.
- `--image-count`: controls how many AI scene images to request.
- `--organize`: copies successful run outputs into a timestamped folder under `outputs/runs/`.
- `--template`: selects the local video style template.
- `--caption-offset`: adjusts generated caption timing in `full` mode.
- `--run-folder`: points `upload-check` and `upload` modes at an organized run folder.
- `--privacy-status`: sets YouTube upload visibility for `upload` mode. Defaults to `private`.

The default topic is:

```text
How people are making money with AI in 2026
```

You can override it with `--topic "your topic here"` for modes that generate topic-based assets.

## Local Setup On Mac

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file in the repo root and add your API values.

Do not commit `.env`.

## Environment Variables

Required local `.env` variables:

```bash
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
YOUTUBE_API_KEY=your_key_here
YOUTUBE_CLIENT_SECRETS_FILE=client_secret.json
YOUTUBE_TOKEN_FILE=youtube_token.json
YOUTUBE_PRIVACY_STATUS=private
```

- `OPENAI_API_KEY`: required for modes that generate scripts and for OpenAI-generated scene images: `script`, `captions`, `metadata`, `voiceover`, `full`, and `full --use-ai-images`.
- `ELEVENLABS_API_KEY`: required for modes that generate ElevenLabs audio: `voiceover` and `full`.
- `ELEVENLABS_VOICE_ID`: required for predictable ElevenLabs voice generation. It must match a valid voice available to the configured ElevenLabs account.
- `YOUTUBE_API_KEY`: placeholder for future non-upload use. YouTube uploads use OAuth, not this API key.
- `YOUTUBE_CLIENT_SECRETS_FILE`: local OAuth client secret file path for manual YouTube uploads. Do not commit this file.
- `YOUTUBE_TOKEN_FILE`: local OAuth token cache path for manual YouTube uploads. Do not commit this file.
- `YOUTUBE_PRIVACY_STATUS`: default upload visibility. Defaults to `private`.

Never commit real API keys, private values, OAuth client secrets, OAuth tokens, or `.env`.

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

Build a captioned video with explicit local image files:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --template ai --image-paths /path/to/image1.png /path/to/image2.jpg
```

Build a captioned video with supported local images from a folder:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --template ai --images-dir /path/to/images
```

Run the full local pipeline:

```bash
python main.py --mode full
```

Run the full local pipeline with the AI template and organized outputs:

```bash
python main.py --mode full --template ai --organize
```

Run the full local pipeline with OpenAI-generated scene images:

```bash
python main.py --mode full --template ai --organize --use-ai-images
```

Request fewer AI scene images for cheaper testing:

```bash
python main.py --mode full --template ai --organize --use-ai-images --image-count 3
```

Request more AI scene images for better visual variety:

```bash
python main.py --mode full --template ai --organize --use-ai-images --image-count 5
```

Check whether an organized run folder has the files expected for future upload:

```bash
python main.py --mode upload-check --run-folder outputs/runs/<run-folder-name>
```

Upload a validated organized run folder to YouTube as a private video:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name>
```

Upload with an explicit privacy status:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

Use a custom topic with any mode that accepts the topic as input:

```bash
python main.py --mode script --topic "How small businesses use AI assistants"
```

## Video Templates

`tools/video_builder.py` creates local vertical MP4 videos and supports these templates:

- `default`
- `bold`
- `minimal`
- `ai`

Select a template with `--template`, for example:

```bash
python main.py --mode full --template ai
```

## Caption Behavior

`tools/captions.py` saves generated SRT captions under `outputs/captions/`.

`tools/video_builder.py` can burn captions into generated MP4 videos when a valid SRT file is provided with `--captions-path`.

Caption burn-in is available in:

- `video` mode when `--captions-path` points to an existing `.srt` file.
- `full` mode as part of the generated script, caption, metadata, audio, and video flow.

If `--captions-path` is not provided in `video` mode, the video is built from the audio file without burned-in captions.

In `full` mode, generated caption timing can be adjusted with `--caption-offset`. The default offset is `0.5` seconds.

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

## Local Image Support

Local image inputs let `video` mode use existing images as the main visual layer behind captions and template overlays.

Use `--image-paths` when you want exact control over the files:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --template ai --image-paths /path/to/image1.png /path/to/image2.jpg
```

Use `--images-dir` when you want the pipeline to collect supported image files from a folder:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --template ai --images-dir /path/to/images
```

Supported local image extensions are:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

Local images are not uploaded anywhere. They are used locally by the video builder as visual backgrounds.

## OpenAI-Generated Image Support

`full` mode can generate scene images with OpenAI when `--use-ai-images` is provided. AI-generated images are used as the main visual layer behind captions and template overlays.

```bash
python main.py --mode full --template ai --organize --use-ai-images
```

`--image-count` controls how many AI scene images to request:

```bash
python main.py --mode full --template ai --organize --use-ai-images --image-count 3
python main.py --mode full --template ai --organize --use-ai-images --image-count 5
```

- AI image generation uses `OPENAI_API_KEY`.
- AI image generation may use extra API credits.
- Use `--image-count 3` for cheaper testing.
- Use `--image-count 5` for better visual variety.
- AI images are generated locally into `outputs/images/`.
- No stock media search is built yet.
- No internet image downloads are built yet.

## Video Templates

The `--template` option selects a built-in local video template. Templates control the visual treatment used by `tools/video_builder.py`, including the look of the generated vertical video and overlays.

Example:

```bash
python main.py --mode full --template ai --organize
```

Image inputs and AI-generated images work as the main visual layer behind the selected template's captions and overlays.

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

A complete organized `full` run should contain:

- `script.txt`
- `captions.srt`
- `metadata.json`
- `audio.mp3`
- `video.mp4`
- `images/` if image copying is implemented

Generated run folders are ignored by Git and should not be committed. The placeholder file `outputs/runs/.gitkeep` should stay tracked so the folder exists in fresh clones.

## Upload Readiness Checks

`upload-check` mode validates an organized run folder before manual YouTube upload:

```bash
python main.py --mode upload-check --run-folder outputs/runs/<run-folder-name>
```

`upload-check` does not upload anything, does not call YouTube, does not require OAuth, and does not require YouTube API keys.

Required files:

- `video.mp4`
- `metadata.json`

Recommended files:

- `captions.srt`
- `script.txt`
- `audio.mp3`

`metadata.json` must be valid JSON and include:

- `title`
- `description`
- `tags`
- `hashtags`
- `topic`
- `generated_from`

`title` and `description` must be non-empty strings. `tags` and `hashtags` must be lists. `video.mp4` must exist, be non-empty, and have a readable duration greater than zero when local MoviePy validation can read it.

`ready: true` means the local package is valid for future upload work. `ready: false` means the folder is missing required upload files or has invalid metadata.

## Manual YouTube Upload

`upload` mode uploads an existing organized run folder to YouTube. It does not generate a script, captions, metadata, audio, images, or video.

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name>
```

Before uploading, `upload` mode runs the same validation as `upload-check`. If the run folder is not ready, the command fails before starting OAuth or uploading anything.

Upload requirements:

- `video.mp4`
- `metadata.json`
- local OAuth client secret file from `YOUTUBE_CLIENT_SECRETS_FILE`
- local OAuth token file from `YOUTUBE_TOKEN_FILE`, created on first successful OAuth flow

`metadata.json` supplies the YouTube title, description, tags, and hashtags. Hashtags are appended to the description when they are not already included.

Uploads use OAuth 2.0 installed app flow and the YouTube Data API. `YOUTUBE_API_KEY` is not used for uploads.

Uploads default to `private` for safety. You can override this with:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

Valid privacy status values are `private`, `unlisted`, and `public`.

OAuth client secret files and token files are local credentials and must not be committed.

## Output Folders

Generated outputs are written under `outputs/` and `memory/`:

- `outputs/scripts/`: generated `.txt` scripts from `tools/file_writer.py`.
- `outputs/captions/`: generated `.srt` captions from `tools/captions.py`.
- `outputs/metadata/`: generated `.json` metadata files from `tools/metadata.py`.
- `outputs/audio/`: generated ElevenLabs `.mp3` audio from `tools/voiceover.py` and local test `.mp3` files from `tools/test_audio.py`.
- `outputs/videos/`: generated `.mp4` videos from `tools/video_builder.py`.
- `outputs/images/`: generated OpenAI scene images from `tools/image_generator.py`.
- `outputs/runs/`: timestamped organized copies of successful run outputs from `tools/run_folder.py`.
- `memory/logs.json`: successful run log maintained by `tools/logger.py`.

`outputs/images/` stores generated AI scene images. Generated image files should not be committed. The placeholder file `outputs/images/.gitkeep` should stay tracked if present so the folder exists in fresh clones.

Generated `.txt`, `.srt`, `.json`, `.mp3`, `.mp4`, `.png`, `.jpg`, `.jpeg`, `.webp`, and generated run folders are ignored by Git and should not be committed.

## Logging Behavior

Successful pipeline runs are logged to:

```text
memory/logs.json
```

The log file should always contain a JSON array. Each successful pipeline run appends one entry with:

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

Failed runs are not logged. `upload-check` is validation-only and `upload` is a manual publishing action, so neither should add local generation pipeline run entries. Local test log entries should not be committed. Before committing, make sure `memory/logs.json` is still a valid JSON array and that local test entries are not staged.

## Troubleshooting

If `script`, `captions`, `metadata`, `voiceover`, or `full` fails with an OpenAI API error, confirm `OPENAI_API_KEY` is set in `.env`.

If `full --use-ai-images` fails with an OpenAI API error, confirm `OPENAI_API_KEY` is set in `.env` and the account has access to image generation.

If `voiceover` or `full` fails with an ElevenLabs API error, confirm `ELEVENLABS_API_KEY` is set in `.env`.

If ElevenLabs audio generation fails because the voice cannot be found or used, confirm `ELEVENLABS_VOICE_ID` is set and matches a valid voice available to the configured ElevenLabs account.

If `--image-count` fails validation, use a value greater than `0`. Use `3` for cheaper testing and `5` for better visual variety.

If local image inputs fail, confirm each `--image-paths` value points to an existing supported file: `.jpg`, `.jpeg`, `.png`, or `.webp`.

If `--images-dir` produces no images, confirm the folder exists and contains at least one supported image file.

If `video` mode fails with a missing audio path, provide `--audio-path` pointing to an existing `.mp3` file.

If caption burn-in fails, confirm `--captions-path` points to an existing valid `.srt` file.

If `upload-check` fails immediately, confirm `--run-folder` points to an existing organized run folder under `outputs/runs/`.

If `upload` fails before OAuth, run `python main.py --mode upload-check --run-folder outputs/runs/<run-folder-name>` and fix the reported validation errors.

If `upload` cannot find OAuth client secrets, confirm `YOUTUBE_CLIENT_SECRETS_FILE` points to a local Google OAuth client JSON file.

If `upload` starts OAuth for the first time, complete the browser flow. The resulting token is saved locally to `YOUTUBE_TOKEN_FILE` and should not be committed.

If generated files do not appear in `git status`, that is expected. Generated outputs, generated image files, and generated run folders are ignored by Git.

If `memory/logs.json` errors during logging, make sure the file contains valid JSON and that the top-level value is an array.

If you want to test video creation without API calls, run:

```bash
python main.py --mode test-audio
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

## Current Limitations / Not Built Yet

- No automatic YouTube upload yet.
- No stock footage search yet.
- No internet image download pipeline yet.
- No scheduling yet.
- No topic research yet.
- No analytics yet.
- No automatic performance feedback loop yet.

## Suggested Next Milestones

These are future options only and are not implemented yet:

- Test and tune AI image prompt quality.
- Document recommended templates/settings.
- Add automated YouTube upload workflow controls.
- Add stock footage or background media search.
- Add topic research.
- Add scheduling.
- Add analytics and performance logging.
- Add automatic performance feedback loop.
