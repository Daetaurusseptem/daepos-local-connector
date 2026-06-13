import queue
import threading
import uuid

# Queue to send the UI prompt
terminal_queue = queue.Queue()

# We need a dictionary to store the Event and the Result for a given transaction
transactions = {}

class TerminalDriver:
    def __init__(self, mode="simulator"):
        self.mode = mode

    def charge(self, amount, currency="MXN"):
        if self.mode == "simulator":
            tx_id = str(uuid.uuid4())
            event = threading.Event()
            transactions[tx_id] = {"event": event, "result": None}

            # Send prompt to UI
            terminal_queue.put({
                "type": "charge",
                "tx_id": tx_id,
                "amount": amount,
                "currency": currency
            })

            # Block the FastAPI thread until UI sets the event
            event.wait()
            
            result = transactions.pop(tx_id)
            return result["result"]
        else:
            return {"status": "approved", "reference": f"AUTH-HW-{str(uuid.uuid4())[:6]}", "amount": amount}
