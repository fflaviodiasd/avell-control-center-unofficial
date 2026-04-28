#!/usr/bin/env python3
import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QWizard, QWizardPage, QVBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

class WorkerThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, cmd, sudo_password, cwd=None):
        super().__init__()
        self.cmd = cmd
        self.sudo_password = sudo_password
        self.cwd = cwd

    def run(self):
        try:
            # Roda o comando e passa a senha sudo via stdin
            process = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd
            )
            
            # Fornecer a senha caso seja solicitada
            if self.sudo_password:
                process.stdin.write(self.sudo_password + '\n')
                process.stdin.flush()

            # Ler a saída linha por linha em tempo real
            for line in process.stdout:
                self.output_signal.emit(line.strip())
            
            process.wait()
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.output_signal.emit(f"Exceção fatal: {str(e)}")
            self.finished_signal.emit(-1)

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Bem-vindo ao Instalador do Avell Control Center")
        layout = QVBoxLayout()
        label = QLabel("Este assistente guiará você pela instalação do painel de controle dos LEDs.\n\n"
                       "O processo irá:\n"
                       "1. Instalar os módulos de Kernel necessários (Tuxedo).\n"
                       "2. Baixar e compilar a engine do teclado (AUCC).\n"
                       "3. Instalar o aplicativo no seu Ubuntu de forma definitiva.\n\n"
                       "Clique em 'Avançar' para continuar.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

class AuthPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Autenticação Necessária")
        layout = QVBoxLayout()
        
        label = QLabel("Precisamos de privilégios de administrador (root) para compilar drivers do Kernel e instalar pacotes.\n"
                       "Por favor, insira sua senha de usuário:")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.registerField("sudo_password*", self.password_input)
        
        layout.addWidget(self.password_input)
        self.setLayout(layout)

    def validatePage(self):
        pwd = self.password_input.text()
        # Valida a senha usando sudo -k (invalida cache anterior) e -S -v
        p = subprocess.Popen(['sudo', '-k', '-S', '-v'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(input=pwd + '\n')
        if p.returncode != 0:
            QMessageBox.warning(self, "Erro", "Senha incorreta ou usuário sem privilégios sudo. Tente novamente.")
            return False
        return True

class DependencyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Instalando Dependências e Drivers")
        self.is_complete = False
        
        layout = QVBoxLayout()
        self.label = QLabel("Por favor, aguarde enquanto os pacotes são baixados e os módulos do Kernel são compilados...\nIsso pode levar alguns minutos.")
        layout.addWidget(self.label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; font-family: monospace;")
        layout.addWidget(self.log_output)
        
        self.setLayout(layout)

    def initializePage(self):
        pwd = self.field("sudo_password")
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'install_deps.sh')
        real_user = os.environ.get('USER', 'root')
        
        cmd = ['sudo', '-S', 'bash', script_path, real_user]
        
        self.thread = WorkerThread(cmd, pwd)
        self.thread.output_signal.connect(self.append_log)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def append_log(self, text):
        self.log_output.append(text)
        # Scroll para o fim
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_finished(self, returncode):
        if returncode == 0:
            self.label.setText("Instalação das dependências concluída com sucesso! Clique em 'Avançar'.")
            self.is_complete = True
            self.completeChanged.emit()
        else:
            self.label.setText("Ocorreu um erro durante a instalação. Verifique os logs acima.")
            self.label.setStyleSheet("color: red; font-weight: bold;")

    def isComplete(self):
        return self.is_complete

class SystemInstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Instalando Aplicativo")
        self.is_complete = False
        
        layout = QVBoxLayout()
        self.label = QLabel("Instalando o Avell Control Center no sistema...")
        layout.addWidget(self.label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; font-family: monospace;")
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def initializePage(self):
        pwd = self.field("sudo_password")
        real_user = os.environ.get('USER', 'root')
        source_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        
        # Script on-the-fly para instalar no /opt e criar systemd
        install_script = f"""#!/bin/bash
set -e
echo "Criando diretório /opt/avell-control-center..."
mkdir -p /opt/avell-control-center
echo "Copiando binário da aplicação..."
cp "{source_dir}/avell-led-control" /opt/avell-control-center/
cp "{source_dir}/icon.png" /opt/avell-control-center/ 2>/dev/null || true
chmod 755 /opt/avell-control-center/avell-led-control
chmod 644 /opt/avell-control-center/icon.png 2>/dev/null || true

echo "Criando atalho de aplicativo (.desktop)..."
cat <<EOF > /usr/share/applications/avell-control-center.desktop
[Desktop Entry]
Name=Avell Control Center
Comment=Controle de LEDs do Teclado e Lightbar
Exec=/opt/avell-control-center/avell-led-control
Icon=/opt/avell-control-center/icon.png
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;
EOF

chmod 644 /usr/share/applications/avell-control-center.desktop
update-desktop-database /usr/share/applications 2>/dev/null || true

echo "Configurando serviço Systemd para boot..."
cat <<EOF > /etc/systemd/system/avell-leds.service
[Unit]
Description=Avell LEDs Configuration on Boot
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/opt/avell-control-center/avell-led-control --boot --config /home/{real_user}/.config/avell-gui-settings.json
RemainAfterExit=yes
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

echo "Recarregando daemon..."
systemctl daemon-reload
echo "Habilitando serviço..."
systemctl enable avell-leds.service

echo "Criação concluída."
"""
        # Salvamos esse script on-the-fly num arquivo temporário
        tmp_script = "/tmp/install_avell_app.sh"
        with open(tmp_script, "w") as f:
            f.write(install_script)
            
        cmd = ['sudo', '-S', 'bash', tmp_script]
        self.thread = WorkerThread(cmd, pwd)
        self.thread.output_signal.connect(self.append_log)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def append_log(self, text):
        self.log_output.append(text)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_finished(self, returncode):
        if returncode == 0:
            self.label.setText("Cópia e atalhos configurados com sucesso! Clique em 'Avançar'.")
            self.is_complete = True
            self.completeChanged.emit()
        else:
            self.label.setText("Ocorreu um erro ao copiar os arquivos.")
            self.label.setStyleSheet("color: red; font-weight: bold;")

    def isComplete(self):
        return self.is_complete

class ConclusionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Instalação Concluída!")
        layout = QVBoxLayout()
        label = QLabel("O Avell Control Center foi instalado com sucesso no seu sistema.\n\n"
                       "Você agora pode encontrar o programa no menu de aplicativos do Ubuntu (pressione a tecla Super/Windows e digite 'Avell').\n\n"
                       "A partir de agora, as configurações de LEDs serão persistentes a cada boot do sistema e sua experiência está completa!\n\n"
                       "Clique em 'Concluir' para fechar.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

class InstallWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instalador - Avell Control Center")
        self.setFixedSize(600, 450)
        
        self.addPage(IntroPage())
        self.addPage(AuthPage())
        self.addPage(DependencyPage())
        self.addPage(SystemInstallPage())
        self.addPage(ConclusionPage())

        self.setStyleSheet("""
            QWizard {
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Ubuntu', sans-serif;
            }
            QLabel { color: #e0e0e0; font-size: 13px; }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #007acc;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005f9e; }
            QPushButton:disabled { background-color: #3d3d3d; color: #888888; }
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    wizard = InstallWizard()
    wizard.show()
    sys.exit(app.exec())
