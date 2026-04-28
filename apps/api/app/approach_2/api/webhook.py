from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database.setup import get_db
import httpx
import uuid

router = APIRouter()

class N8nTriggerRequest(BaseModel):
    n8n_webhook_url: str
    experiment_name: str
    trials: int = 5

class OptunaTrialRequest(BaseModel):
    trial_id: str
    parameters: dict

@router.post("/start-automation")
async def trigger_n8n_automation(req: N8nTriggerRequest, db: Session = Depends(get_db)):
    """
    Kicks off an n8n webhook pointing to the UI's pending manual wait queue.
    """
    trigger_payload = {
        "event": "hyperparameter_tuning_requested",
        "experiment_name": req.experiment_name,
        "trials_requested": req.trials,
        "webhook_callback": f"http://backend:8000/webhook/optuna/trial"
    }

    try:
         async with httpx.AsyncClient() as client:
             # Shoot payload to n8n webhook
             await client.post(req.n8n_webhook_url, json=trigger_payload)
             return {"message": "Automation triggered in n8n. Waiting for manual approval in n8n."}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to trigger n8n: {e}")


@router.post("/optuna/trial")
def run_optuna_trial(req: OptunaTrialRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    n8n will iteratively hit this endpoint to spawn Slideflow MIL trials via Optuna injected params.
    """
    from ..pipelines.mil_trainer import run_mil_training
    
    exp_id = str(uuid.uuid4())[:8]
    # req.parameters contains dynamically generated hyperparameters (lr, batch_size, etc.) from n8n / Optuna logic.
    background_tasks.add_task(run_mil_training, exp_id, req.parameters)

    return {"message": f"Trial {req.trial_id} background task spawned", "exp_id": exp_id}
