from tools.asset_reuse import (
    find_existing_scene_images,
    find_existing_thumbnail_path,
    get_output_slug,
)


def test_get_output_slug_is_stable():
    assert get_output_slug("The Disappearance of the Sodder Children") == (
        "the-disappearance-of-the-sodder-children"
    )
    assert get_output_slug("  Weird: History?!  ") == "weird-history"


def test_find_existing_scene_images_returns_ordered_images(tmp_path):
    slug = "the-disappearance-of-the-sodder-children"
    scene_02 = tmp_path / f"{slug}-scene-02.png"
    scene_01 = tmp_path / f"{slug}-scene-01.png"
    scene_02.write_bytes(b"image 2")
    scene_01.write_bytes(b"image 1")

    image_paths = find_existing_scene_images(
        "The Disappearance of the Sodder Children",
        2,
        output_dir=tmp_path,
    )

    assert image_paths == [scene_01, scene_02]


def test_find_existing_scene_images_detects_insufficient_images(tmp_path):
    slug = "the-disappearance-of-the-sodder-children"
    (tmp_path / f"{slug}-scene-01.png").write_bytes(b"image 1")

    image_paths = find_existing_scene_images(
        "The Disappearance of the Sodder Children",
        3,
        output_dir=tmp_path,
    )

    assert len(image_paths) == 1


def test_find_existing_thumbnail_path_returns_existing_path(tmp_path):
    thumbnail_path = tmp_path / "the-disappearance-of-the-sodder-children-thumbnail.png"
    thumbnail_path.write_bytes(b"thumbnail")

    assert (
        find_existing_thumbnail_path(
            "The Disappearance of the Sodder Children",
            output_dir=tmp_path,
        )
        == thumbnail_path
    )


def test_find_existing_thumbnail_path_returns_none_when_missing(tmp_path):
    assert (
        find_existing_thumbnail_path(
            "The Disappearance of the Sodder Children",
            output_dir=tmp_path,
        )
        is None
    )
