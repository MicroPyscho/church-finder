import subprocess
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Deployment
from app.schemas import (
    DeploymentOut, DeploymentCreate,
    RollbackRequest, RollbackResponse,
)
from app.config import settings

router  = APIRouter()
logger  = logging.getLogger(__name__)


@router.get("", response_model=list[DeploymentOut])
async def list_deployments(
    environment: str = "",
    limit:       int = 20,
    db:          AsyncSession = Depends(get_db),
):
    q = select(Deployment).order_by(Deployment.deployed_at.desc()).limit(limit)
    if environment:
        q = q.where(Deployment.environment == environment)
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.get("/current/{environment}", response_model=DeploymentOut)
async def current_deployment(environment: str, db: AsyncSession = Depends(get_db)):
    q = (
        select(Deployment)
        .where(Deployment.environment == environment, Deployment.is_current == True)
        .order_by(Deployment.deployed_at.desc())
        .limit(1)
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(404, f"No current deployment for environment '{environment}'")
    return row


@router.post("", response_model=DeploymentOut, status_code=201)
async def record_deployment(
    payload: DeploymentCreate,
    db:      AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Deployment)
        .where(Deployment.environment == payload.environment)
        .values(is_current=False)
    )
    deploy = Deployment(**payload.model_dump())
    db.add(deploy)
    await db.commit()
    await db.refresh(deploy)
    return deploy


@router.post("/rollback", response_model=RollbackResponse)
async def rollback(
    payload: RollbackRequest,
    db:      AsyncSession = Depends(get_db),
):
    target = await db.get(Deployment, payload.target_deployment_id)
    if not target:
        raise HTTPException(404, "Target deployment not found")

    env = target.environment

    await db.execute(
        update(Deployment)
        .where(Deployment.environment == env, Deployment.is_current == True)
        .values(is_current=False)
    )

    rollback_deploy = Deployment(
        environment=env,
        version=f"rollback-to-{target.version}",
        image_tag=target.image_tag,
        deployed_by="rollback-button",
        is_current=True,
        rollback_of=target.id,
        notes=f"Rolled back: {payload.reason}" if payload.reason else "Manual rollback",
    )
    db.add(rollback_deploy)
    await db.commit()
    await db.refresh(rollback_deploy)

    if not settings.is_development:
        _trigger_rollback(target.image_tag, env)

    return RollbackResponse(
        success=True,
        new_deployment=rollback_deploy,
        message=f"Rolled back {env} to {target.version} ({target.image_tag})",
    )


def _trigger_rollback(image_tag: str, environment: str):
    try:
        subprocess.run(
            ["bash", "/app/scripts/rollback.sh", image_tag, environment],
            check=True,
            capture_output=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Rollback script failed: %s", exc.stderr.decode())
        raise HTTPException(500, f"Rollback script failed: {exc.stderr.decode()}")
    except FileNotFoundError:
        logger.warning("rollback.sh not found — running in local/dev mode")
        
        