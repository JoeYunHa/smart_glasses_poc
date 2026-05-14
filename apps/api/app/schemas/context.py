from enum import Enum
from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    baseline = "baseline"
    optimized = "optimized"


class DeviceInfo(BaseModel):
    device_id: str
    name: str
    type: str
    supported_actions: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    requires_confirmation: bool = False
    state: dict = Field(default_factory=dict)


class GpsContext(BaseModel):
    latitude: float
    longitude: float
    location_type: str = ""
    place_name: str = ""


class ContextRequest(BaseModel):
    user_request: str
    gps: GpsContext | None = None
    nearby_devices: list[DeviceInfo] = Field(default_factory=list)
    mode: AgentMode = AgentMode.optimized
