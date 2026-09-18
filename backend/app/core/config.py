from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8443
    database_url: str = "sqlite:///runtime/database/goldnest.sqlite3"
    storage_root: Path = Path("runtime/storage")
    jwt_secret: str = ""
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    tls_cert_path: Path = Path("certs/server.crt")
    tls_key_path: Path = Path("certs/server.key")
    yoloe_model: Path = Path("models/yoloe/yoloe-26s-seg.pt")
    yoloe_device: str = "auto"
    yoloe_prompts: str = "jewelry,gold jewelry,bangle,earring,ring,necklace"
    yoloe_confidence: float = 0.15
    yoloe_image_size: int = 960
    visual_prompts_enabled: bool = True
    visual_prompt_confidence: float = 0.08
    dedup_mask_iou: float = 0.55
    dedup_containment: float = 0.80
    min_mask_pixels: int = 80
    min_mask_fraction: float = 0.00003
    max_mask_fraction: float = 0.80
    inspyrenet_model: Path = Path("models/inspyrenet/ckpt_fast.pth")
    inspyrenet_device: str = "cpu"
    inspyrenet_enabled: bool = True
    siglip_model_dir: Path = Path("models/siglip2")
    siglip_provider: str = "auto"
    correction_gallery_path: Path = Path("runtime/model_state/jewelry_correction_gallery.npz")
    keep_uploads: bool = True
    retention_days: int = 0
    display_timezone: str = "Asia/Kolkata"

    def path(self, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_ROOT / value

    @property
    def resolved_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            path = Path(self.database_url.removeprefix("sqlite:///"))
            return f"sqlite:///{self.path(path).as_posix()}"
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
