import json
import os
import platform
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PrinterCapabilities(BaseModel):
    """Capacidades declaradas por un modelo de impresora."""
    cutter: bool = True
    cash_drawer: bool = True
    barcode: bool = True
    qr_code: bool = True
    graphics: bool = True
    color: bool = False
    paper_width_mm: int = 80
    max_print_width_dots: int = 512
    supports_partial_cut: bool = True
    supports_full_cut: bool = False


class PrintOptions(BaseModel):
    """Opciones de impresión."""
    bold: bool = False
    align: str = "left"
    double_width: bool = False
    double_height: bool = False
    auto_cut: bool = True
    open_drawer: bool = False


class PrinterStatus(BaseModel):
    """Estado actual de la impresora."""
    connected: bool = False
    online: bool = False
    paper_out: bool = False
    cover_open: bool = False
    error: Optional[str] = None
    model_detected: Optional[str] = None


class PrinterConfig(BaseModel):
    """Configuración de impresora térmica."""
    enabled: bool = False
    connection_type: Literal["usb", "network", "serial", "bluetooth"] = "network"
    model_profile: str = "generic_escpos"
    # Network
    ip_address: str = "192.168.1.100"
    port: int = 9100
    # USB
    vendor_id: str = ""
    product_id: str = ""
    # Serial
    serial_port: str = "COM3"
    baud_rate: int = 9600
    # Bluetooth
    bluetooth_address: str = ""
    # Opciones
    paper_width: int = 80
    print_density: int = 7  # 0-15 (ESC/POS)
    auto_cut: bool = True
    open_drawer_on_sale: bool = True
    beeper_on_sale: bool = False


class TerminalStatus(BaseModel):
    """Estado actual de la terminal."""
    connected: bool = False
    busy: bool = False
    error: Optional[str] = None
    battery_level: Optional[int] = None


class TerminalConfig(BaseModel):
    """Configuración de terminal de pago."""
    enabled: bool = False
    connection_type: Literal["serial", "network", "smartpos", "clip"] = "serial"
    # Serial
    serial_port: str = "COM4"
    baud_rate: int = 9600
    protocol: Literal["generic", "abm", "iso8583"] = "generic"
    # Network / SmartPOS
    ip_address: str = "192.168.1.50"
    port: int = 8080
    api_key: str = ""
    # Clip
    clip_api_key: str = ""
    # Opciones
    timeout_seconds: int = 120
    currency: str = "MXN"


class AppSettings(BaseModel):
    """Configuración completa del Local Connector."""
    version: str = "2.0.0"
    server_host: str = "127.0.0.1"
    server_port: int = 5000
    log_level: str = "info"

    printer: PrinterConfig = Field(default_factory=PrinterConfig)
    terminal: TerminalConfig = Field(default_factory=TerminalConfig)

    @field_validator("server_port")
    @classmethod
    def validate_port(cls, v):
        if not (1024 <= v <= 65535):
            raise ValueError(f"Puerto inválido: {v}. Debe ser 1024-65535.")
        return v

    def config_path(self) -> Path:
        """Ruta del archivo de configuración según SO."""
        system = platform.system()
        if system == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif system == "Darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        config_dir = base / "DaePoint"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "connector.json"

    def save(self) -> Path:
        """Guarda la configuración a disco."""
        path = self.config_path()
        data = self.model_dump()
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls) -> "AppSettings":
        """Carga la configuración desde disco o crea una por defecto."""
        path = cls.model_validate({}).config_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                return cls.model_validate(raw)
            except Exception:
                pass
        return cls()

    def apply_printer_defaults(self):
        """Aplica valores por defecto del perfil de modelo seleccionado."""
        from .defaults import DEFAULT_PRINTER_PROFILES
        profile = DEFAULT_PRINTER_PROFILES.get(self.printer.model_profile)
        if profile:
            if not self.printer.paper_width:
                self.printer.paper_width = profile.get("paper_width_mm", 80)
            if self.printer.print_density == 7:
                self.printer.print_density = profile.get("print_density", 7)
