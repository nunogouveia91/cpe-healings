@echo off
if not exist "%~dp0index.html" (
    echo ERRO: index.html nao encontrado. Extrai ou copia a pasta completa do projeto.
    pause
    exit /b 1
)

start "" "%~dp0index.html"
if errorlevel 1 (
    echo ERRO: Nao foi possivel abrir o dashboard. Verifica o browser predefinido.
    pause
    exit /b 1
)
exit /b 0
