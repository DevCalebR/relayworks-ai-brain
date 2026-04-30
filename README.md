# RelayWorks AI Content Brain

RelayWorks AI Content Brain is a local Python pipeline for producing short-form video assets and manually uploading validated runs to YouTube. It can generate scripts with OpenAI, create SRT captions, write YouTube-ready metadata JSON, generate ElevenLabs voiceover audio, build vertical MP4 videos with optional burned-in captions, use local or OpenAI-generated images as the video visual layer, organize run outputs, validate upload readiness, and upload a validated run folder through YouTube OAuth.

The project is intentionally local-first. Generated assets stay on your machine under `outputs/`, OAuth credentials stay local, and uploads must be started manually from an organized run folder. Scheduling, stock footage search, topic research, analytics, and thumbnail generation are not built yet.

## Current Pipeline Status

The pipeline currently supports these CLI modes:

- `script`: generates and saves a script only.
- `captions`: generates a script and SRT captions.
- `metadata`: generates a script and YouTube-ready metadata JSON.
- `voiceover`: generates a script and ElevenLabs audio.
- `test-audio`: creates a local test MP3 without API calls.
- `video`: builds an MP4 from an existing audio file, optionally using burned-in captions and local image inputs.
- `full`: generates a script, captions, metadata, ElevenLabs audio, a burned-in caption video, and optional OpenAI-generated scene images.
- `upload-check`: validates an organized run folder before upload.
- `upload`: uploads `video.mp4` from a validated organized run folder using `metadata.json`.

Common options:

- `--template`: selects the local video style template.
- `--caption-offset`: adjusts generated caption timing in `full` mode.
- `--images-dir`: uses supported local images from a folder.
- `--image-paths`: uses explicit local image file paths.
- `--use-ai-images`: generates OpenAI scene images during `full` mode.
- `--image-count`: controls how many AI scene images to request.
- `--organize`: copies successful run outputs into a timestamped folder under `outputs/runs/`.
- `--run-folder`: points `upload-check` and `upload` modes to an organized run folder under `outputs/runs/`.
- `--privacy-status`: controls YouTube visibility for `upload` mode. Use `private` by default.

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

Create a local `.env` file in the repo root and add your API values. Do not commit `.env`.

## Environment Variables

Expected local `.env` values:

```bash
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
YOUTUBE_API_KEY=your_key_here
YOUTUBE_CLIENT_SECRETS_FILE=client_secret.json
YOUTUBE_TOKEN_FILE=youtube_token.json
YOUTUBE_PRIVACY_STATUS=private
```

- `OPENAI_API_KEY`: required for modes that generate scripts and for OpenAI-generated scene images.
- `ELEVENLABS_API_KEY`: required for modes that generate ElevenLabs audio.
- `ELEVENLABS_VOICE_ID`: required for predictable ElevenLabs voice generation.
- `YOUTUBE_API_KEY`: placeholder for possible future non-upload use. It is not used for uploads.
- `YOUTUBE_CLIENT_SECRETS_FILE`: local OAuth desktop client JSON file path. Default: `client_secret.json`.
- `YOUTUBE_TOKEN_FILE`: local OAuth token cache path created after the first successful browser authorization. Default: `youtube_token.json`.
- `YOUTUBE_PRIVACY_STATUS`: default upload visibility. Default: `private`.

YouTube uploads require OAuth. They do not use `YOUTUBE_API_KEY`.

## YouTube OAuth Setup

Manual upload uses Google OAuth desktop credentials:

1. In Google Cloud Console, create or select a project.
2. Enable the YouTube Data API v3.
3. Configure the OAuth consent screen.
4. Create an OAuth client ID for a desktop app.
5. Download the OAuth client JSON.
6. Save it locally as `client_secret.json` or set `YOUTUBE_CLIENT_SECRETS_FILE` to its local path.

On the first successful upload attempt, the browser OAuth flow opens. After you authorize the correct YouTube account/channel, the pipeline writes `youtube_token.json` locally. Future uploads reuse that token and should not re-open OAuth every time.

Deleting `youtube_token.json` forces a new OAuth authorization flow. If you accidentally authorize the wrong YouTube account or channel, delete `youtube_token.json` and run upload again with the correct account.

`client_secret.json` and `youtube_token.json` must never be committed.

## CLI Usage

Generate a script:

```bash
python main.py --mode script
```

Generate captions:

```bash
python main.py --mode captions
```

Generate metadata:

```bash
python main.py --mode metadata
```

Generate voiceover:

```bash
python main.py --mode voiceover
```

Create local test audio:

```bash
python main.py --mode test-audio
```

Build a video from existing audio:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3
```

Build a captioned video:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt
```

Generate a complete organized run with AI scene images:

```bash
python main.py --mode full --template ai --organize --use-ai-images --image-count 3
```

Validate an organized run folder before upload:

```bash
python main.py --mode upload-check --run-folder outputs/runs/<run-folder-name>
```

Upload a validated run folder privately:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

Use a custom topic with any mode that accepts topic input:

```bash
python main.py --mode script --topic "How small businesses use AI assistants"
```

## Successful Manual Upload Workflow

Generate a complete organized run:

```bash
python main.py --mode full --template ai --organize --use-ai-images --image-count 3
```

Validate the newest run folder:

```bash
python main.py --mode upload-check --run-folder "$(ls -td outputs/runs/*/ | head -1)"
```

Upload privately:

```bash
python main.py --mode upload --run-folder "$(ls -td outputs/runs/*/ | head -1)" --privacy-status private
```

After upload, review the video in YouTube Studio before publishing. Private uploads are visible only in the correct authorized YouTube Studio channel.

## Upload Readiness Checks

`upload-check` validates a run folder before upload. It does not upload anything, call YouTube, require OAuth, or use YouTube API keys.

```bash
python main.py --mode upload-check --run-folder outputs/runs/<run-folder-name>
```

Required files:

- `video.mp4`
- `metadata.json`

Recommended files:

- `captions.srt`
- `script.txt`
- `audio.mp3`
- `images/` when image copying is available

`metadata.json` must be valid JSON and include:

- `title`
- `description`
- `tags`
- `hashtags`
- `topic`
- `generated_from`

`ready: true` means the local package is valid for upload. `ready: false` means the folder is missing required upload files or has invalid metadata.

## Manual YouTube Upload

`upload` uploads `video.mp4` from a validated organized run folder using `metadata.json`.

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

Upload behavior:

- `--run-folder` points to the organized run folder under `outputs/runs/`.
- `--privacy-status` controls YouTube visibility. Valid values are `private`, `unlisted`, and `public`.
- `private` is recommended by default for safety.
- The upload validates the run folder first and stops before OAuth or upload if validation fails.
- The upload uses `title`, `description`, `tags`, and `hashtags` from `metadata.json`.
- Hashtags are appended to the description if they are not already included.
- The upload does not generate scripts, captions, metadata, audio, images, or video.
- The upload uses YouTube OAuth, not `YOUTUBE_API_KEY`.

## OAuth Token Behavior

The first successful browser OAuth flow creates `youtube_token.json` locally at the path configured by `YOUTUBE_TOKEN_FILE`.

`youtube_token.json` lets future uploads reuse authorization without re-opening OAuth every time. If the token expires and has a refresh token, the client refreshes it locally.

Delete `youtube_token.json` when:

- You authorized the wrong Google or YouTube account.
- You need to switch YouTube channels.
- You want to force a fresh OAuth authorization flow.

Keep both OAuth files local:

- `client_secret.json`: downloaded from Google Cloud OAuth desktop credentials.
- `youtube_token.json`: created locally after browser authorization.

## Video Templates

`tools/video_builder.py` creates local vertical MP4 videos and supports these templates:

- `default`
- `bold`
- `minimal`
- `ai`

Select a template with `--template`:

```bash
python main.py --mode full --template ai
```

## Captions

`tools/captions.py` saves generated SRT captions under `outputs/captions/`.

`tools/video_builder.py` can burn captions into generated MP4 videos when a valid SRT file is provided with `--captions-path`.

Caption burn-in is available in:

- `video` mode when `--captions-path` points to an existing `.srt` file.
- `full` mode as part of the generated script, caption, metadata, audio, and video flow.

In `full` mode, generated caption timing can be adjusted with `--caption-offset`. The default offset is `0.5` seconds.

## Image Support

Local images and OpenAI-generated images are used as the main visual layer behind captions and template overlays.

Use explicit local image paths:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --template ai --image-paths /path/to/image1.png /path/to/image2.jpg
```

Use a local image folder:

```bash
python main.py --mode video --audio-path outputs/audio/how-people-are-making-money-with-ai-in-2026-test.mp3 --captions-path outputs/captions/how-people-are-making-money-with-ai-in-2026.srt --template ai --images-dir /path/to/images
```

Supported local image extensions:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

Generate AI scene images in `full` mode:

```bash
python main.py --mode full --template ai --organize --use-ai-images --image-count 3
```

AI image generation uses `OPENAI_API_KEY`, may use extra API credits, and writes generated images to `outputs/images/`.

## Output Folders

Generated outputs are written under `outputs/` and `memory/`:

- `outputs/scripts/`: generated `.txt` scripts.
- `outputs/captions/`: generated `.srt` captions.
- `outputs/metadata/`: generated `.json` metadata files.
- `outputs/audio/`: generated ElevenLabs `.mp3` audio and local test `.mp3` files.
- `outputs/videos/`: generated `.mp4` videos.
- `outputs/images/`: generated OpenAI scene images.
- `outputs/runs/`: timestamped organized copies of successful run outputs.
- `memory/logs.json`: successful generation run log.

A complete organized `full` run can contain:

- `script.txt`
- `captions.srt`
- `metadata.json`
- `audio.mp3`
- `video.mp4`
- `images/` if image copying is implemented

Generated `.txt`, `.srt`, `.json`, `.mp3`, `.mp4`, `.png`, `.jpg`, `.jpeg`, `.webp`, and generated run folders are ignored by Git and should not be committed.

## Logging Behavior

Successful generation pipeline runs are logged to:

```text
memory/logs.json
```

The log file should always contain a JSON array. Failed runs are not logged. `upload-check` is validation-only and `upload` is a manual publishing action, so neither should add local generation pipeline run entries.

Local test log entries should not be committed. Before committing, make sure `memory/logs.json` is still a valid JSON array.

## Security

Never commit:

- `.env`
- `client_secret.json`
- `youtube_token.json`
- any `client_secret*.json`, `credentials*.json`, or `token*.json` file
- generated output files
- generated run folders
- local test log entries in `memory/logs.json`

Credential and token files are ignored by Git, but still check staging before every commit.

## Troubleshooting

If `upload` fails with `--run-folder is required`, pass an organized run folder:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

If `upload-check` fails, confirm the run folder contains `video.mp4` and `metadata.json`.

If `upload` cannot find `client_secret.json`, download OAuth desktop credentials from Google Cloud and save the file locally, or update `YOUTUBE_CLIENT_SECRETS_FILE`.

If `youtube_token.json` is missing on the first upload, that is normal. The browser OAuth flow should open and create it after successful authorization.

If the browser OAuth flow opens, authorize the exact Google account and YouTube channel you want to upload to.

If you accidentally authorize the wrong YouTube channel or account, delete `youtube_token.json` and run upload again.

If a private video is not visible, confirm you are viewing the correct YouTube Studio channel for the account used during OAuth.

If an upload fails and you are checking `YOUTUBE_API_KEY`, remember that uploads do not use `YOUTUBE_API_KEY`; they require OAuth.

If credential or token files appear in ignored status, that is expected. They must remain ignored and unstaged.

If generated files do not appear in `git status`, that is expected. Generated outputs, generated image files, and generated run folders are ignored by Git.

If `memory/logs.json` errors during logging, make sure the file contains valid JSON and that the top-level value is an array.

## Current Limitations / Not Built Yet

- No thumbnail generation/support yet.
- No automatic custom thumbnail upload yet.
- No scheduling yet.
- No stock footage search yet.
- No topic research yet.
- No analytics yet.
- No automatic performance feedback loop yet.

## Suggested Next Milestones

- Add thumbnail generation/support.
- Add thumbnail upload support.
- Improve image prompt quality.
- Add stock footage or background media search.
- Add topic research.
- Add scheduling.
- Add analytics and performance logging.
