# adapted from: https://alexharri.com/blog/ascii-rendering

import argparse
import math

from PIL import Image, ImageDraw, ImageFont


def get_sampling_circles(W, H):
    # Base layout from article's reverse-engineered JS array:
    # [[-1, -1], [1, -1], [-1.37, 0], [1.37, 0], [-1, 1], [1, 1]]
    R = W * 0.4
    return [
        (W / 2 + x * (W * 0.25), H / 2 + y * (H / 3.0), R)
        for x, y in [(-1, -1), (1, -1), (-1.37, 0), (1.37, 0), (-1, 1), (1, 1)]
    ]


def calc_circle_overlap(img, cx, cy, r):
    w, h = img.size
    pixels = img.load()
    total = 0
    count = 0

    x0, x1 = max(0, int(cx - r)), min(w - 1, int(math.ceil(cx + r)))
    y0, y1 = max(0, int(cy - r)), min(h - 1, int(math.ceil(cy + r)))

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r**2:
                total += pixels[x, y]
                count += 1

    if not count:
        return 0.0
    return (total / count) / 255.0


def build_shape_vectors(font, W, H, circles):
    chars = [chr(i) for i in range(32, 127)]
    raw_vectors = {}

    for c in chars:
        img = Image.new("L", (W, H), color=0)
        ImageDraw.Draw(img).text((W / 2, H / 2), c, font=font, fill=255, anchor="mm")
        raw_vectors[c] = [calc_circle_overlap(img, cx, cy, r) for cx, cy, r in circles]

    max_vals = [max(v[i] for v in raw_vectors.values()) or 1.0 for i in range(6)]
    return {c: [v[i] / max_vals[i] for i in range(6)] for c, v in raw_vectors.items()}


def render_image(
    image_path,
    cols=80,
    font_path="/usr/share/fonts/truetype/robotomono/RobotoMono-Regular.ttf",
    W=20,
    H=40,
    use_color=False,
):
    try:
        font = ImageFont.truetype(font_path, H - 4)
    except Exception:
        font = ImageFont.load_default()

    circles = get_sampling_circles(W, H)
    shape_vectors = build_shape_vectors(font, W, H, circles)

    orig_img = Image.open(image_path).convert("RGB")
    img_w, img_h = orig_img.size

    cell_w = img_w / cols
    cell_h = cell_w * (H / W)
    rows = int(img_h / cell_h)

    img_rgb = orig_img.resize((cols * W, rows * H), Image.Resampling.BILINEAR)
    img_l = img_rgb.convert("L")

    output = []
    for r in range(rows):
        row_str = []
        for c in range(cols):
            box = (c * W, r * H, (c + 1) * W, (r + 1) * H)
            cell_img_l = img_l.crop(box)
            samp_vec = [calc_circle_overlap(cell_img_l, cx, cy, rad) for cx, cy, rad in circles]

            best_char, best_dist = " ", float("inf")
            for char, shape_vec in shape_vectors.items():
                dist = sum((samp_vec[i] - shape_vec[i]) ** 2 for i in range(6))
                if dist < best_dist:
                    best_dist = dist
                    best_char = char

            if use_color:
                cell_img_rgb = img_rgb.crop(box)
                red, green, blue = cell_img_rgb.resize((1, 1), Image.Resampling.BOX).getpixel(
                    (0, 0)
                )
                row_str.append(f"\033[38;2;{red};{green};{blue}m{best_char}")
            else:
                row_str.append(best_char)

        if use_color:
            row_str.append("\033[0m")
        output.append("".join(row_str))

    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Path to 2D image")
    parser.add_argument("--cols", type=int, default=80, help="Output columns")
    parser.add_argument("--color", action="store_true", help="Output with ANSI truecolor")
    args = parser.parse_args()
    print(render_image(args.image, cols=args.cols, use_color=args.color))


if __name__ == "__main__":
    main()
