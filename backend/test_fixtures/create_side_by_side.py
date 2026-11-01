from pathlib import Path
from PIL import Image

def make_side_by_side(img1_path: Path, img2_path: Path, out_path: Path, label1="Reference Template", label2="Generated Output"):
    im1 = Image.open(img1_path).convert("RGB")
    im2 = Image.open(img2_path).convert("RGB")

    w1, h1 = im1.size
    w2, h2 = im2.size
    max_h = max(h1, h2)
    tot_w = w1 + w2 + 30

    combined = Image.new("RGB", (tot_w, max_h), (230, 235, 240))
    combined.paste(im1, (0, 0))
    combined.paste(im2, (w1 + 30, 0))
    combined.save(str(out_path))
    print(f"Created: {out_path}")

def main():
    comp_dir = Path("backend/test_fixtures/comparison_results")
    for i in range(1, 4):
        ref = comp_dir / f"reference_page_{i}.png"
        gen = comp_dir / f"science_corrected_page_{i}.png"
        out = comp_dir / f"side_by_side_page_{i}.png"
        if ref.exists() and gen.exists():
            make_side_by_side(ref, gen, out)

if __name__ == "__main__":
    main()
