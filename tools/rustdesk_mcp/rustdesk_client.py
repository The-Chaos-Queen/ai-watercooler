"""RustDesk Pro API client for MCP tool wrappers.

This client is intentionally conservative:
- It uses environment-configurable endpoint paths because RustDesk deployments
  can vary by version and reverse proxy layout.
- It returns normalized dictionaries where possible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


class RustDeskError(RuntimeError):
    """Raised when the RustDesk API returns an error."""


@dataclass
class RustDeskConfig:
    base_url: str
    api_token: str
    timeout_s: float = 20.0

    # Endpoint paths (override with env vars if your deployment differs)
    devices_path: str = "/api/devices"
    assign_path: str = "/api/devices/assign"
    disable_path_template: str = "/api/devices/{device_id}/disable"
    audits_path: str = "/api/audits"

    @classmethod
    def from_env(cls) -> "RustDeskConfig":
        base_url = os.getenv("RUSTDESK_BASE_URL", "").strip().rstrip("/")
        api_token = os.getenv("RUSTDESK_API_TOKEN", "").strip()

        if not base_url:
            raise RustDeskError("RUSTDESK_BASE_URL is not set")
        if not api_token:
            raise RustDeskError("RUSTDESK_API_TOKEN is not set")

        timeout_s_raw = os.getenv("RUSTDESK_TIMEOUT_S", "20").strip()
        try:
            timeout_s = float(timeout_s_raw)
        except ValueError as exc:
            raise RustDeskError(f"Invalid RUSTDESK_TIMEOUT_S: {timeout_s_raw}") from exc

        return cls(
            base_url=base_url,
            api_token=api_token,
            timeout_s=timeout_s,
            devices_path=os.getenv("RUSTDESK_DEVICES_PATH", "/api/devices").strip(),
            assign_path=os.getenv("RUSTDESK_ASSIGN_PATH", "/api/devices/assign").strip(),
            disable_path_template=os.getenv(
                "RUSTDESK_DISABLE_PATH_TEMPLATE", "/api/devices/{device_id}/disable"
            ).strip(),
            audits_path=os.getenv("RUSTDESK_AUDITS_PATH", "/api/audits").strip(),
        )


class RustDeskClient:
    def __init__(self, config: Optional[RustDeskConfig] = None) -> None:
        self.config = config or RustDeskConfig.from_env()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.config.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.config.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = self._url(path)
        response = self._session.request(
            method=method,
            url=url,
            timeout=self.config.timeout_s,
            **kwargs,
        )

        content_type = response.headers.get("Content-Type", "")
        payload: Dict[str, Any]
        if "application/json" in content_type:
            payload = response.json()
        else:
            payload = {"raw": response.text}

        if response.status_code >= 400:
            raise RustDeskError(
                f"RustDesk API error {response.status_code} at {path}: {payload}"
            )

        return payload

    @staticmethod
    def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        for key in ("items", "data", "devices", "rows", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []

    def healthcheck(self) -> Dict[str, Any]:
        """Cheap health probe using device list endpoint."""
        payload = self._request("GET", self.config.devices_path, params={"limit": 1})
        return {
            "ok": True,
            "base_url": self.config.base_url,
            "detected_items": len(self._extract_items(payload)),
            "raw_keys": sorted(payload.keys()),
        }

    def list_devices(
        self,
        query: str = "",
        status: str = "all",
        limit: int = 50,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": max(1, min(limit, 500))}
        if query:
            params["q"] = query
        if status and status.lower() != "all":
            params["status"] = status

        payload = self._request("GET", self.config.devices_path, params=params)
        items = self._extract_items(payload)

        normalized = []
        for item in items:
            normalized.append(
                {
                    "device_id": item.get("id") or item.get("device_id"),
                    "hostname": item.get("hostname") or item.get("name"),
                    "owner": item.get("owner") or item.get("user") or item.get("user_id"),
                    "online": item.get("online"),
                    "raw": item,
                }
            )

        return {
            "count": len(normalized),
            "devices": normalized,
            "endpoint": self.config.devices_path,
        }

    def assign_device(
        self,
        device_id: str,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        if not device_id:
            raise RustDeskError("device_id is required")
        if not user_id and not group_id:
            raise RustDeskError("either user_id or group_id is required")

        body: Dict[str, Any] = {"device_id": device_id}
        if user_id:
            body["user_id"] = user_id
        if group_id:
            body["group_id"] = group_id
        if note:
            body["note"] = note

        payload = self._request("POST", self.config.assign_path, json=body)
        return {
            "ok": True,
            "endpoint": self.config.assign_path,
            "request": body,
            "response": payload,
        }

    def disable_device(self, device_id: str, reason: str = "") -> Dict[str, Any]:
        if not device_id:
            raise RustDeskError("device_id is required")

        path = self.config.disable_path_template.format(device_id=device_id)
        body: Dict[str, Any] = {}
        if reason:
            body["reason"] = reason

        payload = self._request("POST", path, json=body)
        return {
            "ok": True,
            "endpoint": path,
            "request": {"device_id": device_id, "reason": reason or None},
            "response": payload,
        }

    def audit_events(self, limit: int = 50, actor: str = "", device_id: str = "") -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": max(1, min(limit, 500))}
        if actor:
            params["actor"] = actor
        if device_id:
            params["device_id"] = device_id

        payload = self._request("GET", self.config.audits_path, params=params)
        items = self._extract_items(payload)

        normalized = []
        for item in items:
            normalized.append(
                {
                    "timestamp": item.get("timestamp") or item.get("created_at"),
                    "actor": item.get("actor") or item.get("user"),
                    "action": item.get("action") or item.get("event"),
                    "device_id": item.get("device_id") or item.get("target_id"),
                    "raw": item,
                }
            )

        return {
            "count": len(normalized),
            "events": normalized,
            "endpoint": self.config.audits_path,
        }
