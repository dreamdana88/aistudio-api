from pathlib import Path

from aistudio_api.domain.models import parse_image_output


ROOT = Path(__file__).resolve().parents[1]


def test_parse_image_output_keeps_only_final_images_in_images_field():
    raw = (ROOT / "test-image-output.json").read_text(encoding="utf-8")
    output = parse_image_output(raw)

    assert len(output.images) == 1
    assert len(output.reasoning_images) == 1
    assert output.images[0].mime == "image/jpeg"
    assert output.reasoning_images[0].mime == "image/jpeg"
    assert output.images[0].data != output.reasoning_images[0].data
    assert output.thinking.startswith("**Envisioning a Kitty Scene**")
