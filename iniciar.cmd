@echo off
setlocal
if not exist "%~dp0index.html" (
    echo ERRO: index.html nao encontrado. Extrai ou copia a pasta completa do projeto.
    echo No Arranque do Windows, cria um atalho para este script; nao copies o script sozinho.
    pause
    exit /b 1
)

if not exist "%~dp0serve.py" (
    echo ERRO: serve.py nao encontrado. Extrai ou copia a pasta completa do projeto.
    pause
    exit /b 1
)

python3 -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python3"
    goto serve
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto serve
)

python -c "import sys; sys.exit(sys.version_info.major != 3)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto serve
)

echo ERRO: Python 3 nao encontrado. Instala Python 3 e ativa a opcao de adicionar ao PATH.
pause
exit /b 1

:serve
pushd "%~dp0"
if errorlevel 1 (
    echo ERRO: Nao foi possivel aceder a pasta do projeto.
    pause
    exit /b 1
)
echo A iniciar o servidor HTTP. Mantem esta janela aberta para acesso pela intranet.
echo Comando: %PYTHON% -u .\serve.py %*
%PYTHON% -u ".\serve.py" %*
if errorlevel 1 (
    popd
    echo ERRO: O servidor terminou com erro. Verifica a mensagem acima.
    pause
    exit /b 1
)
popd
exit /b 0
