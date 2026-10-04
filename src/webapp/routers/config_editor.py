"""Configuration read/validate/save API and system control endpoints.

Validation reuses vision_system.config.loader so the web layer can never
accept values the application itself would reject. Saving never touches the
running pipeline: changes apply on the next restart (restart-required flag).
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vision_system.app_control import AppControl
from vision_system.config.loader import CONFIG_FILES, ConfigError, validate_config_data
from vision_system.utils.paths import CONFIG_DIR

logger = logging.getLogger(__name__)


class SaveRequest(BaseModel):
    raw: str | None = None
    values: dict[str, Any] | None = None


def _read_raw(name: str, config_dir: Path) -> str:
    path = config_dir / f"{name}.yaml"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _parse(name: str, raw: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(raw) if raw.strip() else {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError("Top level must be a mapping")
    return data


def _schema_fields(model: type, current: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for field in dataclasses.fields(model):
        default = (
            field.default
            if field.default is not dataclasses.MISSING
            else field.default_factory()  # type: ignore[misc]
            if field.default_factory is not dataclasses.MISSING
            else None
        )
        if dataclasses.is_dataclass(default):
            continue  # nested models are emitted separately
        entries.append(
            {
                "name": field.name,
                "type": getattr(field.type, "__name__", str(field.type)),
                "default": default,
                "current": current.get(field.name, default),
            }
        )
    return entries


def _atomic_write(name: str, content: str, config_dir: Path) -> None:
    path = config_dir / f"{name}.yaml"
    if path.exists():
        path.with_suffix(".yaml.bak").write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def make_config_router(control: AppControl, config_dir: Path = CONFIG_DIR) -> APIRouter:
    router = APIRouter(prefix="/api/config")

    @router.get("")
    def get_all() -> dict:
        result = {}
        for name in CONFIG_FILES:
            raw = _read_raw(name, config_dir)
            try:
                values = _parse(name, raw)
                error = None
            except ConfigError as exc:
                values, error = {}, str(exc)
            result[name] = {"raw": raw, "values": values, "error": error}
        return result

    @router.get("/schema")
    def get_schema() -> dict:
        result: dict[str, Any] = {}
        for name, (model, nested) in CONFIG_FILES.items():
            try:
                current = _parse(name, _read_raw(name, config_dir))
            except ConfigError:
                current = {}
            sections = {"": _schema_fields(model, current)}
            for key, nested_model in nested.items():
                nested_current = current.get(key, {})
                sections[key] = _schema_fields(
                    nested_model, nested_current if isinstance(nested_current, dict) else {}
                )
            result[name] = sections
        return result

    @router.post("/{name}")
    def save(name: str, request: SaveRequest) -> dict:
        if name not in CONFIG_FILES:
            raise HTTPException(status_code=404, detail=f"Unknown config file: {name}")
        if request.raw is None and request.values is None:
            raise HTTPException(status_code=422, detail="Provide 'raw' or 'values'")
        try:
            if request.raw is not None:
                data = _parse(name, request.raw)
                content = request.raw
            else:
                data = request.values or {}
                content = yaml.safe_dump(data, sort_keys=False)
            validate_config_data(name, data)
        except ConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _atomic_write(name, content, config_dir)
        control.mark_restart_required()
        logger.info("Config %s.yaml saved via web UI; restart required", name)
        return {"saved": True, "restart_required": True}

    return router


def make_system_router(control: AppControl) -> APIRouter:
    router = APIRouter(prefix="/api/system")

    @router.get("")
    def system_status() -> dict:
        status = control.get_status()
        return {
            "state": status.state.value,
            "message": status.message,
            "restart_required": status.restart_required,
            "started_at": status.started_at,
        }

    @router.post("/restart")
    def restart() -> dict:
        control.request_restart()
        return {"restarting": True}

    return router
