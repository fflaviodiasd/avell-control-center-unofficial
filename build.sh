#!/bin/bash
# =============================================================
# build.sh — Script de compilação do Avell Control Center
# Uso:
#   ./build.sh           → Compila app + instalador
#   ./build.sh --all     → Compila app + instalador + desinstalador
#   ./build.sh --deploy  → Compila tudo e atualiza /opt + serviço
# =============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/venv/bin/activate"
DIST="dist_v1"
BUILD="build_v1"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

BUILD_ALL=false
DEPLOY=false

for arg in "$@"; do
    case $arg in
        --all)    BUILD_ALL=true ;;
        --deploy) DEPLOY=true; BUILD_ALL=true ;;
    esac
done

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════╗"
echo "║     Avell Control Center — Build Script       ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# --- Verificações iniciais ---
if [ ! -f "$VENV" ]; then
    echo -e "${RED}[ERRO] venv não encontrado em $VENV${NC}"
    echo "       Crie com: python3 -m venv venv && source venv/bin/activate && pip install pyinstaller pyqt6"
    exit 1
fi

cd "$SCRIPT_DIR"
source "$VENV"

if ! command -v pyinstaller &>/dev/null; then
    echo -e "${RED}[ERRO] pyinstaller não encontrado no venv.${NC}"
    echo "       Instale com: pip install pyinstaller"
    exit 1
fi

# --- Função de build ---
build_spec() {
    local spec="$1"
    local label="$2"
    echo -e "${YELLOW}▶ Compilando: $label${NC}"
    pyinstaller --noconfirm --distpath "$DIST" --workpath "$BUILD" "$spec"
    echo -e "${GREEN}✔ $label compilado com sucesso!${NC}"
    echo ""
}

# --- 1. App principal (deve ser sempre o primeiro) ---
build_spec "avell-led-control.spec" "Avell LED Control (app principal)"

# --- 2. Instalador (embarca o app acima) ---
build_spec "Instalador-Avell.spec" "Instalador Avell"

# --- 3. Desinstalador (opcional) ---
if [ "$BUILD_ALL" = true ]; then
    build_spec "Desinstalar-Avell.spec" "Desinstalador Avell"
fi

# --- 4. Resultado ---
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}✔ Build concluído!${NC}"
echo ""
echo "Arquivos gerados em: $SCRIPT_DIR/$DIST/"
ls -lh "$SCRIPT_DIR/$DIST/"
echo ""

# --- 5. Deploy (opcional: copia para /opt e reinicia serviço) ---
if [ "$DEPLOY" = true ]; then
    echo -e "${YELLOW}▶ Realizando deploy em /opt/avell-control-center/...${NC}"
    sudo cp "$DIST/avell-led-control" /opt/avell-control-center/avell-led-control
    sudo chmod 755 /opt/avell-control-center/avell-led-control
    sudo systemctl daemon-reload
    sudo systemctl restart avell-leds.service
    echo ""
    echo -e "${GREEN}✔ Deploy concluído! Status do serviço:${NC}"
    journalctl -u avell-leds.service --no-pager -n 5
fi
