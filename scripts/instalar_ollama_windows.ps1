# Instala Ollama (si no esta ya instalado) y descarga el modelo que usa
# el bot por defecto. Pensado para ejecutarse con doble clic sobre
# instalar_ollama_windows.bat (que llama a este script).
#
# Qué hace, en orden:
#   1. Comprueba si el comando "ollama" ya existe.
#   2. Si no existe, descarga el instalador oficial desde ollama.com y lo
#      ejecuta en modo silencioso (sin ventanas que haya que ir cerrando).
#   3. Descarga el modelo "llama3.1" (el que usa el bot por defecto).
#   4. Deja un mensaje final claro de si todo salio bien.
#
# Si algo falla (por ejemplo, sin conexion a internet), este script no
# toca nada mas de tu sistema: solo instala Ollama y descarga el modelo.

$ErrorActionPreference = "Stop"

function Write-Step($texto) {
    Write-Host ""
    Write-Host "==> $texto" -ForegroundColor Cyan
}

Write-Step "Comprobando si Ollama ya esta instalado..."
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaCmd) {
    Write-Step "Ollama no esta instalado. Descargando el instalador oficial..."
    $installerPath = Join-Path $env:TEMP "OllamaSetup.exe"
    try {
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Host ""
        Write-Host "No se pudo descargar el instalador de Ollama." -ForegroundColor Red
        Write-Host "Comprueba tu conexion a internet e intentalo de nuevo, o descarga" -ForegroundColor Red
        Write-Host "Ollama manualmente desde https://ollama.com/download" -ForegroundColor Red
        exit 1
    }

    Write-Step "Instalando Ollama (modo silencioso, no deberia pedirte nada)..."
    try {
        Start-Process -FilePath $installerPath -ArgumentList "/VERYSILENT", "/NORESTART" -Wait
    } catch {
        Write-Host ""
        Write-Host "La instalacion silenciosa fallo. Abre manualmente el instalador" -ForegroundColor Yellow
        Write-Host "descargado en: $installerPath" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Ollama instalado."

    # El PATH de esta sesion de PowerShell no incluye lo que acaba de
    # instalar el instalador: lo recargamos desde el registro de Windows.
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
} else {
    Write-Host "Ollama ya estaba instalado en: $($ollamaCmd.Source)"
}

Write-Step "Descargando el modelo 'llama3.1' (puede tardar varios minutos, son varios GB)..."
try {
    & ollama pull llama3.1
} catch {
    Write-Host ""
    Write-Host "No se pudo descargar el modelo. Si Ollama se acaba de instalar," -ForegroundColor Yellow
    Write-Host "puede que necesites cerrar y volver a abrir esta ventana (o reiniciar" -ForegroundColor Yellow
    Write-Host "el PC) para que Windows reconozca el nuevo programa, y volver a" -ForegroundColor Yellow
    Write-Host "ejecutar este script." -ForegroundColor Yellow
    exit 1
}

Write-Step "Listo."
Write-Host "Ollama esta instalado y el modelo 'llama3.1' descargado." -ForegroundColor Green
Write-Host "Ya puedes jugar sin configurar nada mas: python cli.py play" -ForegroundColor Green
