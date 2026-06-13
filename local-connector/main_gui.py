"""DaePoint Local Connector - Interfaz gráfica para configuración y gestión de hardware."""
import sys
import os
import threading
import queue
import logging

# Agregar directorio raíz al path para imports absolutos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

from config.settings import AppSettings, PrinterConfig, TerminalConfig

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("daepoint.connector")

# Cola para comunicación con FastAPI (impresora/terminal virtual)
printer_queue = queue.Queue()
terminal_queue = queue.Queue()
transactions = {}

# Configuración global de la app
_app_settings: AppSettings = AppSettings.load()

# ─── CustomTkinter setup ───
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ConnectorApp(ctk.CTk):
    """Ventana principal del Local Connector."""

    def __init__(self):
        super().__init__()
        self.title("DaePoint Local Connector v2.0")
        self.geometry("680x580")
        self.resizable(False, False)

        self.server_thread = None
        self.is_server_running = False
        self.printer_driver = None
        self.terminal_driver = None

        # Cargar configuración guardada
        self.settings = _app_settings

        self._create_header()
        self._create_tabs()
        self._load_config_to_gui()
        self._start_server()

        # Iniciar loops de colas para simulación
        self.after(500, self._check_printer_queue)
        self.after(100, self._check_terminal_queue)

    # ─── Header ───
    def _create_header(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(
            header, text="DaePoint Hardware Connector",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        self.status_label = ctk.CTkLabel(
            header, text="● Iniciando...",
            text_color="orange", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_label.pack(side="right")

    # ─── Tabs ───
    def _create_tabs(self):
        self.tabview = ctk.CTkTabview(self, width=640, height=480)
        self.tabview.pack(padx=15, pady=10, fill="both", expand=True)

        self.tabview.add("Impresora")
        self.tabview.add("Terminal TPV")
        self.tabview.add("General")

        self._setup_printer_tab()
        self._setup_terminal_tab()
        self._setup_general_tab()

    # ─── Tab Impresora ───
    def _setup_printer_tab(self):
        tab = self.tabview.tab("Impresora")
        tab.columnconfigure(1, weight=1)

        # Habilitada
        self.printer_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkLabel(tab, text="Habilitada:").grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        ctk.CTkSwitch(tab, text="", variable=self.printer_enabled_var).grid(row=0, column=1, padx=15, pady=(15, 5), sticky="w")

        # Tipo de conexión
        ctk.CTkLabel(tab, text="Conexión:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.printer_conn_var = ctk.StringVar(value="network")
        self.printer_conn_menu = ctk.CTkOptionMenu(
            tab, variable=self.printer_conn_var,
            values=["network", "usb", "serial", "bluetooth", "simulator"],
            command=self._on_printer_conn_change
        )
        self.printer_conn_menu.grid(row=1, column=1, padx=15, pady=5, sticky="w")

        # Modelo / Perfil
        ctk.CTkLabel(tab, text="Modelo:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.printer_profile_var = ctk.StringVar(value="generic_escpos")
        self.printer_profile_menu = ctk.CTkOptionMenu(
            tab, variable=self.printer_profile_var,
            values=self._get_printer_profiles()
        )
        self.printer_profile_menu.grid(row=2, column=1, padx=15, pady=5, sticky="w")

        # IP (para red)
        self.printer_ip_label = ctk.CTkLabel(tab, text="IP / Puerto:")
        self.printer_ip_label.grid(row=3, column=0, padx=15, pady=5, sticky="w")
        ip_frame = ctk.CTkFrame(tab, fg_color="transparent")
        ip_frame.grid(row=3, column=1, padx=15, pady=5, sticky="w")
        self.printer_ip_entry = ctk.CTkEntry(ip_frame, placeholder_text="192.168.1.100", width=140)
        self.printer_ip_entry.pack(side="left", padx=(0, 5))
        self.printer_port_entry = ctk.CTkEntry(ip_frame, placeholder_text="9100", width=70)
        self.printer_port_entry.pack(side="left")

        # USB VID/PID
        self.printer_usb_label = ctk.CTkLabel(tab, text="USB VID:PID:")
        self.printer_usb_label.grid(row=4, column=0, padx=15, pady=5, sticky="w")
        self.printer_usb_entry = ctk.CTkEntry(tab, placeholder_text="04b8:0202", width=200)
        self.printer_usb_entry.grid(row=4, column=1, padx=15, pady=5, sticky="w")

        # Serial
        self.printer_serial_label = ctk.CTkLabel(tab, text="Puerto Serial:")
        self.printer_serial_label.grid(row=5, column=0, padx=15, pady=5, sticky="w")
        serial_frame = ctk.CTkFrame(tab, fg_color="transparent")
        serial_frame.grid(row=5, column=1, padx=15, pady=5, sticky="w")
        self.printer_serial_entry = ctk.CTkEntry(serial_frame, placeholder_text="COM3", width=100)
        self.printer_serial_entry.pack(side="left", padx=(0, 5))
        self.printer_baud_entry = ctk.CTkEntry(serial_frame, placeholder_text="9600", width=80)
        self.printer_baud_entry.pack(side="left")

        # Opciones
        self.printer_drawer_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Abrir cajón al vender", variable=self.printer_drawer_var).grid(row=6, column=0, columnspan=2, padx=15, pady=5, sticky="w")

        self.printer_autocut_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab, text="Corte automático", variable=self.printer_autocut_var).grid(row=7, column=0, columnspan=2, padx=15, pady=5, sticky="w")

        # Botones
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=15)

        ctk.CTkButton(btn_frame, text="Auto-detectar", command=self._detect_printer, width=130).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Probar Impresión", command=self._test_printer, width=130).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Guardar", command=self._save_printer_config, fg_color="#10c22b", hover_color="#0a8a1e", width=100).pack(side="left", padx=5)

        # Resultado
        self.printer_result_label = ctk.CTkLabel(tab, text="", text_color="gray", wraplength=550)
        self.printer_result_label.grid(row=9, column=0, columnspan=2, padx=15, pady=(0, 10))

    # ─── Tab Terminal ───
    def _setup_terminal_tab(self):
        tab = self.tabview.tab("Terminal TPV")
        tab.columnconfigure(1, weight=1)

        self.terminal_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkLabel(tab, text="Habilitada:").grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        ctk.CTkSwitch(tab, text="", variable=self.terminal_enabled_var).grid(row=0, column=1, padx=15, pady=(15, 5), sticky="w")

        ctk.CTkLabel(tab, text="Conexión:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.terminal_conn_var = ctk.StringVar(value="serial")
        self.terminal_conn_menu = ctk.CTkOptionMenu(
            tab, variable=self.terminal_conn_var,
            values=["serial", "network", "smartpos", "clip", "simulator"],
            command=self._on_terminal_conn_change
        )
        self.terminal_conn_menu.grid(row=1, column=1, padx=15, pady=5, sticky="w")

        # Serial
        self.terminal_serial_label = ctk.CTkLabel(tab, text="Puerto / IP:")
        self.terminal_serial_label.grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.terminal_address_entry = ctk.CTkEntry(tab, placeholder_text="COM4 o 192.168.1.50", width=200)
        self.terminal_address_entry.grid(row=2, column=1, padx=15, pady=5, sticky="w")

        self.terminal_baud_label = ctk.CTkLabel(tab, text="Baud Rate:")
        self.terminal_baud_label.grid(row=3, column=0, padx=15, pady=5, sticky="w")
        self.terminal_baud_entry = ctk.CTkEntry(tab, placeholder_text="9600", width=200)
        self.terminal_baud_entry.grid(row=3, column=1, padx=15, pady=5, sticky="w")

        # Protocolo
        ctk.CTkLabel(tab, text="Protocolo:").grid(row=4, column=0, padx=15, pady=5, sticky="w")
        self.terminal_protocol_var = ctk.StringVar(value="generic")
        ctk.CTkOptionMenu(
            tab, variable=self.terminal_protocol_var,
            values=["generic", "abm", "iso8583", "smartpos", "clip"]
        ).grid(row=4, column=1, padx=15, pady=5, sticky="w")

        # Timeout
        ctk.CTkLabel(tab, text="Timeout (seg):").grid(row=5, column=0, padx=15, pady=5, sticky="w")
        self.terminal_timeout_entry = ctk.CTkEntry(tab, placeholder_text="120", width=200)
        self.terminal_timeout_entry.grid(row=5, column=1, padx=15, pady=5, sticky="w")

        # API Key (para SmartPOS)
        self.terminal_apikey_label = ctk.CTkLabel(tab, text="API Key:")
        self.terminal_apikey_label.grid(row=6, column=0, padx=15, pady=5, sticky="w")
        self.terminal_apikey_entry = ctk.CTkEntry(tab, placeholder_text="Opcional - SmartPOS", width=200, show="*")
        self.terminal_apikey_entry.grid(row=6, column=1, padx=15, pady=5, sticky="w")

        # Botones
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=15)

        ctk.CTkButton(btn_frame, text="Auto-detectar", command=self._detect_terminal, width=130).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Probar Cobro", command=self._test_terminal, width=130).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Guardar", command=self._save_terminal_config, fg_color="#10c22b", hover_color="#0a8a1e", width=100).pack(side="left", padx=5)

        self.terminal_result_label = ctk.CTkLabel(tab, text="", text_color="gray", wraplength=550)
        self.terminal_result_label.grid(row=8, column=0, columnspan=2, padx=15, pady=(0, 10))

    # ─── Tab General ───
    def _setup_general_tab(self):
        tab = self.tabview.tab("General")

        ctk.CTkLabel(tab, text="Configuración del Servidor", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=15, pady=(15, 10), anchor="w")

        # Puerto del servidor
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(frame, text="Puerto API:").pack(side="left", padx=(0, 10))
        self.server_port_entry = ctk.CTkEntry(frame, placeholder_text="5000", width=100)
        self.server_port_entry.pack(side="left")

        # Log level
        frame2 = ctk.CTkFrame(tab, fg_color="transparent")
        frame2.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(frame2, text="Log Level:").pack(side="left", padx=(0, 10))
        self.log_level_var = ctk.StringVar(value="info")
        ctk.CTkOptionMenu(frame2, variable=self.log_level_var, values=["debug", "info", "warning", "error"]).pack(side="left")

        # Botones de config
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(btn_frame, text="Guardar Todo", command=self._save_all_config, fg_color="#10c22b", hover_color="#0a8a1e").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Restablecer Fábrica", command=self._reset_config, fg_color="#c22b10", hover_color="#8a1a0b").pack(side="left", padx=5)

        # Info
        ctk.CTkLabel(tab, text=f"Config: {self.settings.config_path()}", text_color="gray", font=ctk.CTkFont(size=11)).pack(padx=15, pady=(20, 5), anchor="w")

    # ─── Helpers ───

    def _get_printer_profiles(self):
        from config.defaults import DEFAULT_PRINTER_PROFILES
        return sorted(DEFAULT_PRINTER_PROFILES.keys())

    def _on_printer_conn_change(self, choice):
        """Muestra/oculta campos según tipo de conexión."""
        is_network = choice in ("network", "simulator")
        is_usb = choice == "usb"
        is_serial = choice in ("serial", "bluetooth")

        # Red
        self.printer_ip_label.grid() if is_network else self.printer_ip_label.grid_remove()
        self.printer_ip_entry.master.grid() if is_network else self.printer_ip_entry.master.grid_remove()
        # USB
        self.printer_usb_label.grid() if is_usb else self.printer_usb_label.grid_remove()
        self.printer_usb_entry.grid() if is_usb else self.printer_usb_entry.grid_remove()
        # Serial
        self.printer_serial_label.grid() if is_serial else self.printer_serial_label.grid_remove()
        self.printer_serial_entry.master.grid() if is_serial else self.printer_serial_entry.master.grid_remove()

    def _on_terminal_conn_change(self, choice):
        is_serial = choice in ("serial", "simulator")
        is_network = choice in ("network", "smartpos", "clip")

        self.terminal_baud_label.grid() if is_serial else self.terminal_baud_label.grid_remove()
        self.terminal_baud_entry.grid() if is_serial else self.terminal_baud_entry.grid_remove()
        self.terminal_apikey_label.grid() if is_network else self.terminal_apikey_label.grid_remove()
        self.terminal_apikey_entry.grid() if is_network else self.terminal_apikey_entry.grid_remove()

    def _load_config_to_gui(self):
        """Carga la configuración del archivo a los campos de la GUI."""
        s = self.settings

        # Impresora
        self.printer_enabled_var.set(s.printer.enabled)
        self.printer_conn_var.set(s.printer.connection_type)
        self.printer_profile_var.set(s.printer.model_profile)
        self.printer_ip_entry.delete(0, "end")
        self.printer_ip_entry.insert(0, s.printer.ip_address)
        self.printer_port_entry.delete(0, "end")
        self.printer_port_entry.insert(0, str(s.printer.port))
        self.printer_usb_entry.delete(0, "end")
        self.printer_usb_entry.insert(0, f"{s.printer.vendor_id}:{s.printer.product_id}")
        self.printer_serial_entry.delete(0, "end")
        self.printer_serial_entry.insert(0, s.printer.serial_port)
        self.printer_baud_entry.delete(0, "end")
        self.printer_baud_entry.insert(0, str(s.printer.baud_rate))
        self.printer_drawer_var.set(s.printer.open_drawer_on_sale)
        self.printer_autocut_var.set(s.printer.auto_cut)

        # Terminal
        self.terminal_enabled_var.set(s.terminal.enabled)
        self.terminal_conn_var.set(s.terminal.connection_type)
        self.terminal_address_entry.delete(0, "end")
        self.terminal_address_entry.insert(0, s.terminal.serial_port or s.terminal.ip_address)
        self.terminal_baud_entry.delete(0, "end")
        self.terminal_baud_entry.insert(0, str(s.terminal.baud_rate))
        self.terminal_protocol_var.set(s.terminal.protocol)
        self.terminal_timeout_entry.delete(0, "end")
        self.terminal_timeout_entry.insert(0, str(s.terminal.timeout_seconds))
        self.terminal_apikey_entry.delete(0, "end")
        self.terminal_apikey_entry.insert(0, s.terminal.api_key or s.terminal.clip_api_key)

        # General
        self.server_port_entry.delete(0, "end")
        self.server_port_entry.insert(0, str(s.server_port))
        self.log_level_var.set(s.log_level)

        # Aplicar visibilidad inicial
        self._on_printer_conn_change(s.printer.connection_type)
        self._on_terminal_conn_change(s.terminal.connection_type)

    def _save_printer_config(self):
        """Guarda la configuración de impresora desde la GUI."""
        conn = self.printer_conn_var.get()
        ip_parts = self.printer_ip_entry.get().split(":")
        usb_parts = self.printer_usb_entry.get().split(":")

        self.settings.printer = PrinterConfig(
            enabled=self.printer_enabled_var.get(),
            connection_type=conn,
            model_profile=self.printer_profile_var.get(),
            ip_address=ip_parts[0] if ip_parts else "192.168.1.100",
            port=int(ip_parts[1]) if len(ip_parts) > 1 else 9100,
            vendor_id=usb_parts[0] if len(usb_parts) >= 1 else "",
            product_id=usb_parts[1] if len(usb_parts) >= 2 else "",
            serial_port=self.printer_serial_entry.get() or "COM3",
            baud_rate=int(self.printer_baud_entry.get() or "9600"),
            auto_cut=self.printer_autocut_var.get(),
            open_drawer_on_sale=self.printer_drawer_var.get(),
        )

        path = self.settings.save()
        self.printer_result_label.configure(text=f"✓ Guardado en {path.name}", text_color="green")
        logger.info(f"Config impresora guardada: {self.settings.printer.model_dump()}")

    def _save_terminal_config(self):
        """Guarda la configuración de terminal desde la GUI."""
        addr = self.terminal_address_entry.get()
        conn = self.terminal_conn_var.get()

        is_network = conn in ("network", "smartpos", "clip")

        self.settings.terminal = TerminalConfig(
            enabled=self.terminal_enabled_var.get(),
            connection_type=conn,
            serial_port=addr if not is_network else "",
            baud_rate=int(self.terminal_baud_entry.get() or "9600"),
            ip_address=addr if is_network else "",
            port=8080,
            protocol=self.terminal_protocol_var.get(),
            timeout_seconds=int(self.terminal_timeout_entry.get() or "120"),
            api_key=self.terminal_apikey_entry.get() if conn == "smartpos" else "",
            clip_api_key=self.terminal_apikey_entry.get() if conn == "clip" else "",
        )

        path = self.settings.save()
        self.terminal_result_label.configure(text=f"✓ Guardado en {path.name}", text_color="green")
        logger.info(f"Config terminal guardada: {self.settings.terminal.model_dump()}")

    def _save_all_config(self):
        """Guarda toda la configuración."""
        self.settings.server_port = int(self.server_port_entry.get() or "5000")
        self.settings.log_level = self.log_level_var.get()
        self._save_printer_config()
        self._save_terminal_config()
        self.printer_result_label.configure(text="✓ Toda la configuración guardada", text_color="green")

    def _reset_config(self):
        """Restablece configuración de fábrica."""
        self.settings = AppSettings()
        path = self.settings.save()
        self._load_config_to_gui()
        self.printer_result_label.configure(text=f"✓ Configuración restablecida ({path.name})", text_color="orange")

    # ─── Auto-detección ───

    def _detect_printer(self):
        """Detecta impresoras conectadas."""
        self.printer_result_label.configure(text="🔍 Buscando impresoras...", text_color="orange")
        self.update()

        def _detect():
            try:
                from hardware.discovery import detect_printers
                found = detect_printers()
                self.after(0, lambda: self._on_printer_detected(found))
            except Exception as e:
                self.after(0, lambda: self.printer_result_label.configure(
                    text=f"Error: {e}", text_color="red"
                ))

        threading.Thread(target=_detect, daemon=True).start()

    def _on_printer_detected(self, printers):
        if not printers:
            self.printer_result_label.configure(text="No se encontraron impresoras", text_color="gray")
            return

        # Usar la primera detectada con auto-configure
        p = printers[0]
        try:
            from hardware.discovery import auto_configure_printer
            config = auto_configure_printer(p)
        except Exception:
            config = {
                "connection_type": p["connection_type"],
                "ip_address": p["address"].split(":")[0] if ":" in p["address"] else "192.168.1.100",
                "port": int(p["address"].split(":")[1]) if ":" in p["address"] else 9100,
                "serial_port": p["address"],
                "vendor_id": p["address"].split(":")[0] if ":" in p["address"] else "",
                "product_id": p["address"].split(":")[1] if ":" in p["address"] else "",
            }

        self.printer_conn_var.set(config.get("connection_type", p["connection_type"]))
        self.printer_profile_var.set(config.get("model_profile", "generic_escpos"))
        self.printer_enabled_var.set(True)

        if config.get("connection_type") == "network":
            self.printer_ip_entry.delete(0, "end")
            self.printer_ip_entry.insert(0, config.get("ip_address", "192.168.1.100"))
            self.printer_port_entry.delete(0, "end")
            self.printer_port_entry.insert(0, str(config.get("port", 9100)))
        elif config.get("connection_type") == "usb":
            self.printer_usb_entry.delete(0, "end")
            self.printer_usb_entry.insert(0, f"{config.get('vendor_id', '')}:{config.get('product_id', '')}")
        elif config.get("connection_type") == "serial":
            self.printer_serial_entry.delete(0, "end")
            self.printer_serial_entry.insert(0, config.get("serial_port", p["address"]))

        self._on_printer_conn_change(config.get("connection_type", p["connection_type"]))

        summary = f"✓ Detectada: {p['model']} ({p['connection_type']}: {p['address']})"
        if len(printers) > 1:
            summary += f" [+{len(printers)-1} más]"
        self.printer_result_label.configure(text=summary, text_color="green")
        logger.info(f"Impresoras detectadas: {printers}")

    def _detect_terminal(self):
        """Detecta terminales conectadas."""
        self.terminal_result_label.configure(text="🔍 Buscando terminales...", text_color="orange")
        self.update()

        def _detect():
            try:
                from hardware.discovery import detect_terminals
                found = detect_terminals()
                self.after(0, lambda: self._on_terminal_detected(found))
            except Exception as e:
                self.after(0, lambda: self.terminal_result_label.configure(
                    text=f"Error: {e}", text_color="red"
                ))

        threading.Thread(target=_detect, daemon=True).start()

    def _on_terminal_detected(self, terminals):
        if not terminals:
            self.terminal_result_label.configure(text="No se encontraron terminales", text_color="gray")
            return

        t = terminals[0]
        try:
            from hardware.discovery import auto_configure_terminal
            config = auto_configure_terminal(t)
        except Exception:
            config = {
                "connection_type": t["connection_type"],
                "serial_port": t["address"],
            }

        self.terminal_enabled_var.set(True)
        self.terminal_conn_var.set(config.get("connection_type", t["connection_type"]))
        self.terminal_address_entry.delete(0, "end")
        self.terminal_address_entry.insert(0, config.get("serial_port", t["address"]))
        self.terminal_result_label.configure(
            text=f"✓ Detectada: {t['model']} ({t['address']})", text_color="green"
        )
        logger.info(f"Terminales detectadas: {terminals}")

    # ─── Pruebas de hardware ───

    def _test_printer(self):
        """Prueba la impresora con un ticket de ejemplo."""
        self.printer_result_label.configure(text="Imprimiendo ticket de prueba...", text_color="orange")
        self.update()

        def _print():
            try:
                self._save_printer_config()
                from hardware.printer.escpos_driver import ESCPOSDriver

                driver = ESCPOSDriver(self.settings.printer)
                if driver.connect():
                    ticket = (
                        "================================\n"
                        "     DaePoint POS - PRUEBA     \n"
                        "================================\n"
                        "\n"
                        "Fecha: 2026-06-13 12:00\n"
                        "Cajero: Prueba\n"
                        "\n"
                        "--------------------------------\n"
                        " 1x Hamburger Clasica   $89.00\n"
                        " 2x Coca Cola 600ml     $36.00\n"
                        "--------------------------------\n"
                        " SUBTOTAL:              $125.00\n"
                        " TOTAL:                 $125.00\n"
                        "\n"
                        ">>   ¡GRACIAS POR SU COMPRA!   \n"
                        "\n"
                        "[QR:DaePointPOS2026Test]\n"
                    )
                    driver.print_receipt(ticket)
                    driver.disconnect()
                    self.after(0, lambda: self.printer_result_label.configure(
                        text="✓ Ticket impreso correctamente", text_color="green"
                    ))
                else:
                    err = driver.status.error or "No se pudo conectar"
                    self.after(0, lambda e=err: self.printer_result_label.configure(
                        text=f"✗ Error: {e}", text_color="red"
                    ))
            except Exception as e:
                self.after(0, lambda err=str(e): self.printer_result_label.configure(
                    text=f"✗ Error: {err}", text_color="red"
                ))

        threading.Thread(target=_print, daemon=True).start()

    def _test_terminal(self):
        """Prueba la terminal con un cobro simulado."""
        self.terminal_result_label.configure(text="Iniciando cobro de prueba ($10.00 MXN)...", text_color="orange")
        self.update()

        def _charge():
            try:
                self._save_terminal_config()
                # Usar simulador por ahora
                import uuid
                ref = f"TEST-{str(uuid.uuid4())[:8]}"
                self.after(0, lambda: self.terminal_result_label.configure(
                    text=f"✓ Cobro aprobado (Ref: {ref}, $10.00 MXN)", text_color="green"
                ))
            except Exception as e:
                self.after(0, lambda err=str(e): self.terminal_result_label.configure(
                    text=f"✗ Error: {err}", text_color="red"
                ))

        threading.Thread(target=_charge, daemon=True).start()

    # ─── Servidor FastAPI ───

    def _start_server(self):
        def run():
            try:
                import uvicorn
                import os
                if getattr(sys, 'stdout', None) is None:
                    sys.stdout = open(os.devnull, "w")
                if getattr(sys, 'stderr', None) is None:
                    sys.stderr = open(os.devnull, "w")
                if getattr(sys, 'stdin', None) is None:
                    sys.stdin = open(os.devnull, "r")
                uvicorn.run(app, host="127.0.0.1", port=self.settings.server_port, log_level="info")
            except Exception as e:
                logger.error(f"Error servidor: {e}")

        from api.server import app
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        self.after(1500, self._update_status_running)

    def _update_status_running(self):
        self.is_server_running = True
        self.status_label.configure(
            text=f"● Activo (Puerto {self.settings.server_port})",
            text_color="green"
        )

    # ─── Colas de simulación ───

    def _check_printer_queue(self):
        try:
            while True:
                msg = printer_queue.get_nowait()
                self._show_printer_popup(msg["title"], msg["content"], msg["type"])
        except queue.Empty:
            pass
        self.after(500, self._check_printer_queue)

    def _check_terminal_queue(self):
        try:
            while True:
                msg = terminal_queue.get_nowait()
                if msg["type"] == "charge":
                    self._show_terminal_popup(msg["tx_id"], msg["amount"], msg["currency"])
        except queue.Empty:
            pass
        self.after(100, self._check_terminal_queue)

    def _show_terminal_popup(self, tx_id, amount, currency):
        popup = ctk.CTkToplevel(self)
        popup.title("Terminal Bancaria")
        popup.geometry("320x200")
        popup.attributes("-topmost", True)

        ctk.CTkLabel(popup, text="SIMULADOR TERMINAL",
                      font=ctk.CTkFont(weight="bold", size=16)).pack(pady=(20, 10))
        ctk.CTkLabel(popup, text=f"Cobrando: ${amount} {currency}",
                      font=ctk.CTkFont(size=14)).pack(pady=10)

        def approve():
            import uuid
            transactions[tx_id]["result"] = {
                "status": "approved",
                "reference": f"AUTH-SIM-{str(uuid.uuid4())[:6]}",
                "amount": amount,
            }
            transactions[tx_id]["event"].set()
            popup.destroy()

        def decline():
            transactions[tx_id]["result"] = {
                "status": "error",
                "message": "Declinada",
            }
            transactions[tx_id]["event"].set()
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", decline)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Aprobar", fg_color="green", hover_color="darkgreen",
                       command=approve, width=110).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Rechazar", fg_color="red", hover_color="darkred",
                       command=decline, width=110).pack(side="right", padx=10)

    def _show_printer_popup(self, title, content, sim_type):
        popup = ctk.CTkToplevel(self)
        popup.title(title)

        if sim_type == "drawer":
            popup.geometry("400x150")
            ctk.CTkLabel(popup, text=content, text_color="#10c22b",
                          font=ctk.CTkFont(size=16, weight="bold")).pack(expand=True, padx=20, pady=20)
            self.after(3000, popup.destroy)
        else:
            popup.geometry("350x500")
            frame = ctk.CTkScrollableFrame(popup, fg_color="white", corner_radius=0)
            frame.pack(fill="both", expand=True, padx=10, pady=10)
            ctk.CTkLabel(frame, text=content, text_color="black",
                          font=("Courier New", 11), justify="left", anchor="nw").pack(fill="both", expand=True, padx=10, pady=10)


# ─── CLI para headless / testing ───

def main():
    """Entry point para CLI o GUI."""
    if "--config-only" in sys.argv:
        # Headless: cargar y mostrar config
        settings = AppSettings.load()
        print(f"Config path: {settings.config_path()}")
        print(f"Printer: {settings.printer.model_dump_json(indent=2)}")
        print(f"Terminal: {settings.terminal.model_dump_json(indent=2)}")
        return

    if "--test-print" in sys.argv:
        settings = AppSettings.load()
        from hardware.printer.escpos_driver import ESCPOSDriver
        driver = ESCPOSDriver(settings.printer)
        if driver.connect():
            driver.print_receipt("=== PRUEBA DaePoint ===\nHello World!\n")
            driver.disconnect()
            print("OK: Ticket impreso")
        else:
            print(f"ERROR: {driver.status.error}")
        return

    if "--detect" in sys.argv:
        from hardware.discovery import detect_printers, detect_terminals
        print("Impresoras:")
        for p in detect_printers():
            print(f"  - {p}")
        print("Terminales:")
        for t in detect_terminals():
            print(f"  - {t}")
        return

    # GUI mode
    app = ConnectorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
