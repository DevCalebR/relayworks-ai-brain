import json
from datetime import datetime, timezone
from pathlib import Path


LOG_FILE = Path("memory/logs.json")


def _load_logs():
    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text("[]\n", encoding="utf-8")
        return []

    content = LOG_FILE.read_text(encoding="utf-8")

    if not content.strip():
        return []

    try:
        logs = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"{LOG_FILE} contains invalid JSON") from error

    if not isinstance(logs, list):
        raise ValueError(f"{LOG_FILE} must contain a JSON array")

    return logs


def log_pipeline_run(topic, mode, outputs):
    """
    Append one successful pipeline run to memory/logs.json.

    Args:
        topic: Pipeline topic.
        mode: CLI mode that completed successfully.
        outputs: Dictionary of generated output paths.

    Returns:
        The appended log entry dictionary.
    """
    logs = _load_logs()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "mode": mode,
        "outputs": outputs,
    }

    logs.append(entry)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(logs, indent=2) + "\n", encoding="utf-8")

    return entry
