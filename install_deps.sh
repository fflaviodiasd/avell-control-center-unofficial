#!/bin/bash

# Script de instalação de dependências.
# DEVE SER EXECUTADO COMO ROOT (sudo).
# Argumento 1: Nome do usuário real (para configurar o sudoers).

REAL_USER=$1
MANUAL_ID=$2
if [ -z "$REAL_USER" ]; then
    echo "Erro: Forneça o nome do usuário."
    exit 1
fi

echo -e "=== INSTALADOR AUTOMÁTICO AVELL LED CONTROL ==="

echo -e "> Verificando dependências já instaladas..."
TUXEDO_INSTALLED=0
modinfo tuxedo_nb04_keyboard &> /dev/null && TUXEDO_INSTALLED=1

AUCC_INSTALLED=0
if command -v pip3 &> /dev/null; then
    pip3 show aucc &> /dev/null && AUCC_INSTALLED=1
fi

if [ $TUXEDO_INSTALLED -eq 1 ] && [ $AUCC_INSTALLED -eq 1 ]; then
    echo -e "[OK] Dependências já configuradas na máquina. Pulando etapa de download e compilação..."
else
    # 1. Instalação de Dependências
    echo -e "> Baixando pacotes de sistema necessários..."
    export DEBIAN_FRONTEND=noninteractive
    apt update && apt install -y git build-essential dkms linux-headers-$(uname -r) \
    flex bison libfuse2 python3-pip python3-setuptools usbutils python3-pyqt6

    if [ $TUXEDO_INSTALLED -eq 0 ]; then
        # 2. Compilação e instalação dos Drivers Tuxedo via DKMS
        echo -e "> Compilando e instalando drivers de hardware via DKMS..."
        cd /tmp
        [ -d "tuxedo-drivers" ] && rm -rf tuxedo-drivers
        git clone https://github.com/tuxedocomputers/tuxedo-drivers.git
        cd tuxedo-drivers

        TUXEDO_VER=$(git describe --tags --abbrev=0 2>/dev/null || echo "1.0")
        TUXEDO_NAME="tuxedo-drivers"
        DKMS_SRC="/usr/src/${TUXEDO_NAME}-${TUXEDO_VER}"

        # Copia o fonte para onde o DKMS espera
        mkdir -p "$DKMS_SRC"
        cp -r . "$DKMS_SRC/"

        # Cria dkms.conf se não existir
        if [ ! -f "$DKMS_SRC/dkms.conf" ]; then
            cat > "$DKMS_SRC/dkms.conf" << DKMSEOF
PACKAGE_NAME="${TUXEDO_NAME}"
PACKAGE_VERSION="${TUXEDO_VER}"
MAKE="make -C \${kernel_source_dir} M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build modules"
CLEAN="make -C \${kernel_source_dir} M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build clean"
AUTOINSTALL="yes"
BUILT_MODULE_NAME[0]="ite_8291"
BUILT_MODULE_LOCATION[0]="src/ite_8291/"
DEST_MODULE_LOCATION[0]="/updates/src/ite_8291"
BUILT_MODULE_NAME[1]="ite_8291_lb"
BUILT_MODULE_LOCATION[1]="src/ite_8291_lb/"
DEST_MODULE_LOCATION[1]="/updates/src/ite_8291_lb"
DKMSEOF
        fi

        dkms add -m "${TUXEDO_NAME}" -v "${TUXEDO_VER}" || true
        dkms build -m "${TUXEDO_NAME}" -v "${TUXEDO_VER}" -k "$(uname -r)"
        dkms install -m "${TUXEDO_NAME}" -v "${TUXEDO_VER}" -k "$(uname -r)" --force
        depmod -a
    else
        echo -e "[OK] Módulos Tuxedo já compilados. Verificando se o kernel atual está coberto..."
        # Recompila para o kernel atual se necessário (após update do kernel)
        TUXEDO_DKMS=$(dkms status 2>/dev/null | grep tuxedo | head -1 | awk -F, '{print $1}' | awk '{print $1}')
        if [ -n "$TUXEDO_DKMS" ]; then
            TUXEDO_VER_DKMS=$(dkms status 2>/dev/null | grep tuxedo | head -1 | awk -F'/' '{print $2}' | awk '{print $1}')
            if ! dkms status | grep -q "$(uname -r)"; then
                echo -e "> Recompilando módulos para o kernel $(uname -r)..."
                dkms build -m "tuxedo-drivers" -v "${TUXEDO_VER_DKMS}" -k "$(uname -r)"
                dkms install -m "tuxedo-drivers" -v "${TUXEDO_VER_DKMS}" -k "$(uname -r)" --force
                depmod -a
            fi
        fi
    fi

    if [ $AUCC_INSTALLED -eq 0 ]; then
        # 4. Instalação do Controlador de Teclado (AUCC)
        echo -e "> Instalando motor do teclado (AUCC)..."
        if ! command -v pip3 &> /dev/null; then
            echo -e "[ERRO] pip3 não foi instalado corretamente via apt! Interrompendo a instalação."
            exit 1
        fi
        cd /tmp
        [ -d "avell-unofficial-control-center" ] && rm -rf avell-unofficial-control-center
        git clone https://github.com/rodgomesc/avell-unofficial-control-center.git
        cd avell-unofficial-control-center
        pip3 install . --break-system-packages
    else
        echo -e "[OK] Motor AUCC já está instalado."
    fi
fi

# 3. Carregamento dos Módulos
echo -e "> Ativando módulos de suporte (Lightbar)..."
modprobe ite_8291 || echo -e "Aviso: Key Rejected. Verifique o Secure Boot na BIOS!"
modprobe ite_8291_lb
# Removemos o driver de teclado do kernel para evitar que ele "tranque" o USB,
# permitindo que o AUCC (Python) assuma o controle total.
modprobe -r tuxedo_nb04_keyboard 2>/dev/null || true

# 5. AJUSTE INTELIGENTE: Detecção de ID Real do Teclado
echo -e "> Localizando o chip ITE Device(8291) - Controlador de LED..."

# Filtra especificamente a linha que contém o modelo do teclado (8291)
# e extrai o ID de 4 dígitos (ex: 600b)
HW_ID=$(lsusb | grep "048d" | grep "(8291)" | grep -oP '048d:\K[0-9a-f]{4}')

if [ -z "$HW_ID" ] && [ -z "$MANUAL_ID" ]; then
    echo -e "[ERRO] Dispositivo ITE Device(8291) não encontrado via USB e nenhum ID manual foi fornecido."
    echo -e "Aviso: A máquina pode utilizar interface ACPI/WMI, e o aucc será ignorado."
else
    FINAL_ID=${MANUAL_ID:-$HW_ID}
    echo -e "[OK] Teclado (8291) configurado para usar o ID: 0x$FINAL_ID"
    # 6. Aplicação do Patch de ID no Código Python
    PYTHON_PATH=$(pip3 show avell-unofficial-control-center | grep Location | awk '{print $2}')/aucc/main.py

    if [ -f "$PYTHON_PATH" ]; then
        echo -e "> Aplicando patch no arquivo $PYTHON_PATH..."
        sed -i "s/product_id=0x[0-9a-f]\{4\}/product_id=0x${FINAL_ID}/g" "$PYTHON_PATH"
        echo -e "[OK] Configuração de hardware 0x${FINAL_ID} aplicada no main.py."
        
        # Correção do bug crítico da biblioteca aucc (NoneType Error)
        HANDLER_PATH=$(dirname "$PYTHON_PATH")/core/handler.py
        if [ -f "$HANDLER_PATH" ]; then
            echo -e "> Aplicando patch de segurança no handler.py..."
            # Escreve um script python temporario para reescrever o arquivo para ser mais robusto e não depender de sed
            python3 -c "
import sys
with open('$HANDLER_PATH', 'r') as f:
    lines = f.readlines()
with open('$HANDLER_PATH', 'w') as f:
    in_get_device = False
    for line in lines:
        if 'def _get_device' in line:
            in_get_device = True
            f.write(line)
            continue
        if in_get_device and 'def _get_interface' in line:
            in_get_device = False
        
        if in_get_device:
            if 'device = usb.core.find' in line:
                f.write(line)
                f.write('        if device is None:\n')
                f.write('            raise ValueError(f\"Dispositivo USB não encontrado pelo sistema. Verifique as permissões ou se o ID {vendor:04x}:{product:04x} está correto.\")\n')
                continue
            if 'if device is None:' in line or 'raise ValueError' in line or 'else:' in line or 'return device' in line:
                continue
            if 'if not sys.platform.startswith' in line:
                f.write(line)
                continue
            if 'if device.is_kernel_driver_active' in line:
                f.write(line)
                continue
            if 'device.detach_kernel_driver' in line:
                f.write(line)
                f.write('        return device\n')
                continue
        f.write(line)
"
            echo -e "[OK] Patch de segurança do aucc aplicado com sucesso."
        fi
        
        # Limpar o cache do Python para forçar a recompilação com o ID correto
        rm -rf $(dirname "$PYTHON_PATH")/__pycache__
        rm -rf $(dirname "$PYTHON_PATH")/core/__pycache__
    else
        echo -e "[ERRO] Falha ao localizar o motor AUCC para aplicar o patch."
    fi
fi

# 7. Configuração de Boot e Permissões (Sudoers)
echo -e "> Finalizando permissões e inicialização..."

# Adiciona módulos ao boot
# Adiciona apenas os módulos da Lightbar ao boot (o teclado será via AUCC)
for mod in ite_8291 ite_8291_lb; do
    grep -q "^$mod" /etc/modules || echo "$mod" >> /etc/modules
done

# Configura sudoers para a GUI funcionar sem senha
SUDO_CONFIG="$REAL_USER ALL=(ALL) NOPASSWD: /usr/local/bin/aucc, /usr/bin/tee /sys/class/leds/rgb\:lightbar/*"
if ! grep -q "/usr/local/bin/aucc" /etc/sudoers; then
    echo "$SUDO_CONFIG" >> /etc/sudoers
fi

echo -e "=== TUDO PRONTO! ==="
