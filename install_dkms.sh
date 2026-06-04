#!/bin/bash
# =============================================================
# Script: install_dkms.sh
# Finalidade: Registrar os módulos ite_8291 e ite_8291_lb no
# DKMS para que sejam recompilados AUTOMATICAMENTE a cada
# atualização de kernel. Executar como root (sudo).
# =============================================================

set -e

TUXEDO_SRC="/tmp/tuxedo-drivers"
TUXEDO_NAME="tuxedo-avell"

echo "=== Configurando módulos Tuxedo com DKMS ==="

# --- 1. Instalar dependências necessárias ---
echo "> Instalando dependências de compilação..."
apt-get install -y --quiet dkms git build-essential linux-headers-$(uname -r) flex bison

# --- 2. Baixar o código-fonte do Tuxedo ---
echo "> Baixando código-fonte dos drivers..."
[ -d "$TUXEDO_SRC" ] && rm -rf "$TUXEDO_SRC"
git clone --depth=1 https://github.com/tuxedocomputers/tuxedo-drivers.git "$TUXEDO_SRC"
cd "$TUXEDO_SRC"

# --- 3. Determinar versão ---
TUXEDO_VER=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "1.0.0")
echo "> Versão detectada: $TUXEDO_VER"

DKMS_SRC="/usr/src/${TUXEDO_NAME}-${TUXEDO_VER}"

# --- 4. Remover versão antiga do DKMS (se existir) ---
if dkms status | grep -q "${TUXEDO_NAME}"; then
    OLD_VER=$(dkms status | grep "${TUXEDO_NAME}" | awk -F'/' '{print $2}' | awk '{print $1}' | head -1)
    echo "> Removendo versão antiga ${OLD_VER} do DKMS..."
    dkms remove "${TUXEDO_NAME}/${OLD_VER}" --all || true
fi

# --- 5. Copiar fonte para o diretório do DKMS ---
echo "> Copiando fonte para $DKMS_SRC..."
rm -rf "$DKMS_SRC"
mkdir -p "$DKMS_SRC"
cp -r "$TUXEDO_SRC/." "$DKMS_SRC/"

# --- 6. Criar dkms.conf ---
echo "> Criando configuração do DKMS..."
cat > "$DKMS_SRC/dkms.conf" << EOF
PACKAGE_NAME="${TUXEDO_NAME}"
PACKAGE_VERSION="${TUXEDO_VER}"
AUTOINSTALL="yes"

MAKE[0]="make -C src/ite_8291 KDIR=/lib/modules/\${kernelver}/build"
CLEAN[0]="make -C src/ite_8291 KDIR=/lib/modules/\${kernelver}/build clean"
BUILT_MODULE_NAME[0]="ite_8291"
BUILT_MODULE_LOCATION[0]="src/ite_8291/"
DEST_MODULE_LOCATION[0]="/updates/src/ite_8291"

MAKE[1]="make -C src/ite_8291_lb KDIR=/lib/modules/\${kernelver}/build"
CLEAN[1]="make -C src/ite_8291_lb KDIR=/lib/modules/\${kernelver}/build clean"
BUILT_MODULE_NAME[1]="ite_8291_lb"
BUILT_MODULE_LOCATION[1]="src/ite_8291_lb/"
DEST_MODULE_LOCATION[1]="/updates/src/ite_8291_lb"
EOF

# --- 7. Registrar, compilar e instalar via DKMS ---
echo "> Registrando no DKMS..."
dkms add -m "${TUXEDO_NAME}" -v "${TUXEDO_VER}"

echo "> Compilando para o kernel atual ($(uname -r))..."
dkms build -m "${TUXEDO_NAME}" -v "${TUXEDO_VER}" -k "$(uname -r)"

echo "> Instalando módulos..."
dkms install -m "${TUXEDO_NAME}" -v "${TUXEDO_VER}" -k "$(uname -r)" --force

depmod -a

# --- 8. Carregar os módulos agora ---
echo "> Carregando módulos..."
modprobe ite_8291 || echo "Aviso: ite_8291 não carregado (verifique Secure Boot)"
modprobe ite_8291_lb || echo "Aviso: ite_8291_lb não carregado"

# --- 9. Garantir carga automática no boot ---
for mod in ite_8291 ite_8291_lb; do
    grep -q "^${mod}" /etc/modules 2>/dev/null || echo "${mod}" >> /etc/modules
done

# --- 10. Verificação final ---
echo ""
echo "=== RESULTADO ==="
dkms status | grep "${TUXEDO_NAME}" && echo "[OK] DKMS configurado com sucesso!"

if ls /sys/class/leds/ | grep -q lightbar; then
    echo "[OK] Lightbar disponível em /sys/class/leds/"
else
    echo "[AVISO] Lightbar ainda não aparece. Pode ser necessário reiniciar."
fi

echo ""
echo ">>> A partir de agora, sempre que o kernel atualizar, os módulos"
echo ">>> serão recompilados AUTOMATICAMENTE pelo DKMS. Sem ação manual!"
