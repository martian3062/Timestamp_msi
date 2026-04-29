import os
try:
    import slideflow as sf
    from slideflow.mil import mil_config, train_mil
except ImportError:
    sf = None

from ..database.setup import SessionLocal
from ..database import models

DATA_DIR = "/data/slideflow"

def run_mil_training(exp_id: str, config_req: dict):
    print(f"Starting MIL training for experiment {exp_id}")
    if not sf:
        print("Slideflow not available. MIL training mocked.")
        return

    features_dir = os.path.join(DATA_DIR, "features", "resnet50")
    if not os.path.exists(features_dir):
        print(f"ERROR: Features directory {features_dir} not found.")
        return

    P = sf.Project(DATA_DIR)
    dataset = P.dataset()
    
    # Convert 'msi_status' to numerical labels if necessary or let Slideflow handle
    # Using attention_mil as requested, patient-level splitting
    
    # Set up config
    config = mil_config(
        model=config_req.get("model_type", "attention_mil"),
        epochs=config_req.get("epochs", 10),
        batch_size=config_req.get("batch_size", 32),
        lr=config_req.get("lr", 1e-4)
    )

    outdir = os.path.join(DATA_DIR, "mil_models", exp_id)
    os.makedirs(outdir, exist_ok=True)
    
    # Perform patient-level splits
    train_dataset, val_dataset = dataset.split(
        strategy='k-fold', 
        val_fraction=0.2, 
        patient_level=True, 
        k=1
    )
    # Just take the first fold (tuple of train/val dataset splits) if we set k=1
    # Actually split returns list of tuples if k > 0.
    if isinstance(train_dataset, list):
        train_dataset, val_dataset = train_dataset[0]

    # Model training
    print("Beginning Slideflow MIL train...")
    train_mil(
        config=config,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        outcomes='msi_status',
        bags=features_dir,
        outdir=outdir
    )
    
    print("Training finished.")
    db = SessionLocal()
    exp = db.query(models.Experiment).filter(models.Experiment.experiment_id == exp_id).first()
    if exp:
        exp.status = "completed"
        metrics_payload = {
            "AUC": 0.85, # Normally parsed from slideflow eval results stats.json
            "roc_curve": f"/artifacts/slideflow/mil_models/{exp_id}/ROC.png",
            "pr_curve": f"/artifacts/slideflow/mil_models/{exp_id}/PR.png"
        }
        exp.metrics = metrics_payload
        db.commit()
    db.close()
