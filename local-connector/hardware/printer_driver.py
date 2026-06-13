import queue

# We will use this queue to communicate between the FastAPI threads 
# and the main CustomTkinter GUI thread safely.
printer_queue = queue.Queue()

class PrinterDriver:
    def __init__(self, mode="simulator", **kwargs):
        self.mode = mode
        self.kwargs = kwargs
        # In the future, here we would initialize the real printer based on mode (USB, Network, etc.)
        # For simulator, we don't need a real connection.

    def print_receipt(self, content: str):
        if self.mode == "simulator":
            print(f"[PrinterDriver] Simulated Print Request Received")
            # Push to the queue so the main GUI thread can render it
            printer_queue.put({
                "type": "receipt",
                "title": "Ticket de Venta (Simulador)",
                "content": content
            })
        else:
            # Future real printing logic
            print(f"[PrinterDriver] Printing to {self.mode}")

    def open_cash_drawer(self):
        if self.mode == "simulator":
            print(f"[PrinterDriver] Simulated Cash Drawer Open")
            # Push to the queue so the main GUI thread can render it
            printer_queue.put({
                "type": "drawer",
                "title": "Cajón de Dinero (Simulador)",
                "content": "\n\n******************************\n   CAJÓN DE DINERO ABIERTO   \n******************************\n\n"
            })
        else:
            # Future real kick
            print("[PrinterDriver] Kicking Cash Drawer")
