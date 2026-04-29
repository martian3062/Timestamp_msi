import os
try:
    import slideflow as sf
except ImportError:
    sf = None

DATA_DIR = "/data/slideflow"

def run_feature_extraction(cohort: str, extractor_name: str="resnet50"):
    print(f"Starting feature extraction with {extractor_name} for cohort {cohort}")
    if not sf:
        print("Slideflow not available. Feature extraction mocked.")
        return
        
    P = sf.Project(DATA_DIR)
    dataset = P.dataset()
    dataset = dataset.filter({'cohort': cohort})
    
    print(f"Building feature extractor: {extractor_name}")
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    feature_extractor = sf.build_feature_extractor(extractor_name, device=device)
    
    features_dir = os.path.join(DATA_DIR, "features", extractor_name)
    os.makedirs(features_dir, exist_ok=True)
    
    print(f"Generating feature bags into {features_dir}")
    P.generate_feature_bags(feature_extractor, dataset, outdir=features_dir)
    print("Feature extraction complete.")
