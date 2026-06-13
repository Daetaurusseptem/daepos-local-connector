"""DaePoint Local Connector - API Server (FastAPI)."""
import sys
import os
import time
import uuid
import logging

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from config.settings import AppSettings, PrinterConfig, TerminalConfig

logger = logging.getLogger("daepoint.api")

# ─── Load settings ───
settings = AppSettings.load()

# ─── Initialize drivers based on config ───

def _init_printer():
    """Inicializa el driver de impresora según configuración."""
    if not settings.printer.enabled:
        return None
    try:
        if settings.printer.connection_type == "simulator":
            return "simulator"
        from hardware.printer.escpos_driver import ESCPOSDriver
        driver = ESCPOSDriver(settings.printer)
        if driver.connect():
            logger.info("Impresora conectada correctamente")
            return driver
        else:
            logger.warning(f"No se pudo conectar impresora: {driver.status.error}")
            return None
    except Exception as e:
        logger.error(f"Error inicializando impresora: {e}")
        return None


def _init_terminal():
    """Inicializa el driver de terminal según configuración."""
    if not settings.terminal.enabled:
        return None
    try:
        if settings.terminal.connection_type == "simulator":
            return "simulator"
        from hardware.terminal.serial_driver import SerialTerminalDriver
        from hardware.terminal.smartpos_driver import SmartPOSTerminalDriver

        conn = settings.terminal.connection_type
        if conn in ("serial",):
            driver = SerialTerminalDriver(settings.terminal)
        elif conn in ("network", "smartpos"):
            driver = SmartPOSTerminalDriver(settings.terminal)
        else:
            return "simulator"

        if driver.connect():
            logger.info("Terminal conectada correctamente")
            return driver
        else:
            logger.warning("No se pudo conectar terminal")
            return None
    except Exception as e:
        logger.error(f"Error inicializando terminal: {e}")
        return None


printer_driver = _init_printer()
terminal_driver = _init_terminal()

# ─── FastAPI App ───

app = FastAPI(
    title="DaePoint Local Connector",
    version="2.0.0",
    description="API para impresión de tickets y cobro con terminal de pago.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ───

class PrintRequest(BaseModel):
    content: str
    printer_name: str = "default"
    paper_size: str = "80mm"
    printer_type: str = "receipt"
    auto_cut: bool = True
    open_drawer: bool = True


class PaymentRequest(BaseModel):
    amount: float
    currency: str = "MXN"


class ConfigUpdateRequest(BaseModel):
    section: str  # "printer" or "terminal"
    config: dict


# ─── Endpoints ───

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "DaePoint Local Connector v2.0",
        "printer_connected": printer_driver is not None,
        "terminal_connected": terminal_driver is not None,
        "config_path": str(settings.config_path()),
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/status")
def get_status():
    """Estado detallado del connector."""
    printer_status = "disconnected"
    terminal_status = "disconnected"

    if printer_driver == "simulator":
        printer_status = "simulator"
    elif printer_driver is not None:
        printer_status = "connected" if printer_driver.connected else "error"

    if terminal_driver == "simulator":
        terminal_status = "simulator"
    elif terminal_driver is not None:
        terminal_status = "connected" if terminal_driver.connected else "error"

    return {
        "printer": {
            "enabled": settings.printer.enabled,
            "status": printer_status,
            "connection_type": settings.printer.connection_type,
            "model": settings.printer.model_profile,
        },
        "terminal": {
            "enabled": settings.terminal.enabled,
            "status": terminal_status,
            "connection_type": settings.terminal.connection_type,
        },
    }


# ─── Printer Endpoints ───

@app.post("/print")
def print_receipt(request: PrintRequest):
    """Envía un ticket a la impresora."""
    if printer_driver is None and not settings.printer.enabled:
        raise HTTPException(400, "Impresora no habilitada. Configure en la GUI.")

    if printer_driver == "simulator":
        logger.info(f"[SIMULADOR] Ticket: {request.content[:50]}...")
        return {"status": "success", "message": "Ticket enviado (simulador)", "mode": "simulator"}

    if printer_driver is None:
        raise HTTPException(503, "Impresora no conectada")

    try:
        printer_driver.print_receipt(request.content)
        return {"status": "success", "message": "Ticket impreso"}
    except Exception as e:
        logger.error(f"Error imprimiendo: {e}")
        raise HTTPException(500, f"Error de impresión: {e}")


@app.post("/open-drawer")
def open_drawer():
    """Abre el cajón de dinero."""
    if printer_driver == "simulator":
        return {"status": "success", "message": "Cajón abierto (simulador)", "mode": "simulator"}

    if printer_driver is None:
        raise HTTPException(503, "Impresora no conectada")

    try:
        result = printer_driver.open_drawer()
        return {"status": "success" if result else "error", "message": "Cajón abierto" if result else "Error abriendo cajón"}
    except Exception as e:
        raise HTTPException(500, f"Error: {e}")


@app.get("/printer/status")
def printer_status():
    """Estado de la impresora."""
    if printer_driver == "simulator":
        return {"connected": True, "online": True, "mode": "simulator"}
    if printer_driver is None:
        return {"connected": False, "online": False}
    return printer_driver.status.model_dump()


# ─── Payment Endpoints ───

@app.post("/payment/charge")
def charge_payment(request: PaymentRequest):
    """Realiza un cobro con la terminal."""
    if terminal_driver is None and not settings.terminal.enabled:
        raise HTTPException(400, "Terminal no habilitada. Configure en la GUI.")

    if terminal_driver == "simulator":
        ref = f"AUTH-SIM-{str(uuid.uuid4())[:8]}"
        return {
            "status": "approved",
            "reference": ref,
            "amount": request.amount,
            "mode": "simulator",
        }

    if terminal_driver is None:
        raise HTTPException(503, "Terminal no conectada")

    try:
        result = terminal_driver.charge(request.amount, request.currency)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error cobrando: {e}")
        raise HTTPException(500, f"Error de cobro: {e}")


@app.post("/payment/refund")
def refund_payment(transaction_id: str, amount: float):
    """Realiza un reembolso."""
    if terminal_driver == "simulator":
        return {"status": "approved", "reference": transaction_id, "amount": amount, "mode": "simulator"}
    if terminal_driver is None:
        raise HTTPException(503, "Terminal no conectada")

    result = terminal_driver.refund(transaction_id, amount)
    return result.model_dump()


@app.get("/terminal/status")
def terminal_status_endpoint():
    """Estado de la terminal."""
    if terminal_driver == "simulator":
        return {"connected": True, "online": True, "mode": "simulator"}
    if terminal_driver is None:
        return {"connected": False, "online": False}
    return terminal_driver.get_status()


# ─── Config Endpoints ───

@app.get("/config")
def get_config():
    """Obtiene la configuración actual."""
    return settings.model_dump()


@app.post("/config")
def update_config(request: ConfigUpdateRequest):
    """Actualiza la configuración."""
    global printer_driver, terminal_driver

    try:
        if request.section == "printer":
            settings.printer = PrinterConfig(**request.config)
        elif request.section == "terminal":
            settings.terminal = TerminalConfig(**request.config)
        else:
            raise HTTPException(400, f"Sección desconocida: {request.section}")

        settings.save()
        return {"status": "success", "message": f"Config {request.section} actualizada"}
    except Exception as e:
        raise HTTPException(500, f"Error actualizando config: {e}")


@app.post("/config/reload")
def reload_config():
    """Recarga la configuración desde disco."""
    global settings, printer_driver, terminal_driver
    settings = AppSettings.load()
    printer_driver = _init_printer()
    terminal_driver = _init_terminal()
    return {"status": "success", "message": "Configuración recargada"}


@app.get("/config/path")
def config_path():
    """Retorna la ruta del archivo de configuración."""
    return {"path": str(settings.config_path())}


# ─── Discovery Endpoints ───

@app.get("/detect/printers")
def detect_printers():
    """Detecta impresoras conectadas."""
    from hardware.discovery import detect_printers as _detect
    return {"printers": _detect()}


@app.get("/detect/terminals")
def detect_terminals():
    """Detecta terminales conectadas."""
    from hardware.discovery import detect_terminals as _detect
    return {"terminals": _detect()}


# ─── Printer Profiles ───

@app.get("/profiles/printers")
def list_printer_profiles():
    """Lista perfiles de impresoras disponibles."""
    from config.defaults import DEFAULT_PRINTER_PROFILES
    return {"profiles": DEFAULT_PRINTER_PROFILES}
