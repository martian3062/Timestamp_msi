from pathlib import Path
import inspect

import pandas as pd
import slideflow as sf


project = sf.Project("slideflow_project")
dataset = project.dataset(
    tile_px=256,
    tile_um=128,
    filter_blank="msi_status",
    verification="both",
)

ann = Path("annotations/tcga_crc_msi_annotations.csv")
slides = Path("slideflow_project/data/slides")
df = pd.read_csv(ann)

print("split_signature", inspect.signature(dataset.split))
print("ann_exists", ann.exists())
print("slides_dir", slides.exists())
print("rows", len(df))
print("labels", df["msi_status"].value_counts().to_dict())
print("slide_files", len(list(slides.glob("*.svs")) + list(slides.glob("*.ndpi"))))
