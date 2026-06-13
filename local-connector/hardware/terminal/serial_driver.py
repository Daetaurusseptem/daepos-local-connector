"""Driver de terminal de pago por puerto serial (COM/TTY).

Soporta comunicación con terminales bancarias mediante protocolos:
- Genérico (STX/ETX frames)
- ABM (formato mexicano)
- ISO8583
"""
import logging
import threading
import time
import uuid
from typing import Optional

from .base import TerminalDriver, ChargeResult

logger = logging.getLogger("daepoint.terminal")


class SerialTerminalDriver(TerminalDriver):
    """Driver para terminal de pago por serial."""

    STX = b"\x02"
    ETX = b"\x03"
    ACK = b"\x06"
    NAK = b"\x15"

    def __init__(self, config):
        self.config = config
        self._conn = None
        self._connected = False
        self._busy = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Conecta al puerto serial."""
        try:
            import serial
            self._conn = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=self.config.timeout_seconds,
            )
            self._connected = True
            logger.info(f"Terminal conectada: {self.config.serial_port}")
            return True
        except ImportError:
            logger.warning("pyserial no instalado. Instale: pip install pyserial")
            return False
        except Exception as e:
            logger.error(f"Error conexión serial terminal: {e}")
            self._connected = False
            return False

    def disconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._connected = False

    def _send_command(self, command: bytes, timeout: float = 30) -> Optional[bytes]:
        """Envía comando y espera respuesta."""
        if not self._connected or not self._conn:
            return None

        try:
            self._conn.write(self.STX + command + self.ETX)
            # Esperar ACK o NAK
            response = self._conn.read(1)
            if response == self.ACK:
                # Leer datos de respuesta
                data = self._conn.read(1024)
                return data
            elif response == self.NAK:
                logger.warning("Terminal rechazó comando (NAK)")
                return None
            else:
                logger.warning(f"Respuesta inesperada: {response}")
                return None
        except Exception as e:
            logger.error(f"Error enviando comando: {e}")
            return None

    def charge(self, amount: float, currency: str = "MXN") -> ChargeResult:
        """Realiza un cobro por serial."""
        if self._busy:
            return ChargeResult(status="error", message="Terminal ocupada")

        self._busy = True
        try:
            # Formato genérico: cobrar monto
            amount_str = f"{amount:.2f}"
            command = f"CHARGE|{amount_str}|{currency}".encode()

            response = self._send_command(command, timeout=self.config.timeout_seconds)
            if response is None:
                return ChargeResult(status="error", message="Sin respuesta de terminal")

            # Parsear respuesta genérica
            resp_str = response.decode(errors="replace")
            parts = resp_str.split("|")

            if len(parts) >= 2:
                status = parts[0].strip()
                if status.upper() in ("APPROVED", "APROBADO", "OK"):
                    ref = parts[1].strip() if len(parts) > 1 else str(uuid.uuid4())[:8]
                    return ChargeResult(
                        status="approved",
                        reference=ref,
                        amount=amount,
                        auth_code=ref,
                        transaction_id=str(uuid.uuid4()),
                    )
                else:
                    return ChargeResult(
                        status="declined",
                        message=parts[1].strip() if len(parts) > 1 else "Declinada",
                        amount=amount,
                    )
            else:
                return ChargeResult(status="error", message="Formato de respuesta inválido")
        finally:
            self._busy = False

    def refund(self, transaction_id: str, amount: float) -> ChargeResult:
        """Realiza un reembolso."""
        if self._busy:
            return ChargeResult(status="error", message="Terminal ocupada")

        self._busy = True
        try:
            command = f"REFUND|{transaction_id}|{amount:.2f}".encode()
            response = self._send_command(command, timeout=self.config.timeout_seconds)
            if response is None:
                return ChargeResult(status="error", message="Sin respuesta de terminal")

            resp_str = response.decode(errors="replace")
            parts = resp_str.split("|")

            if len(parts) >= 2 and parts[0].strip().upper() in ("APPROVED", "APROBADO", "OK"):
                return ChargeResult(
                    status="approved",
                    reference=transaction_id,
                    amount=amount,
                )
            return ChargeResult(status="declined", message="Reembolso rechazado")
        finally:
            self._busy = False

    def cancel(self) -> bool:
        """Cancela la operación actual."""
        try:
            command = b"CANCEL"
            response = self._send_command(command, timeout=5)
            return response is not None
        except Exception:
            return False

    def get_status(self) -> dict:
        """Obtiene estado de la terminal."""
        if not self._connected:
            return {"connected": False, "error": "No conectada"}

        try:
            command = b"STATUS"
            response = self._send_command(command, timeout=5)
            if response:
                return {"connected": True, "online": True, "response": response.decode(errors="replace")}
            return {"connected": True, "online": False}
        except Exception as e:
            return {"connected": True, "online": False, "error": str(e)}
