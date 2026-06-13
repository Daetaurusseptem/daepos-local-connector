"""Driver universal ESC/POS para impresoras térmicas.

Soporta conexión USB, Red (TCP/IP), Serial y Bluetooth.
Compatible con ~90% de impresoras térmicas del mercado:
  Epson, Star, Bixolon, Citizen, Xprinter, Hasar, y más.
"""
import io
import socket
import logging
from typing import Optional
from enum import Enum

from config.settings import (
    PrinterConfig, PrinterStatus, PrinterCapabilities, PrintOptions
)

logger = logging.getLogger("daepoint.printer")


class ConnectionType(Enum):
    USB = "usb"
    NETWORK = "network"
    SERIAL = "serial"
    BLUETOOTH = "bluetooth"


class ESCPOSDriver:
    """Driver ESC/POS genérico multi-conexión."""

    # ESC/POS commands
    ESC = b"\x1b"
    GS = b"\x1d"
    FS = b"\x1c"

    def __init__(self, config: PrinterConfig):
        self.config = config
        self._conn: Optional[object] = None
        self._connected = False
        self._status = PrinterStatus()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def status(self) -> PrinterStatus:
        return self._status

    def connect(self) -> bool:
        """Conecta a la impresora según el tipo de conexión configurado."""
        try:
            ct = ConnectionType(self.config.connection_type)
            if ct == ConnectionType.NETWORK:
                return self._connect_network()
            elif ct == ConnectionType.SERIAL:
                return self._connect_serial()
            elif ct == ConnectionType.USB:
                return self._connect_usb()
            elif ct == ConnectionType.BLUETOOTH:
                return self._connect_bluetooth()
            return False
        except Exception as e:
            logger.error(f"Error conectando impresora: {e}")
            self._status = PrinterStatus(connected=False, error=str(e))
            return False

    def disconnect(self):
        """Desconecta de la impresora."""
        if self._conn:
            try:
                if isinstance(self._conn, socket.socket):
                    self._conn.close()
                elif hasattr(self._conn, "close"):
                    self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._connected = False
        self._status = PrinterStatus()

    def _connect_network(self) -> bool:
        """Conexión por red TCP/IP (puerto 9100 por defecto)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.config.ip_address, self.config.port))
            self._conn = sock
            self._connected = True
            self._status = PrinterStatus(
                connected=True, online=True,
                model_detected=self.config.model_profile
            )
            logger.info(f"Impresora conectada por red: {self.config.ip_address}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Error conexión red: {e}")
            self._status = PrinterStatus(connected=False, error=str(e))
            return False

    def _connect_serial(self) -> bool:
        """Conexión por puerto serial (COM/TTY)."""
        try:
            import serial
            ser = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=1,
            )
            self._conn = ser
            self._connected = True
            self._status = PrinterStatus(
                connected=True, online=True,
                model_detected=self.config.model_profile
            )
            logger.info(f"Impresora conectada por serial: {self.config.serial_port}")
            return True
        except ImportError:
            logger.warning("pyserial no instalado. Instale: pip install pyserial")
            self._status = PrinterStatus(connected=False, error="pyserial no instalado")
            return False
        except Exception as e:
            logger.error(f"Error conexión serial: {e}")
            self._status = PrinterStatus(connected=False, error=str(e))
            return False

    def _connect_usb(self) -> bool:
        """Conexión USB por vendor/product ID."""
        try:
            import usb.core
            vid = int(self.config.vendor_id, 16) if self.config.vendor_id else 0x04b8
            pid = int(self.config.product_id, 16) if self.config.product_id else 0x0202
            dev = usb.core.find(idVendor=vid, idProduct=pid)
            if dev is None:
                self._status = PrinterStatus(connected=False, error="Impresora USB no encontrada")
                return False
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
            dev.set_configuration()
            self._conn = dev
            self._connected = True
            self._status = PrinterStatus(
                connected=True, online=True,
                model_detected=self.config.model_profile
            )
            logger.info(f"Impresora USB conectada: {self.config.vendor_id}:{self.config.product_id}")
            return True
        except ImportError:
            logger.warning("pyusb no instalado. Instale: pip install pyusb")
            self._status = PrinterStatus(connected=False, error="pyusb no instalado")
            return False
        except Exception as e:
            logger.error(f"Error conexión USB: {e}")
            self._status = PrinterStatus(connected=False, error=str(e))
            return False

    def _connect_bluetooth(self) -> bool:
        """Conexión Bluetooth (serial over BT)."""
        try:
            import serial
            ser = serial.Serial(
                port=self.config.bluetooth_address,
                baudrate=self.config.baud_rate,
                timeout=1,
            )
            self._conn = ser
            self._connected = True
            self._status = PrinterStatus(
                connected=True, online=True,
                model_detected=self.config.model_profile
            )
            logger.info(f"Impresora Bluetooth conectada: {self.config.bluetooth_address}")
            return True
        except Exception as e:
            logger.error(f"Error conexión Bluetooth: {e}")
            self._status = PrinterStatus(connected=False, error=str(e))
            return False

    def _send(self, data: bytes) -> bool:
        """Envía datos brutos a la impresora."""
        if not self._connected or not self._conn:
            return False
        try:
            if isinstance(self._conn, socket.socket):
                self._conn.sendall(data)
            elif hasattr(self._conn, "write"):
                self._conn.write(data)
            return True
        except Exception as e:
            logger.error(f"Error enviando datos: {e}")
            self._connected = False
            self._status = PrinterStatus(connected=False, error=f"Error de envío: {e}")
            return False

    # ─── Comandos ESC/POS de alto nivel ───

    def initialize(self) -> bool:
        """Inicializa la impresora (reset)."""
        return self._send(self.ESC + b"@")

    def set_density(self, density: int = 7):
        """Configura densidad de impresión (0-15)."""
        d = max(0, min(15, density))
        return self._send(self.GS + b"\x7c" + bytes([d]))

    def set_codepage(self, codepage: str = "cp437"):
        """Configura codepage de caracteres."""
        codepage_map = {
            "cp437": 0, "cp850": 2, "cp852": 18, "cp858": 19,
            "cp860": 3, "cp863": 6, "cp865": 8, "cp1252": 16,
        }
        cp_byte = codepage_map.get(codepage, 0)
        return self._send(self.ESC + b"t" + bytes([cp_byte]))

    def cut_paper(self, lines: int = 3, partial: bool = True):
        """Corta el papel (parcial o completo)."""
        if partial:
            return self._send(self.GS + b"V" + bytes([1, lines * 10]))
        else:
            return self._send(self.GS + b"V" + bytes([0, lines * 10]))

    def open_drawer(self, pin: int = 2) -> bool:
        """Abre el cajón de dinero."""
        p = 0 if pin == 2 else 1
        return self._send(self.ESC + b"p" + bytes([p, 40, 80]))

    def beep(self, count: int = 1, duration: int = 2) -> bool:
        """Envía beep al buzzer."""
        return self._send(self.ESC + b"B" + bytes([count, duration]))

    def print_text(self, text: str, bold: bool = False, align: str = "left",
                   double_width: bool = False, double_height: bool = False) -> bool:
        """Imprime texto con formato."""
        # Negrita
        self._send(self.ESC + b"E" + bytes([1 if bold else 0]))
        # Alineación
        align_map = {"left": 0, "center": 1, "right": 2}
        self._send(self.ESC + b"a" + bytes([align_map.get(align, 0)]))
        # Doble ancho/alto
        if double_width or double_height:
            n = (2 if double_width else 0) | (4 if double_height else 0) | (8 if double_height else 0)
            self._send(self.GS + b"!" + bytes([n]))
        # Texto
        result = self._send(text.encode("cp437", errors="replace") + b"\n")
        # Reset formato
        self._send(self.ESC + b"E" + b"\x00")
        self._send(self.GS + b"!" + b"\x00")
        return result

    def print_line(self, text: str):
        """Imprime una línea simple."""
        return self.print_text(text)

    def print_centered(self, text: str, bold: bool = False):
        """Imprime texto centrado."""
        return self.print_text(text, bold=bold, align="center")

    def print_double_width(self, text: str, centered: bool = False):
        """Imprime texto en doble ancho."""
        return self.print_text(text, double_width=True,
                               align="center" if centered else "left")

    def print_double_height(self, text: str, centered: bool = False):
        """Imprime texto en doble alto."""
        return self.print_text(text, double_height=True,
                               align="center" if centered else "left")

    def print_barcode(self, barcode_type: str, data: str) -> bool:
        """Imprime código de barras."""
        # ESC/POS barcode codes
        barcode_map = {
            "CODE128": 73, "CODE39": 39, "EAN13": 2, "EAN8": 3,
            "UPCA": 65, "ITF": 0, "CODABAR": 6,
        }
        bc_type = barcode_map.get(barcode_type.upper(), 73)  # Default CODE128
        # GS H n (barcode height)
        self._send(self.GS + b"h" + bytes([50]))
        # GS H n (barcode width)
        self._send(self.GS + b"w" + bytes([2]))
        # GS k m d... NUL (barcode)
        self._send(self.GS + b"k" + bytes([bc_type]) + data.encode() + b"\x00")
        return True

    def print_qr(self, data: str, size: int = 6) -> bool:
        """Imprime código QR."""
        # GS ( k (QR code)
        self._send(self.GS + b"(k" + bytes([4, 0, 49, 65, 50, 0]))
        # Tamaño módulo
        self._send(self.GS + b"(k" + bytes([3, 0, 49, 67, size]))
        # Error correction
        self._send(self.GS + b"(k" + bytes([3, 0, 49, 69, 48]))
        # Datos
        qr_data = data.encode()
        self._send(self.GS + b"(k" + bytes([len(qr_data) + 3, 0, 49, 80, 48]) + qr_data)
        # Print
        self._send(self.GS + b"(k" + bytes([3, 0, 49, 81, 48]))
        return True

    def print_receipt(self, content: str, options: Optional[PrintOptions] = None):
        """Imprime un ticket completo desde contenido de texto."""
        if not self._connected:
            logger.error("No hay impresora conectada")
            return False

        self.initialize()
        self.set_codepage("cp437")

        lines = content.split("\n")
        for line in lines:
            if line.strip() == "":
                self._send(b"\n")
            elif line.startswith("=="):  # Doble ancho
                self.print_double_width(line.replace("=", "").strip(), centered=True)
            elif line.startswith("--"):  # Negrita centrado
                self.print_centered(line.replace("-", "").strip(), bold=True)
            elif line.startswith(">>"):  # Centrado
                self.print_centered(line.replace(">", "").strip())
            elif line.startswith("[BARCODE:"):  # Código de barras
                barcode_data = line.split(":")[1].rstrip("]")
                self.print_barcode("CODE128", barcode_data)
            elif line.startswith("[QR:"):  # QR code
                qr_data = line.split(":")[1].rstrip("]")
                self.print_qr(qr_data)
            else:
                self.print_line(line)

        # Cortar papel al final
        if self.config.auto_cut:
            self.cut_paper(partial=True)

        # Abrir cajón si está configurado
        if self.config.open_drawer_on_sale:
            self.open_drawer(pin=2)

        return True
