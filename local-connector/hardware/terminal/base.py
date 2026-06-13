"""Base abstracta para drivers de terminal de pago."""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class ChargeResult(BaseModel):
    """Resultado de una operación de cobro."""
    status: str  # approved, declined, error, cancelled
    reference: Optional[str] = None
    amount: float = 0
    message: Optional[str] = None
    auth_code: Optional[str] = None
    transaction_id: Optional[str] = None
    receipt_number: Optional[str] = None


class TerminalDriver(ABC):
    """Clase base abstracta para terminales de pago."""

    @abstractmethod
    def connect(self) -> bool:
        """Conecta a la terminal."""
        ...

    @abstractmethod
    def disconnect(self):
        """Desconecta de la terminal."""
        ...

    @abstractmethod
    def charge(self, amount: float, currency: str = "MXN") -> ChargeResult:
        """Realiza un cobro."""
        ...

    @abstractmethod
    def refund(self, transaction_id: str, amount: float) -> ChargeResult:
        """Realiza un reembolso."""
        ...

    @abstractmethod
    def cancel(self) -> bool:
        """Cancela la operación actual."""
        ...

    @abstractmethod
    def get_status(self) -> dict:
        """Obtiene el estado de la terminal."""
        ...

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Indica si está conectado."""
        ...
