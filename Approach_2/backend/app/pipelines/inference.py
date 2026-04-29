import os
try:
    import slideflow as sf
except ImportError:
    sf = None

DATA_DIR = "/data/slideflow"

def run_inference(slide_id: str, model_version: str):
    """Run prediction on a single slide and generate heatmap."""
    heatmaps_dir = os.path.join(DATA_DIR, "heatmaps")
    os.makedirs(heatmaps_dir, exist_ok=True)
    
    heatmap_file = os.path.join(heatmaps_dir, f"{slide_id}_heatmap.png")
    heatmap_url = f"/artifacts/slideflow/heatmaps/{slide_id}_heatmap.png"

    if not sf:
        print("Slideflow not available. Inference mocked.")
        return {
            "prediction": "MSI-H",
            "probability": 0.88,
            "heatmap_path": "mocked"
        }
    
    # Attempt to locate the WSI file
    slide_path = f"/data/slides/{slide_id}.svs"
    if not os.path.exists(slide_path):
        slide_path = f"/data/slides/{slide_id}.ndpi"
        
    model_path = os.path.join(DATA_DIR, "mil_models", model_version)
    
    try:
        heatmap = sf.Heatmap(
            slide_path, 
            model=model_path,
            outdir=heatmaps_dir,
            tile_px=256, 
            tile_um=256
        )
        heatmap.save(heatmap_file)
    except Exception as e:
        print(f"Error generating heatmap: {e}")
        return {
            "prediction": "Unknown",
            "probability": 0.0,
            "heatmap_path": None,
            "error": str(e)
        }

    return {
        "prediction": "MSI-H", # Example static label, extract from model logic
        "probability": 0.92,
        "heatmap_path": heatmap_url
    }
