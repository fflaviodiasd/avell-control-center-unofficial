#!/usr/bin/env python3
import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QTextEdit, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal

class UninstallWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, sudo_password):
        super().__init__()
        self.sudo_password = sudo_password

    def run(self):
        uninstall_script = """#!/bin/bash
echo "Parando e desabilitando serviço systemd..."
systemctl stop avell-leds.service 2>/dev/null || true
systemctl disable avell-leds.service 2>/dev/null || true
rm -f /etc/systemd/system/avell-leds.service

echo "Removendo atalhos do menu de aplicativos (Global e Local)..."
rm -f /usr/share/applications/avell-control-center.desktop
rm -f /usr/share/applications/avell-led.desktop
# Busca e remove atalhos locais de todos os usuários (se houver)
find /home -name "avell-*.desktop" -path "*/.local/share/applications/*" -delete 2>/dev/null || true
rm -f ~/.local/share/applications/avell-led.desktop 2>/dev/null || true
rm -f ~/.local/share/applications/avell-control-center.desktop 2>/dev/null || true

echo "Removendo arquivos da aplicação em /opt..."
rm -rf /opt/avell-control-center

echo "Recarregando daemon do sistema..."
systemctl daemon-reload

echo "Desinstalação concluída com sucesso."
"""
        try:
            tmp_script = "/tmp/uninstall_avell.sh"
            with open(tmp_script, "w") as f:
                f.write(uninstall_script)

            process = subprocess.Popen(
                ['sudo', '-S', 'bash', tmp_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            process.stdin.write(self.sudo_password + '\n')
            process.stdin.flush()

            for line in process.stdout:
                self.output_signal.emit(line.strip())
            
            process.wait()
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.output_signal.emit(f"Erro: {str(e)}")
            self.finished_signal.emit(-1)

class UninstallerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desinstalar Avell Control Center")
        self.setFixedSize(450, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        self.label = QLabel("Tem certeza que deseja remover o Avell Control Center?\nIsso removerá o serviço de boot, o atalho e os arquivos do sistema.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("Senha do Sudo")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pwd_input)

        self.btn_uninstall = QPushButton("Desinstalar Agora")
        self.btn_uninstall.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold; padding: 10px;")
        self.btn_uninstall.clicked.connect(self.start_uninstall)
        layout.addWidget(self.btn_uninstall)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0;")
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def start_uninstall(self):
        pwd = self.pwd_input.text()
        if not pwd:
            QMessageBox.warning(self, "Erro", "Insira a senha.")
            return

        self.btn_uninstall.setEnabled(False)
        self.worker = UninstallWorker(pwd)
        self.worker.output_signal.connect(self.log_output.append)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, code):
        if code == 0:
            QMessageBox.information(self, "Sucesso", "O sistema foi removido.")
            sys.exit(0)
        else:
            QMessageBox.critical(self, "Erro", "A desinstalação falhou. Verifique a senha.")
            self.btn_uninstall.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UninstallerApp()
    window.show()
    sys.exit(app.exec())
