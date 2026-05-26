"""detect_location_tag — poll the ROSBot AprilTag HTTP server.

When a physical AprilTag is visible to the ROSBot's camera, this tool
returns the location name, description, and talking points so Reachy
can describe where the visitor is standing.

The ROSBot must be running apriltag_http_server.py (port 8767 by default).
Set the APRILTAG_SERVER_URL environment variable if the ROSBot is on a
different IP or port:

    export APRILTAG_SERVER_URL=http://192.168.0.10:8767
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import httpx

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies

logger = logging.getLogger(__name__)

# Override via environment variable to point at the ROSBot's actual IP/port
_BASE_URL = os.getenv("APRILTAG_SERVER_URL", "http://localhost:8767")
_TIMEOUT_S = float(os.getenv("APRILTAG_SERVER_TIMEOUT", "3.0"))


class DetectLocationTag(Tool):
    """Check whether the ROSBot camera can see a location marker (AprilTag)."""

    name = "detect_location_tag"
    description = (
        "Check if the ROSBot camera has detected a location marker (AprilTag) nearby. "
        "Returns the location name, description, and talking points if a known tag is visible. "
        "Call this when: a visitor asks 'what is this?', 'where are we?', 'what's here?', "
        "'describe this area', or when you want to proactively identify the current location."
    )
    parameters_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def __call__(self, deps: ToolDependencies, **_kwargs: Any) -> Dict[str, Any]:
        url = f"{_BASE_URL.rstrip('/')}/apriltag/status"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("AprilTag server unreachable at %s: %s", url, e)
            return {
                "detected": False,
                "error": "Cannot reach the AprilTag server on the ROSBot.",
                "hint": (
                    "Make sure apriltag_http_server.py is running on the ROSBot "
                    f"and that APRILTAG_SERVER_URL is set correctly (currently: {_BASE_URL})."
                ),
            }
        except Exception as e:
            logger.error("Unexpected error from AprilTag server: %s", e)
            return {
                "detected": False,
                "error": str(e),
            }

        if not data.get("detected", False):
            return {
                "detected": False,
                "message": "No location marker is currently visible to the robot camera.",
            }

        logger.info(
            "Location tag detected: id=%s → '%s'",
            data.get("tag_id"),
            data.get("name"),
        )
        return {
            "detected": True,
            "tag_id": data.get("tag_id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "talking_points": data.get("talking_points", []),
        }
