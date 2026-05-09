import pytest

from tools.script_reader import read_script_file


def test_read_script_file_accepts_txt_and_strips_whitespace(tmp_path):
    script_path = tmp_path / "manual-script.txt"
    script_path.write_text("\n  This is the narration script.  \n", encoding="utf-8")

    assert read_script_file(script_path) == "This is the narration script."


def test_read_script_file_accepts_markdown(tmp_path):
    script_path = tmp_path / "manual-script.md"
    script_path.write_text("# Title\n\nNarration text.", encoding="utf-8")

    assert read_script_file(script_path) == "# Title\n\nNarration text."


def test_read_script_file_missing_path_fails_clearly(tmp_path):
    script_path = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError, match="Script file does not exist"):
        read_script_file(script_path)


def test_read_script_file_directory_fails_clearly(tmp_path):
    with pytest.raises(ValueError, match="Script path must be a file"):
        read_script_file(tmp_path)


def test_read_script_file_unsupported_extension_fails_clearly(tmp_path):
    script_path = tmp_path / "manual-script.docx"
    script_path.write_text("Narration text.", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported script file extension"):
        read_script_file(script_path)


def test_read_script_file_empty_file_fails_clearly(tmp_path):
    script_path = tmp_path / "empty.txt"
    script_path.write_text("   \n", encoding="utf-8")

    with pytest.raises(ValueError, match="Script file is empty"):
        read_script_file(script_path)
