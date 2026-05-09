# RelayWorks AI Content Brain

RelayWorks AI Content Brain is a local Python pipeline for producing episode-style video assets and manually uploading validated runs to YouTube. It can generate scripts with OpenAI, create SRT captions, write YouTube-ready metadata JSON, generate ElevenLabs voiceover audio, build landscape or vertical MP4 videos with optional burned-in captions, generate local YouTube-ready thumbnails, use local or OpenAI-generated images as the video visual layer, organize run outputs, validate upload readiness, and upload a validated run folder through YouTube OAuth.

The project is intentionally local-first. Generated assets stay on your machine under `outputs/`, OAuth credentials stay local, and uploads must be started manually from an organized run folder. Scheduling, stock footage search, external trend data, analytics, and automatic publishing are not built yet.

## Current Pipeline Status

The pipeline currently supports these CLI modes:

- `script`: generates and saves a script only.
- `captions`: generates a script and SRT captions.
- `metadata`: generates a script and YouTube-ready metadata JSON.
- `voiceover`: generates a script and ElevenLabs audio.
- `test-audio`: creates a local test MP3 without API calls.
- `video`: builds an MP4 from an existing audio file, optionally using burned-in captions and local image inputs.
- `full`: generates a script, captions, metadata, ElevenLabs audio, a burned-in caption video, and optional OpenAI-generated scene images.
- `thumbnail`: generates a local 1280x720 thumbnail image without generating a video or calling YouTube.
- `topic-research`: generates and ranks local OpenAI-based YouTube Shorts topic ideas.
- `daily-shorts`: generates a high-volume daily batch of vertical Shorts packages under `outputs/daily_batches/`.
- `upload-batch-private`: uploads passed Shorts from a daily batch as private videos only.
- `series-plan`: generates a reusable series bible, episode plan, full story, and chapter source files.
- `series-check`: validates a saved series plan and updates `quality_report.json` without calling generation APIs.
- `batch-series`: generates selected episodes from a saved series plan using the existing full video pipeline.
- `shorts-series-private-upload`: creates or uses a Shorts-focused series plan, generates each vertical Short, validates each organized run folder, and uploads each Short privately.
- `upload-check`: validates an organized run folder before upload.
- `upload`: uploads `video.mp4` from a validated organized run folder using `metadata.json`.

Common options:

- `--template`: selects the local video style template.
- `--video-format`: selects `landscape` for normal YouTube episode videos or `vertical` for Shorts-style videos. Default: `landscape`.
- `--target-duration-seconds`: controls the target spoken script duration for generated scripts. Default: `150`.
- `--caption-offset`: adjusts generated caption timing in `full` mode.
- `--images-dir`: uses supported local images from a folder.
- `--image-paths`: uses explicit local image file paths.
- `--use-ai-images`: generates OpenAI scene images during `full` mode.
- `--image-count`: controls how many AI scene images to request.
- `--generate-thumbnail`: generates a local thumbnail during `full` mode.
- `--thumbnail-source`: uses a local source image for `thumbnail` mode.
- `--use-ai-thumbnail`: uses OpenAI to generate a thumbnail background.
- `--organize`: copies successful run outputs into a timestamped folder under `outputs/runs/`.
- `--run-folder`: points `upload-check` and `upload` modes to an organized run folder under `outputs/runs/`.
- `--privacy-status`: controls YouTube visibility for `upload` mode. Use `private` by default.
- `--upload-thumbnail`: optionally uploads `thumbnail.png` from the run folder after a successful video upload.
- `--niche`: sets the niche to research in `topic-research` mode.
- `--audience`: optionally sets the target audience in `topic-research` and `series-plan` modes.
- `--topic-count`: controls how many topic ideas to generate in `topic-research` mode.
- `--count`: controls how many Shorts to generate in `daily-shorts` mode. Default: `10`.
- `--short-image-count`: controls AI scene images per Short in `daily-shorts` mode. Default: `5`.
- `--short-duration-seconds`: controls target spoken duration per Short in `daily-shorts` mode. Default: `45`.
- `--no-thumbnail`: skips thumbnail generation in `daily-shorts` mode.
- `--skip-upload-check`: skips local upload-check validation in `daily-shorts` mode.
- `--ignore-topic-history`: allows `daily-shorts` to reuse previous topics by skipping local topic history checks.
- `--batch-folder`: points `upload-batch-private` to a folder under `outputs/daily_batches/`.
- `--limit`: limits how many passed Shorts `upload-batch-private` uploads.
- `--episodes`: controls how many episodes to create in `series-plan` mode, or the first N episodes to use when supported by a series mode.
- `--series-folder`: points `series-check` or `batch-series` to a saved folder under `outputs/series/`.
- `--episode`: generates one episode from a saved series plan.
- `--episodes-range`: generates an inclusive episode range from a saved series plan, such as `1-5`.
- `--force-batch`: allows `batch-series` to run even when `quality_report.json` is not ready.
- `--continue-on-error`: keeps processing later Shorts in `shorts-series-private-upload` if one Short fails. Default behavior stops on the first error.

The default topic is:

```text
The strangest disappearance in history
```

You can override it with `--topic "your topic here"` for modes that generate topic-based assets.

Script generation now defaults to a 2-3 minute weird history / mystery episode format, targeting about 150 seconds of narration or roughly 320-450 words.

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

- `OPENAI_API_KEY`: required for modes that generate scripts, topic research, and OpenAI-generated scene images.
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
python main.py --mode video --audio-path outputs/audio/the-strangest-disappearance-in-history-test.mp3
```

Build a captioned video:

```bash
python main.py --mode video --audio-path outputs/audio/the-strangest-disappearance-in-history-test.mp3 --captions-path outputs/captions/the-strangest-disappearance-in-history.srt
```

Generate a complete organized run with AI scene images:

```bash
python main.py --mode full --topic "The Lost Colony of Roanoke Episode 1: The Village That Vanished" --template ai --organize --use-ai-images --image-count 12 --generate-thumbnail --target-duration-seconds 150 --video-format landscape
```

Generate a local thumbnail only:

```bash
python main.py --mode thumbnail --topic "The strangest disappearance in history"
```

Generate a local thumbnail from an existing image:

```bash
python main.py --mode thumbnail --topic "The strangest disappearance in history" --thumbnail-source /path/to/image.png
```

Generate a complete organized run with a thumbnail:

```bash
python main.py --mode full --topic "The strangest disappearance in history" --template ai --organize --use-ai-images --image-count 6 --generate-thumbnail
```

Research topic ideas locally with OpenAI:

```bash
python main.py --mode topic-research --niche "weird history mysteries" --audience "curious history and mystery fans" --topic-count 10
```

Topic research uses OpenAI only. It does not call YouTube APIs, scrape the web, use YouTube trend data, or use analytics feedback yet. Generated topic research JSON files are saved under `outputs/topics/` and should not be committed.

## Daily Shorts Production

`daily-shorts` is optimized for high-volume Shorts production in the weird history, mystery, scary factual stories, dark history, strange historical events, and eerie true stories niche. The target production volume is 10-20 Shorts per day, with each Short meaningfully different from the others. Avoid repetitive or spammy batches even when the command can generate volume quickly.

Every `daily-shorts` run automatically generates fresh topics. By default, topics are checked against local topic history at `memory/daily_shorts_topics.json`, so previous daily Shorts topics are not reused across runs. If the system cannot find enough fresh topics after checking history and retrying, it creates the smaller fresh batch it did find and writes warnings to `batch_summary.json` and `NEXT_STEPS.md`. To get more fresh ideas, use a broader niche or lower count.

Generate a small test batch:

```bash
python main.py --mode daily-shorts --count 2 --short-image-count 4
```

Generate a full daily batch:

```bash
python main.py --mode daily-shorts --count 20
```

Generate a niche-specific batch:

```bash
python main.py --mode daily-shorts --niche "weird history and strange true stories" --count 20
```

Open the newest batch:

```bash
open "$(ls -td outputs/daily_batches/*/ | head -1)"
```

Upload one selected Short privately:

```bash
python main.py --mode upload --run-folder outputs/daily_batches/<batch-folder>/short-01 --privacy-status private --upload-thumbnail
```

Daily batch behavior:

- Creates one timestamped folder under `outputs/daily_batches/`.
- Creates `short-01/`, `short-02/`, and later Short folders inside the batch.
- Generates unique, specific, curiosity-driven Shorts topics every run.
- Checks generated topics against `memory/daily_shorts_topics.json` and skips previous daily Shorts topics by default.
- Saves accepted fresh topics to local topic history before generation starts, so failed batches do not immediately reuse the same topics.
- If fresh topic generation shortfalls, continues with the fresh topics found and warns in `batch_summary.json` and `NEXT_STEPS.md`.
- Uses vertical video format by default.
- Targets about 45 seconds of narration by default.
- Generates 5 AI scene images per Short by default, with 4-6 recommended for faster Shorts production.
- Generates `script.txt`, `captions.srt`, `metadata.json`, `audio.mp3`, `video.mp4`, `images/`, `thumbnail.png` when enabled, and `quality_score.json` for each Short.
- Runs local upload-check validation by default when each Short package completes.
- Writes `batch_summary.json` and `NEXT_STEPS.md` at the batch root.

`NEXT_STEPS.md` tells you where the batch folder is, how many Shorts passed quality, how to open the folder on Mac, how to upload-check a selected Short, and how to privately upload a selected Short. Review every video before publishing. `daily-shorts` does not auto-publish publicly, does not schedule videos, and does not use YouTube Analytics.

To make an explicit exception and allow topic reuse, add `--ignore-topic-history`:

```bash
python main.py --mode daily-shorts --count 20 --ignore-topic-history
```

Use this only when you intentionally want to bypass the local history check.

Optional private batch upload is available for already-reviewed batches:

```bash
python main.py --mode upload-batch-private --batch-folder outputs/daily_batches/<batch-folder> --limit 3 --upload-thumbnail
```

`upload-batch-private` only uploads Shorts that passed local quality scoring, always uses `private` privacy status, and writes `upload_results.json` in the batch folder. Do not use it until you have reviewed the generated Shorts.

Generate a reusable series plan:

```bash
python main.py --mode series-plan \
  --topic "The Flannan Isles Lighthouse Mystery" \
  --episodes 5 \
  --target-duration-seconds 150 \
  --audience "fans of weird history and strange true stories"
```

`series-plan` is intended to create episode-ready story plans, not just file structure. The current primary format is 2-3 minute landscape YouTube episodes for serialized weird-history, mystery, scary factual story, dark history, strange historical event, and eerie true story channels. This differs from Shorts: each episode needs a connected documentary arc, a clear narrative purpose, concrete evidence focus, continuity from the previous episode, and a specific reason to continue.

It writes a series bible, full story arc, episode plan, chapter source files, and `quality_report.json` with hooks, narrative purposes, concrete topic-specific evidence focus, avoid-repeating notes, factual guardrails, ending teases, and final closing thoughts. Generated factual plans should be reviewed before `batch-series`, especially when the topic includes disputed records, later retellings, uncertain causes, death counts, folklore, or evidence that is easy to overstate.

Check a saved plan without spending API credits:

```bash
python main.py --mode series-check \
  --series-folder outputs/series/<series-folder-name>
```

`series-check` loads `series_bible.json` and `episode_plan.json`, updates `quality_report.json`, and prints the report as JSON. It does not call OpenAI, ElevenLabs, image generation, video generation, YouTube, or upload anything. Do not run `batch-series` until `quality_report.json` says `ready_for_batch` is `true`.

Generate selected episodes from a saved series plan:

```bash
python main.py --mode batch-series \
  --series-folder outputs/series/<series-folder-name> \
  --episodes-range 1-5 \
  --template ai \
  --organize \
  --use-ai-images \
  --image-count 12 \
  --generate-thumbnail \
  --target-duration-seconds 150 \
  --video-format landscape
```

`batch-series` now checks `quality_report.json` or regenerates the report before producing episodes. If `ready_for_batch` is `false`, it fails before spending generation credits. Fix weak titles, vague evidence, missing hooks, repeated episodes, unsupported templates, unsupported video formats, or weak narrative purposes before running batch generation.

Force a batch only when intentionally overriding the quality gate:

```bash
python main.py --mode batch-series \
  --series-folder outputs/series/<series-folder-name> \
  --episodes 1 \
  --force-batch
```

`--force-batch` prints a warning and continues. Use it only when you have manually reviewed the issues and still want to spend credits. `batch-series` does not upload to YouTube by default and does not call the upload mode. It writes local assets, can organize each episode into a run folder, and runs `upload-check` only for organized run folders.

Create and privately upload a complete 5-video Shorts series:

```bash
python main.py --mode shorts-series-private-upload --topic "The Lost Colony of Roanoke" --episodes 5
```

Use an existing series folder:

```bash
python main.py --mode shorts-series-private-upload --series-folder outputs/series/the-lost-colony-of-roanoke --episodes 5
```

`shorts-series-private-upload` is intentionally Shorts-only. Long-form private upload may be added later, but it is not part of this mode.

Default settings:

- `privacy_status`: `private`
- `episodes`: `5`
- `organize`: `true`
- `template`: `ai`
- `use_ai_images`: `true`
- `image_count`: `7`
- `generate_thumbnail`: `true`
- `target_duration_seconds`: `75`
- `video_format`: `vertical`
- stop on the first error unless `--continue-on-error` is passed

Behavior:

- If `--series-folder` is provided, it uses that folder and does not create a new series plan.
- If `--series-folder` is not provided, `--topic` is required and the mode creates a Shorts-focused series plan.
- The generated plan is optimized for 5 connected short-form videos: immediate hooks, one focused mystery/history beat per Short, quick escalation, ending teases, and a short CTA.
- Each Short is generated through the existing full generation pipeline.
- Each run is organized into a timestamped folder under `outputs/runs/`.
- `upload-check` runs before every upload. If it fails, the workflow stops before upload unless `--continue-on-error` is set.
- Each ready Short uploads privately to YouTube through OAuth.
- `thumbnail.png` is uploaded when it exists in the organized run folder. Missing thumbnails do not fail the upload.
- Episode upload records are written under `outputs/series/<series-slug>/episodes/`.
- A final batch summary is saved under `outputs/batches/`.

This command can spend OpenAI, ElevenLabs, and YouTube API quota or credits for every Short in the series. The first YouTube upload may open the browser OAuth flow.

Generated outputs, run folders, series folders, daily Shorts batches, batch summaries, OAuth secrets, OAuth tokens, and `.env` must never be committed.

Validate an organized run folder before upload:

```bash
python main.py --mode upload-check --run-folder outputs/runs/<run-folder-name>
```

Upload a validated run folder privately:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

Upload a validated run folder privately and set its thumbnail:

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private --upload-thumbnail
```

Use a custom topic with any mode that accepts topic input:

```bash
python main.py --mode script --topic "The island nobody was allowed to visit"
```

## Successful Manual Upload Workflow

Generate a complete organized run:

```bash
python main.py --mode full --topic "The strangest disappearance in history" --template ai --organize --use-ai-images --image-count 6
```

Validate the newest run folder:

```bash
python main.py --mode upload-check --run-folder "$(ls -td outputs/runs/*/ | head -1)"
```

Upload privately:

```bash
python main.py --mode upload --run-folder "$(ls -td outputs/runs/*/ | head -1)" --privacy-status private
```

If the run folder contains `thumbnail.png`, upload privately and set the thumbnail:

```bash
python main.py --mode upload --run-folder "$(ls -td outputs/runs/*/ | head -1)" --privacy-status private --upload-thumbnail
```

After upload, review the video in YouTube Studio before publishing. Private uploads are visible only in the correct authorized YouTube Studio channel.

## Series Workflow

The reusable series flow is:

1. Generate a series plan with `--mode series-plan`.
2. Review the generated series bible, episode plan, full story, chapter files, and `quality_report.json` under `outputs/series/<series-slug>/`.
3. Run `--mode series-check` after edits to update `quality_report.json`.
4. Generate selected episodes with `--mode batch-series` only when `ready_for_batch` is `true`.
5. Review `upload-check` results for organized run folders.
6. Manually upload private videos after review.

Factual series plans should still get human review before `batch-series`, especially for dates, names, locations, and unresolved theories. `series-plan` includes topic-containment guardrails to avoid unsupported templates, generic episode arcs, repeated episode coverage, overstated evidence, and cross-contaminated details from unrelated famous cases, but generated plans may still require factual review before production. Do not run `batch-series` until `quality_report.json` says `ready_for_batch` is `true`.

`series-plan` creates:

- `series_bible.json`
- `episode_plan.json`
- `full_story.md`
- `quality_report.json`
- `chapters/episode-XX.md`
- `episodes/` for generated per-episode records

`quality_report.json` is a local readiness report with `ready_for_batch`, issues, warnings, and suggestions. It checks for missing fields, unsupported templates, unsupported video formats, generic or overclaiming titles, repeated episode coverage, vague fake-source language, weak hooks, missing ending teases, and missing narrative purposes.

Final episodes still need an `ending_tease`; it should point to the lingering mystery or unresolved factual tension rather than another episode.

`batch-series` writes batch summaries under `outputs/batches/` and writes per-episode records under `outputs/series/<series-slug>/episodes/episode-XX.json`. Generated series folders and batch summary JSON files are ignored by Git. Keep only `.gitkeep` files tracked in those folders.

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
- `thumbnail.png`
- `images/` when image copying is available

`metadata.json` must be valid JSON and include:

- `title`
- `description`
- `tags`
- `hashtags`
- `topic`
- `generated_from`

`ready: true` means the local package is valid for upload. `ready: false` means the folder is missing required upload files or has invalid metadata.

Missing `thumbnail.png` creates a warning only. It does not make upload readiness fail.

## Manual YouTube Upload

`upload` uploads `video.mp4` from a validated organized run folder using `metadata.json`.
Generated metadata now uses richer episode-style descriptions, weird history / mystery tags, and niche hashtags by default.

```bash
python main.py --mode upload --run-folder outputs/runs/<run-folder-name> --privacy-status private
```

Upload behavior:

- `--run-folder` points to the organized run folder under `outputs/runs/`.
- `--privacy-status` controls YouTube visibility. Valid values are `private`, `unlisted`, and `public`.
- `--upload-thumbnail` uploads `thumbnail.png` from the same run folder after the video upload succeeds.
- `private` is recommended by default for safety.
- The upload validates the run folder first and stops before OAuth or upload if validation fails.
- The upload uses `title`, `description`, `tags`, and `hashtags` from `metadata.json`.
- Hashtags are appended to the description if they are not already included.
- The upload does not generate scripts, captions, metadata, audio, images, or video.
- The upload uses YouTube OAuth, not `YOUTUBE_API_KEY`.

Thumbnail upload behavior:

- Thumbnail upload is optional. By default, `upload` uploads the video only.
- `thumbnail.png` must already exist in the organized run folder when `--upload-thumbnail` is used.
- Thumbnail upload happens after the video has uploaded successfully.
- Missing `thumbnail.png` does not affect normal video-only uploads.
- Thumbnail upload uses the same YouTube OAuth credentials and token as video upload.

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

`tools/video_builder.py` creates local MP4 videos and supports these templates:

- `default`
- `bold`
- `minimal`
- `ai`

Video format options:

- `--video-format landscape`: renders 1920x1080 and is recommended for 2-3 minute episode-style YouTube videos.
- `--video-format vertical`: renders 1080x1920 and remains available for Shorts-style videos.

Select a template with `--template`:

```bash
python main.py --mode full --template ai --video-format landscape
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
python main.py --mode video --audio-path outputs/audio/the-strangest-disappearance-in-history-test.mp3 --captions-path outputs/captions/the-strangest-disappearance-in-history.srt --template ai --image-paths /path/to/image1.png /path/to/image2.jpg
```

Use a local image folder:

```bash
python main.py --mode video --audio-path outputs/audio/the-strangest-disappearance-in-history-test.mp3 --captions-path outputs/captions/the-strangest-disappearance-in-history.srt --template ai --images-dir /path/to/images
```

Supported local image extensions:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

Generate AI scene images in `full` mode:

```bash
python main.py --mode full --topic "The strangest disappearance in history" --template ai --organize --use-ai-images --image-count 6 --video-format landscape
```

AI image generation uses `OPENAI_API_KEY`, may use extra API credits, and writes generated images to `outputs/images/`. Scene image prompts are built from ordered narration beats so generated images better match the moment being narrated.

## Thumbnail Support

`thumbnail` mode creates a local 1280x720 YouTube-ready thumbnail under `outputs/thumbnails/`.

```bash
python main.py --mode thumbnail --topic "The strangest disappearance in history"
```

Use `--thumbnail-source` to crop and resize an existing image as the visual base, then add a readable title overlay from the topic:

```bash
python main.py --mode thumbnail --topic "The strangest disappearance in history" --thumbnail-source /path/to/image.png
```

Use `--use-ai-thumbnail` to generate a thumbnail background with OpenAI, then add the local title overlay:

```bash
python main.py --mode thumbnail --topic "The strangest disappearance in history" --use-ai-thumbnail
```

Full mode only generates a thumbnail when `--generate-thumbnail` is provided:

```bash
python main.py --mode full --topic "The strangest disappearance in history" --template ai --organize --use-ai-images --image-count 6 --generate-thumbnail
```

When organized, generated thumbnails are copied into the run folder as `thumbnail.png`. Thumbnail generation is local only. To upload that file to YouTube after video upload, pass `--upload-thumbnail` in `upload` mode.

## Output Folders

Generated outputs are written under `outputs/` and `memory/`:

- `outputs/scripts/`: generated `.txt` scripts.
- `outputs/captions/`: generated `.srt` captions.
- `outputs/metadata/`: generated `.json` metadata files.
- `outputs/audio/`: generated ElevenLabs `.mp3` audio and local test `.mp3` files.
- `outputs/videos/`: generated `.mp4` videos.
- `outputs/images/`: generated OpenAI scene images.
- `outputs/thumbnails/`: generated thumbnail images.
- `outputs/topics/`: generated OpenAI topic research `.json` files.
- `outputs/series/`: generated series bibles, episode plans, chapter files, and per-episode records.
- `outputs/batches/`: generated batch summary `.json` files.
- `outputs/daily_batches/`: generated daily Shorts batch folders, per-Short assets, quality scores, and next steps.
- `outputs/runs/`: timestamped organized copies of successful run outputs.
- `memory/logs.json`: successful generation run log.

A complete organized `full` run can contain:

- `script.txt`
- `captions.srt`
- `metadata.json`
- `audio.mp3`
- `video.mp4`
- `thumbnail.png`
- `images/` if image copying is implemented

Generated `.txt`, `.srt`, `.json`, `.mp3`, `.mp4`, `.png`, `.jpg`, `.jpeg`, `.webp`, generated topic research files, generated series folders, generated daily batch folders, generated batch summaries, and generated run folders are ignored by Git and should not be committed.

External trend data, YouTube search, analytics, performance feedback, scheduling, and automatic publishing are future milestones.

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
- generated series folders, except tracked `.gitkeep` files
- generated daily Shorts batch folders, except tracked `.gitkeep` files
- generated batch summaries
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

If `--upload-thumbnail` fails, confirm `thumbnail.png` exists in the organized run folder. The file is optional for normal uploads but required when the flag is used.

If credential or token files appear in ignored status, that is expected. They must remain ignored and unstaged.

If generated files do not appear in `git status`, that is expected. Generated outputs, generated image files, and generated run folders are ignored by Git.

If thumbnail generation from a source image fails, confirm `--thumbnail-source` points to an existing image file.

If `--use-ai-thumbnail` fails with an OpenAI API error, confirm `OPENAI_API_KEY` is set in `.env`.

If `memory/logs.json` errors during logging, make sure the file contains valid JSON and that the top-level value is an array.

## Current Limitations / Not Built Yet

- No general automatic thumbnail upload outside `shorts-series-private-upload` and explicit `--upload-thumbnail`.
- No long-form one-command private upload yet.
- No automatic public publishing.
- No scheduling yet.
- No YouTube Analytics import yet.
- No stock footage search yet.
- No background music yet.
- No external trend data or YouTube search yet.
- No automatic winner detection or performance feedback loop yet.
- Private batch upload exists through `upload-batch-private`, but generated Shorts should still be reviewed manually before use.

## Suggested Next Milestones

- Improve thumbnail generation/support.
- Add thumbnail review and management workflow.
- Improve image prompt quality.
- Add stock footage or background media search.
- Add external trend research once the local topic workflow is stable.
- Add scheduling.
- Add analytics and performance logging.
