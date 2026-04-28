#!/bin/bash

# Verifica se está rodando como root (via sudo)
if [ "$EUID" -ne 0 ]; then
  echo "Por favor, execute este script com sudo: sudo bash install_service.sh"
  exit
fi

SERVICE_FILE="/etc/systemd/system/avell-leds.service"
PYTHON_BIN="/usr/bin/python3"
CONFIG_PATH="/home/$SUDO_USER/.config/avell-gui-settings.json"
APPLY_SCRIPT="/home/ffsilva/Documentos/avell-gui/main.py --boot --config $CONFIG_PATH"

# ATENÇÃO: Quando você compilar com o PyInstaller (ex: criar o binário 'avell-gui'), 
# altere a linha ExecStart abaixo para rodar apenas o binário compilado.
# Exemplo: ExecStart=/usr/local/bin/avell-gui --boot --config /home/ffsilva/.config/avell-gui-settings.json

echo "Criando serviço systemd em $SERVICE_FILE..."

cat <<EOF > $SERVICE_FILE
[Unit]
Description=Avell LEDs Configuration on Boot
After=multi-user.target

[Service]
Type=oneshot
ExecStart=$PYTHON_BIN $APPLY_SCRIPT
RemainAfterExit=yes
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

echo "Recarregando daemon do systemd..."
systemctl daemon-reload

echo "Habilitando o serviço para rodar no boot..."
systemctl enable avell-leds.service

echo "Iniciando o serviço agora (teste)..."
systemctl start avell-leds.service

echo "================================================="
echo "Sucesso! O serviço foi instalado e configurado."
echo "As configurações do Avell Control Center agora"
echo "serão aplicadas automaticamente quando o sistema ligar,"
echo "sem precisar abrir o aplicativo."
echo "================================================="
