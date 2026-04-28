#!/bin/bash

# Script de instalação de dependências.
# DEVE SER EXECUTADO COMO ROOT (sudo).
# Argumento 1: Nome do usuário real (para configurar o sudoers).

REAL_USER=$1
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
        # 2. Compilação dos Drivers Tuxedo (Kernel)
        echo -e "> Compilando drivers de hardware..."
        cd /tmp
        [ -d "tuxedo-drivers" ] && rm -rf tuxedo-drivers
        git clone https://github.com/tuxedocomputers/tuxedo-drivers.git
        cd tuxedo-drivers && make clean && make
        make install PWD=$(pwd)
        depmod -a
    else
        echo -e "[OK] Módulos Tuxedo já compilados."
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

if [ -z "$HW_ID" ]; then
    echo -e "[ERRO] Dispositivo ITE Device(8291) não encontrado via USB."
    echo -e "Aviso: A máquina pode utilizar interface ACPI/WMI, e o aucc será ignorado."
else
    echo -e "[OK] Teclado (8291) identificado: 0x$HW_ID"
    # 6. Aplicação do Patch de ID no Código Python
    PYTHON_PATH=$(pip3 show avell-unofficial-control-center | grep Location | awk '{print $2}')/aucc/main.py

    if [ -f "$PYTHON_PATH" ]; then
        echo -e "> Aplicando patch no arquivo $PYTHON_PATH..."
        # Patch fixo solicitado pelo usuário
        sed -i 's/product_id=0x[0-9a-f]\{4\}/product_id=0x600b/g' "$PYTHON_PATH"
        echo -e "[OK] Configuração de hardware 0x600b aplicada."
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
