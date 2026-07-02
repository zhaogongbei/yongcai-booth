from pathlib import Path
from PIL import Image


IMAGE_ROOT = Path(__file__).resolve().parents[1] / "public" / "images"
QUALITY = 80
MOBILE_WIDTH = 640


def convert_image(path: Path) -> None:
    with Image.open(path) as image:
        image = image.convert("RGB")
        webp_path = path.with_suffix(".webp")
        image.save(webp_path, "WEBP", quality=QUALITY, method=6)

        mobile_path = path.with_name(f"{path.stem}-{MOBILE_WIDTH}w.webp")
        mobile = image.copy()
        if mobile.width > MOBILE_WIDTH:
            ratio = MOBILE_WIDTH / mobile.width
            mobile = mobile.resize((MOBILE_WIDTH, int(mobile.height * ratio)))
        mobile.save(mobile_path, "WEBP", quality=75, method=6)
        print(f"optimized {path.relative_to(IMAGE_ROOT)}")


def main() -> None:
    for path in IMAGE_ROOT.rglob("*.png"):
        convert_image(path)


if __name__ == "__main__":
    main()
