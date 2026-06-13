"""Registro de drivers de impresora con auto-detección y perfiles de modelo."""
import logging
from typing import Dict, List, Optional, Type
from .escpos_driver import ESCPOSDriver

logger = logging.getLogger("daepoint.printer")


class PrinterRegistry:
    """Registro centralizado de drivers y perfiles de impresoras."""

    def __init__(self):
        self._drivers: Dict[str, Type[ESCPOSDriver]] = {}
        self._profiles: Dict[str, dict] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Registra el driver ESC/POS genérico y perfiles por defecto."""
        from config.defaults import DEFAULT_PRINTER_PROFILES
        self._drivers["escpos"] = ESCPOSDriver
        self._profiles.update(DEFAULT_PRINTER_PROFILES)

    def register_driver(self, name: str, driver_class: Type[ESCPOSDriver]):
        """Registra un driver personalizado."""
        self._drivers[name] = driver_class
        logger.info(f"Driver registrado: {name}")

    def register_profile(self, name: str, profile: dict):
        """Registra un perfil de modelo."""
        self._profiles[name] = profile
        logger.info(f"Perfil registrado: {name}")

    def get_driver(self, profile_name: str) -> Type[ESCPOSDriver]:
        """Obtiene el driver apropiado para un perfil."""
        # Buscar el perfil
        profile = self._profiles.get(profile_name, {})
        driver_name = profile.get("driver", "escpos")
        return self._drivers.get(driver_name, ESCPOSDriver)

    def get_profile(self, name: str) -> Optional[dict]:
        """Obtiene un perfil de modelo por nombre."""
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        """Lista todos los perfiles disponibles."""
        return list(self._profiles.keys())

    def list_profiles_detail(self) -> List[dict]:
        """Lista perfiles con detalles."""
        return [
            {"name": k, "vendor": v.get("vendor", ""), "model": v.get("model", k)}
            for k, v in self._profiles.items()
        ]


def detect_printers() -> List[dict]:
    """Detecta impresoras conectadas en el sistema.

    Retorna lista de dict con:
        - connection_type: usb/network/serial
        - address: dirección detectada
        - model: modelo detectado (si es posible)
    """
    detected = []

    # Detectar impresoras de red (puerto 9100 estándar ESC/POS)
    try:
        import socket
        for port in [9100, 9101]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(("192.168.1.100", port))
                sock.close()
                if result == 0:
                    detected.append({
                        "connection_type": "network",
                        "address": f"192.168.1.100:{port}",
                        "model": "detectado_red",
                    })
            except Exception:
                pass
    except Exception:
        pass

    # Detectar impresoras USB
    try:
        import usb.core
        # VID:PID de impresoras conocidas
        known_printers = [
            (0x04b8, 0x0202, "Epson"),
            (0x0525, 0x0063, "Generico USB"),
            (0x0416, 0x5011, "Xprinter"),
            (0x04b8, 0x020e, "Epson TM-M30"),
            (0x04b8, 0x020d, "Epson TM-T88VI"),
        ]
        for vid, pid, vendor in known_printers:
            dev = usb.core.find(idVendor=vid, idProduct=pid)
            if dev:
                detected.append({
                    "connection_type": "usb",
                    "address": f"{vid:04x}:{pid:04x}",
                    "model": f"{vendor} USB",
                })
    except ImportError:
        pass
    except Exception:
        pass

    # Detectar impresoras seriales
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Filtrar por descripción común de impresoras
            desc = (port.description or "").lower()
            hwid = (port.hwid or "").lower()
            if any(kw in desc for kw in ["printer", "receipt", "thermal", "pos", "epson", "star"]):
                detected.append({
                    "connection_type": "serial",
                    "address": port.device,
                    "model": port.description or "Serial detectada",
                })
            # Buscar por VID:PID de fabricantes comunes
            if any(vid in hwid for vid in ["04b8", "0525", "0416"]):
                detected.append({
                    "connection_type": "serial",
                    "address": port.device,
                    "model": port.description or "Serial detectada",
                })
    except ImportError:
        pass
    except Exception:
        pass

    return detected


def get_printer_driver(config) -> ESCPOSDriver:
    """Factory method: crea un driver basado en la configuración."""
    registry = PrinterRegistry()
    driver_class = registry.get_driver(config.model_profile)
    return driver_class(config)
