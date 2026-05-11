"""Generates icon.ico for the AI Skill Generator CLI binary."""
import os
from PIL import Image, ImageDraw


def create_icon():
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (79, 70, 229, 255))  # indigo #4f46e5
        draw = ImageDraw.Draw(img)

        s = size / 256.0
        # Lightning bolt ⚡ scaled to canvas
        bolt = [
            (140 * s, 10 * s),
            (60 * s,  130 * s),
            (110 * s, 130 * s),
            (80 * s,  246 * s),
            (196 * s, 126 * s),
            (146 * s, 126 * s),
        ]
        draw.polygon(bolt, fill=(255, 255, 255, 255))
        images.append(img)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    images[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Created {out}")


if __name__ == "__main__":
    create_icon()
