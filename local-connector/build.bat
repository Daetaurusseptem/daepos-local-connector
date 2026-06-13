@echo off
echo ========================================
echo   DaePoint Local Connector - Build
echo ========================================
echo.

echo [1/4] Limpiando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/4] Verificando dependencias...
pip install pyinstaller --quiet
pip install -r requirements.txt --quiet

echo [3/4] Construyendo Ejecutable...
pyinstaller --noconfirm ^
    --onedir ^
    --windowed ^
    --name "DaePointConnector" ^
    --add-data "api;api" ^
    --add-data "hardware;hardware" ^
    --add-data "config;config" ^
    --hidden-import "fastapi" ^
    --hidden-import "uvicorn" ^
    --hidden-import "pydantic" ^
    --hidden-import "serial" ^
    --hidden-import "escpos" ^
    main_gui.py

echo [4/4] Verificando compilacion...
if exist dist\DaePointConnector\DaePointConnector.exe (
    echo.
    echo ========================================
    echo   BUILD COMPLETADO EXITOSAMENTE
    echo ========================================
    echo   Ejecutable: dist\DaePointConnector\DaePointConnector.exe
    echo.
    echo   Para distribuir, comprima la carpeta dist\DaePointConnector\
    echo.
) else (
    echo.
    echo   ERROR: No se encontro el ejecutable compilado
    echo.
)
pause
