"""Perfiles por defecto para impresoras y terminales conocidas."""

DEFAULT_PRINTER_PROFILES = {
    # Generic ESC/POS (funciona con ~90% de impresoras térmicas)
    "generic_escpos": {
        "name": "Genérica ESC/POS",
        "vendor": "Generico",
        "codepage": "cp437",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
        "beeper_freq": 1000,
    },
    # Epson TM-T20
    "epson_tm_t20": {
        "name": "Epson TM-T20",
        "vendor": "Epson",
        "model": "TM-T20",
        "codepage": "cp858",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
        "supports_full_cut": False,
    },
    # Epson TM-T88
    "epson_tm_t88": {
        "name": "Epson TM-T88VI",
        "vendor": "Epson",
        "model": "TM-T88VI",
        "codepage": "cp858",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial_full",
        "drawer_pin": 2,
        "supports_full_cut": True,
    },
    # Epson TM-M30
    "epson_tm_m30": {
        "name": "Epson TM-M30",
        "vendor": "Epson",
        "model": "TM-M30",
        "codepage": "cp858",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
    },
    # Star TSP143
    "star_tsp143": {
        "name": "Star TSP143III",
        "vendor": "Star",
        "model": "TSP143III",
        "codepage": "cp437",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 5,
    },
    # Star TSP654
    "star_tsp654": {
        "name": "Star TSP654II",
        "vendor": "Star",
        "model": "TSP654II",
        "codepage": "cp437",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 5,
    },
    # Bixolon SRP-350
    "bixolon_srp350": {
        "name": "Bixolon SRP-350III",
        "vendor": "Bixolon",
        "model": "SRP-350III",
        "codepage": "cp437",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
    },
    # Citizen CT-S310
    "citizen_cts310": {
        "name": "Citizen CT-S310II",
        "vendor": "Citizen",
        "model": "CT-S310II",
        "codepage": "cp437",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
    },
    # Xprinter XP-80C
    "xprinter_xp80c": {
        "name": "Xprinter XP-80C",
        "vendor": "Xprinter",
        "model": "XP-80C",
        "codepage": "cp437",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
    },
    # Hasar HTP-250
    "hasar_htp250": {
        "name": "Hasar HTP-250",
        "vendor": "Hasar",
        "model": "HTP-250",
        "codepage": "cp858",
        "paper_width_mm": 80,
        "max_print_width_dots": 512,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
    },
    # 58mm printers (reducido)
    "generic_58mm": {
        "name": "Impresora 58mm Genérica",
        "vendor": "Generico",
        "codepage": "cp437",
        "paper_width_mm": 58,
        "max_print_width_dots": 384,
        "print_density": 7,
        "cutter": "partial",
        "drawer_pin": 2,
    },
}

DEFAULT_TERMINAL_PROFILES = {
    "serial_generic": {
        "name": "Terminal Serial Genérica",
        "protocol": "generic",
        "baud_rate": 9600,
        "timeout_seconds": 120,
    },
    "ingenico_lane3000": {
        "name": "Ingenico Lane 3000",
        "protocol": "smartpos",
        "connection": "network",
    },
    "verifone_vx680": {
        "name": "Verifone VX680",
        "protocol": "iso8583",
        "connection": "network",
    },
    "pax_a920": {
        "name": "PAX A920",
        "protocol": "smartpos",
        "connection": "network",
    },
    "clip_terminal": {
        "name": "Clip Terminal",
        "protocol": "clip",
        "connection": "network",
    },
}


def get_default_config() -> dict:
    """Retorna una configuración base con valores por defecto."""
    return {
        "printer": {
            "enabled": False,
            "connection_type": "network",
            "model_profile": "generic_escpos",
            "ip_address": "192.168.1.100",
            "port": 9100,
            "paper_width": 80,
            "print_density": 7,
            "auto_cut": True,
            "open_drawer_on_sale": True,
        },
        "terminal": {
            "enabled": False,
            "connection_type": "serial",
            "serial_port": "COM4",
            "baud_rate": 9600,
            "protocol": "generic",
            "timeout_seconds": 120,
            "currency": "MXN",
        },
    }
