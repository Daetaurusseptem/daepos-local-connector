"""
DaePoint Local Connector - Build & Packaging Script.

Uso:
    python packaging/build.py              # Build completo
    python packaging/build.py --release    # Build + installer
    python packaging/build.py --clean      # Limpiar
"""
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
OUTPUT_NAME = "DaePointConnector"


def get_version() -> str:
    """Obtiene la versión desde git describe o fallback."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            # Limpiar prefijo 'v' si existe
            if version.startswith("v"):
                version = version[1:]
            return version
    except Exception:
        pass
    return "2.0.0-dev"


def get_version_info(version: str) -> dict:
    """Convierte versión a tupla (major, minor, patch, build) para PyInstaller."""
    parts = version.replace("-", ".").split(".")
    nums = []
    for p in parts[:4]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums[:4])


def write_version_file(version: str):
    """Crea archivo de versión para PyInstaller."""
    major, minor, patch, build = get_version_info(version)
    version_content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'DaePoint POS'),
            StringStruct(u'FileDescription', u'DaePoint Local Connector'),
            StringStruct(u'FileVersion', u'{version}'),
            StringStruct(u'InternalName', u'DaePointConnector'),
            StringStruct(u'OriginalFilename', u'DaePointConnector.exe'),
            StringStruct(u'ProductName', u'DaePoint Local Connector'),
            StringStruct(u'ProductVersion', u'{version}'),
            StringStruct(u'LegalCopyright', u'DaePoint POS'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
    version_path = ROOT_DIR / "version_info.py"
    version_path.write_text(version_content, encoding="utf-8")
    return version_path


def clean():
    """Limpia directorios de build anteriores."""
    print("Limpiando builds anteriores...")
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
    # Limpiar version_info.py si existe
    version_file = ROOT_DIR / "version_info.py"
    if version_file.exists():
        version_file.unlink()
    print("   OK Limpieza completada")


def build(version: str):
    """Ejecuta PyInstaller para crear el ejecutable."""
    print(f"Construyendo ejecutable v{version}...")

    # Crear archivo de versión
    version_path = write_version_file(version)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", OUTPUT_NAME,
        "--version-file", str(version_path),
        "--add-data", f"api{os.pathsep}api",
        "--add-data", f"hardware{os.pathsep}hardware",
        "--add-data", f"config{os.pathsep}config",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "pydantic",
        "--hidden-import", "serial",
        "--hidden-import", "escpos",
        "--hidden-import", "usb",
        "--hidden-import", "usb.core",
        "--hidden-import", "usb.util",
        "main_gui.py",
    ]

    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print("   Error en la compilacion")
        sys.exit(1)

    exe_path = DIST_DIR / OUTPUT_NAME / f"{OUTPUT_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"   OK Ejecutable creado: {exe_path} ({size_mb:.1f} MB)")
    else:
        print("   No se encontro el ejecutable")
        sys.exit(1)


def create_installer():
    """Crea el instalador NSIS (Windows)."""
    if platform.system() != "Windows":
        print("NSIS installer solo disponible en Windows")
        return False

    nsis_path = None
    for p in [
        Path("C:\\Program Files (x86)\\NSIS\\makensis.exe"),
        Path("C:\\Program Files\\NSIS\\makensis.exe"),
    ]:
        if p.exists():
            nsis_path = p
            break

    if not nsis_path.exists():
        print("NSIS no encontrado. Instale desde: https://nsis.sourceforge.io/")
        return False

    print("Creando instalador NSIS...")
    spec_path = ROOT_DIR / "packaging" / "installer.nsi"

    if not spec_path.exists():
        print(f"   No se encontro: {spec_path}")
        return False

    result = subprocess.run([str(nsis_path), str(spec_path)], cwd=str(ROOT_DIR))
    if result.returncode == 0:
        installer = ROOT_DIR / "DaePointConnector-Setup.exe"
        if installer.exists():
            size_mb = installer.stat().st_size / (1024 * 1024)
            print(f"   OK Instalador creado: {installer} ({size_mb:.1f} MB)")
            return True
    print("   Error creando instalador")
    return False


def create_portable_zip(version: str):
    """Crea un ZIP portable del ejecutable."""
    print("Creando ZIP portable...")
    dist_folder = DIST_DIR / OUTPUT_NAME
    if not dist_folder.exists():
        print("   No hay build para empaquetar")
        return None

    zip_name = f"{OUTPUT_NAME}-{version}-win64"
    zip_path = DIST_DIR / zip_name
    shutil.make_archive(str(zip_path), "zip", str(dist_folder))

    size_mb = zip_path.stat().st_size / (1024 * 1024) if zip_path.exists() else 0
    print(f"   OK ZIP portable: {zip_path}.zip ({size_mb:.1f} MB)")
    return zip_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DaePoint Connector Build Script")
    parser.add_argument("--clean", action="store_true", help="Limpiar builds anteriores")
    parser.add_argument("--release", action="store_true", help="Build completo con installer")
    parser.add_argument("--portable", action="store_true", help="Crear ZIP portable")
    parser.add_argument("--version", type=str, help="Forzar version (ej: 2.1.0)")
    args = parser.parse_args()

    os.chdir(str(ROOT_DIR))

    if args.clean:
        clean()
        return

    # Obtener version
    version = args.version or get_version()
    print(f"\n{'='*50}")
    print(f"  DaePoint Local Connector - Build v{version}")
    print(f"{'='*50}\n")

    # Build siempre
    clean()
    build(version)

    # Cleanup version file
    version_file = ROOT_DIR / "version_info.py"
    if version_file.exists():
        version_file.unlink()

    if args.portable or args.release:
        create_portable_zip(version)

    if args.release:
        create_installer()

    print(f"\n{'='*50}")
    print(f"  BUILD COMPLETADO - v{version}")
    print(f"{'='*50}")
    print(f"  Ejecutable: {DIST_DIR / OUTPUT_NAME / f'{OUTPUT_NAME}.exe'}")
    print()


if __name__ == "__main__":
    main()
