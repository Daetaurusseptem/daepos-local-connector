"""Driver de terminal de pago SmartPOS (WiFi/TCP/IP).

Soporta terminales bancarias inteligentes con API HTTP:
- Ingenico Lane/Move/Desk
- Verifone
- PAX
"""
import logging
import time
import uuid
from typing import Optional

from .base import TerminalDriver, ChargeResult

logger = logging.getLogger("daepoint.terminal")


class SmartPOSTerminalDriver(TerminalDriver):
    """Driver para terminal SmartPOS por HTTP."""

    def __init__(self, config):
        self.config = config
        self._connected = False
        self._busy = False
        self._base_url = f"http://{self.config.ip_address}:{self.config.port}"

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Verifica conexión con la terminal SmartPOS."""
        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                f"{self._base_url}/status",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            if self.config.api_key:
                req.add_header("Authorization", f"Bearer {self.config.api_key}")

            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    self._connected = True
                    logger.info(f"SmartPOS conectada: {self._base_url}")
                    return True
            return False
        except ImportError:
            logger.error("urllib no disponible")
            return False
        except Exception as e:
            logger.error(f"Error conexión SmartPOS: {e}")
            self._connected = False
            return False

    def disconnect(self):
        self._connected = False

    def _http_request(self, method: str, path: str, data: Optional[dict] = None,
                      timeout: int = 30) -> Optional[dict]:
        """Realiza petición HTTP a la terminal."""
        import urllib.request
        import json

        url = f"{self._base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"Error HTTP SmartPOS: {e}")
            return None

    def charge(self, amount: float, currency: str = "MXN") -> ChargeResult:
        """Realiza un cobro via HTTP POST."""
        if self._busy:
            return ChargeResult(status="error", message="Terminal ocupada")

        self._busy = True
        try:
            payload = {
                "amount": round(amount, 2),
                "currency": currency,
                "transaction_type": "sale",
                "reference": str(uuid.uuid4())[:12],
            }

            response = self._http_request("POST", "/charge", payload,
                                          timeout=self.config.timeout_seconds)
            if response is None:
                return ChargeResult(status="error", message="Sin respuesta de terminal")

            status = response.get("status", "").lower()
            if status in ("approved", "aprobado", "ok", "success"):
                return ChargeResult(
                    status="approved",
                    reference=response.get("reference", ""),
                    amount=amount,
                    auth_code=response.get("auth_code", ""),
                    transaction_id=response.get("transaction_id", str(uuid.uuid4())),
                    receipt_number=response.get("receipt_number", ""),
                )
            else:
                return ChargeResult(
                    status="declined",
                    message=response.get("message", "Declinada"),
                    amount=amount,
                )
        finally:
            self._busy = False

    def refund(self, transaction_id: str, amount: float) -> ChargeResult:
        """Realiza un reembolso via HTTP."""
        if self._busy:
            return ChargeResult(status="error", message="Terminal ocupada")

        self._busy = True
        try:
            payload = {
                "transaction_id": transaction_id,
                "amount": round(amount, 2),
                "transaction_type": "refund",
            }

            response = self._http_request("POST", "/refund", payload, timeout=30)
            if response is None:
                return ChargeResult(status="error", message="Sin respuesta")

            status = response.get("status", "").lower()
            if status in ("approved", "aprobado", "ok", "success"):
                return ChargeResult(
                    status="approved",
                    reference=transaction_id,
                    amount=amount,
                )
            return ChargeResult(status="declined", message="Reembolso rechazado")
        finally:
            self._busy = False

    def cancel(self) -> bool:
        """Cancela operación actual."""
        response = self._http_request("POST", "/cancel", timeout=5)
        return response is not None and response.get("status") == "cancelled"

    def get_status(self) -> dict:
        """Obtiene estado de la terminal."""
        if not self._connected:
            return {"connected": False, "error": "No conectada"}

        response = self._http_request("GET", "/status", timeout=5)
        return response or {"connected": True, "online": False}
