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


def get_printer_driver(config) -> ESCPOSDriver:
    """Factory method: crea un driver basado en la configuración."""
    registry = PrinterRegistry()
    driver_class = registry.get_driver(config.model_profile)
    return driver_class(config)
