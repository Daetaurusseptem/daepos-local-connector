"""Auto-detección de hardware conectado al sistema."""
import logging
import platform
from typing import List, Dict

logger = logging.getLogger("daepoint.discovery")


def detect_printers() -> List[Dict]:
    """Detecta impresoras térmicas conectadas."""
    detected = []

    # Red local - buscar en subred común
    try:
        import socket
        import struct

        # Obtener IP local para determinar subred
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "192.168.1.100"
            s.close()

        # Extraer prefijo de red (ej: 192.168.1)
        parts = local_ip.split(".")
        prefix = ".".join(parts[:3])

        # Escanear puertos comunes de impresora en la subred
        for host_suffix in range(1, 255):
            host = f"{prefix}.{host_suffix}"
            for port in [9100, 9101, 9102]:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.3)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    if result == 0:
                        # Intentar identificar modelo
                        model = _identify_printer(host, port)
                        detected.append({
                            "connection_type": "network",
                            "address": f"{host}:{port}",
                            "model": model,
                            "brand": _extract_brand(model),
                        })
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Error escaneando red: {e}")

    # USB
    try:
        import usb.core
        import usb.util

        known_printers = [
            (0x04b8, 0x0202, "Epson", "TM-T20"),
            (0x04b8, 0x020d, "Epson", "TM-T88VI"),
            (0x04b8, 0x020e, "Epson", "TM-M30"),
            (0x04b8, 0x020f, "Epson", "TM-T20III"),
            (0x04b8, 0x021c, "Epson", "TM-T88VI-DT"),
            (0x0525, 0x0063, "Generico", "USB Printer"),
            (0x0416, 0x5011, "Xprinter", "XP-80C"),
            (0x0416, 0x5012, "Xprinter", "XP-N160II"),
            (0x04b8, 0x0220, "Epson", "TM-L90"),
            (0x04b8, 0x0221, "Epson", "TM-L90LF"),
        ]
        for vid, pid, brand, model in known_printers:
            dev = usb.core.find(idVendor=vid, idProduct=pid)
            if dev:
                detected.append({
                    "connection_type": "usb",
                    "address": f"{vid:04x}:{pid:04x}",
                    "model": f"{brand} {model}",
                    "brand": brand,
                })
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Error detectando USB: {e}")

    # Serial
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = (port.description or "").lower()
            hwid = (port.hwid or "").lower()

            # Por descripción
            if any(kw in desc for kw in [
                "printer", "receipt", "thermal", "pos", "epson", "star",
                "bixolon", "citizen", "xprinter", "hasar"
            ]):
                detected.append({
                    "connection_type": "serial",
                    "address": port.device,
                    "model": port.description or "Serial detectada",
                    "brand": _extract_brand(port.description or ""),
                })
            # Por VID:PID conocido
            elif any(vid in hwid for vid in ["04b8", "0525", "0416", "1c87", "0fe4"]):
                detected.append({
                    "connection_type": "serial",
                    "address": port.device,
                    "model": port.description or "Serial detectada",
                    "brand": _extract_brand(port.description or ""),
                })
    except ImportError:
        logger.warning("pyserial no instalado - detección serial deshabilitada")
    except Exception as e:
        logger.warning(f"Error detectando serial: {e}")

    return detected


def detect_terminals() -> List[Dict]:
    """Detecta terminales de pago conectadas."""
    detected = []

    # Serial
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = (port.description or "").lower()
            hwid = (port.hwid or "").lower()

            if any(kw in desc for kw in [
                "terminal", "tpv", " Ingenico", "Verifone", "PAX",
                "card reader", "payment"
            ]):
                detected.append({
                    "connection_type": "serial",
                    "address": port.device,
                    "model": port.description or "Terminal detectada",
                })
            elif any(vid in hwid for vid in ["0b00", "08e6", "0c2e"]):
                detected.append({
                    "connection_type": "serial",
                    "address": port.device,
                    "model": port.description or "Terminal detectada",
                })
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Error detectando terminales seriales: {e}")

    # SmartPOS por mDNS/SSDP
    try:
        # Implementar descubrimiento mDNS/SSDP para terminales WiFi
        pass
    except Exception:
        pass

    return detected


def _identify_printer(host: str, port: int) -> str:
    """Intenta identificar el modelo de impresora por red."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((host, port))

        # Enviar ESC/POS status request: GS I (Información)
        sock.send(b"\x1d\x49\x01")
        time.sleep(0.5)
        response = sock.recv(64)
        sock.close()

        if response:
            # Intentar parsear respuesta para identificar modelo
            return _parse_status_response(response)
    except Exception:
        pass
    return "Desconocida"


def _parse_status_response(response: bytes) -> str:
    """Parsea respuesta de estado ESC/POS para identificar modelo."""
    # Respuesta típica contiene el nombre del modelo
    try:
        text = response.decode("ascii", errors="ignore").strip()
        if text:
            return text[:50]
    except Exception:
        pass
    return "Desconocida"


def _extract_brand(text: str) -> str:
    """Extrae marca del texto de descripción."""
    brands = {
        "epson": "Epson", "star": "Star", "bixolon": "Bixolon",
        "citizen": "Citizen", "xprinter": "Xprinter", "hasar": "Hasar",
        "ingenico": "Ingenico", "verifone": "Verifone", "pax": "PAX",
    }
    text_lower = text.lower()
    for keyword, brand in brands.items():
        if keyword in text_lower:
            return brand
    return "Otro"


def auto_configure_printer(detected: Dict) -> Dict:
    """Genera configuración óptima para una impresora detectada."""
    from config.defaults import DEFAULT_PRINTER_PROFILES

    model = detected.get("model", "").lower()
    brand = detected.get("brand", "").lower()
    conn_type = detected.get("connection_type", "network")

    # Buscar perfil por marca/modelo
    profile_key = "generic_escpos"
    for key, profile in DEFAULT_PRINTER_PROFILES.items():
        if brand and brand in profile.get("vendor", "").lower():
            profile_key = key
            break

    config = {
        "enabled": True,
        "connection_type": conn_type,
        "model_profile": profile_key,
        "paper_width": 80,
        "print_density": 7,
        "auto_cut": True,
        "open_drawer_on_sale": True,
    }

    if conn_type == "network":
        addr = detected.get("address", "192.168.1.100:9100")
        parts = addr.split(":")
        config["ip_address"] = parts[0]
        config["port"] = int(parts[1]) if len(parts) > 1 else 9100
    elif conn_type == "usb":
        config["vendor_id"] = detected.get("address", "04b8:0202").split(":")[0]
        config["product_id"] = detected.get("address", "04b8:0202").split(":")[1]
    elif conn_type == "serial":
        config["serial_port"] = detected.get("address", "COM3")
        config["baud_rate"] = 9600

    return config


def auto_configure_terminal(detected: Dict) -> Dict:
    """Genera configuración óptima para una terminal detectada."""
    config = {
        "enabled": True,
        "connection_type": "serial",
        "serial_port": detected.get("address", "COM4"),
        "baud_rate": 9600,
        "protocol": "generic",
        "timeout_seconds": 120,
        "currency": "MXN",
    }
    return config


# Importar time para usar en _identify_printer
import time
