import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QHBoxLayout, QFrame, QSystemTrayIcon, QMenu,
                             QInputDialog, QLineEdit, QMessageBox, QColorDialog, QComboBox, QCheckBox,
                             QTabWidget, QSlider, QSpinBox)
import json
import argparse
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QTimer
from monitor_widgets import CpuAreaChart, RamStackedBar, DiskDonutChart, NetMirroredChart

class AvellHardwareManager:
    """Classe responsável por gerenciar a comunicação com o hardware via Shell"""
    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self.sudo_password = None
        self.lb_anim_process = None
        self.last_lb_color = (0, 150, 255)
        self.last_kbd_color_suffix = ""

    def _get_aucc_anim_color_suffix(self, r, g, b):
        colors = {
            'r': (255, 0, 0), 'o': (255, 165, 0), 'y': (255, 255, 0),
            'g': (0, 255, 0), 'b': (0, 0, 255), 't': (0, 128, 128), 'p': (128, 0, 128)
        }
        def color_distance(c1, c2):
            return sum((a - b) ** 2 for a, b in zip(c1, c2))
        return min(colors.keys(), key=lambda k: color_distance((r, g, b), colors[k]))

    def get_sudo_password(self):
        if self.sudo_password is None and self.parent_widget:
            password, ok = QInputDialog.getText(
                self.parent_widget,
                "Autenticação Necessária",
                "Digite sua senha (sudo) para aplicar as configurações:",
                QLineEdit.EchoMode.Password
            )
            if ok and password:
                self.sudo_password = password
        return self.sudo_password
    
    def run_command(self, cmd_list):
        """Executa comandos enviando a senha via sudo -S (ignora se for root)"""
        if os.geteuid() == 0:
            if cmd_list[0] == 'sudo':
                if len(cmd_list) > 1 and cmd_list[1] == '-S':
                    cmd_list = cmd_list[2:]
                else:
                    cmd_list = cmd_list[1:]
            try:
                subprocess.Popen(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Erro root: {e}")
            return

        pwd = self.get_sudo_password()
        if not pwd:
            return

        try:
            if cmd_list[0] == 'sudo':
                cmd_list.insert(1, '-S')
            
            p = subprocess.Popen(cmd_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = p.communicate(input=pwd + '\n')
            
            if p.returncode != 0:
                print(f"Erro: {err}")
                if "incorrect password" in err.lower() or "senha incorreta" in err.lower() or "try again" in err.lower():
                    self.sudo_password = None
                    if self.parent_widget:
                        QMessageBox.warning(self.parent_widget, "Erro", "Senha incorreta. Tente novamente.")
        except Exception as e:
            print(f"Erro ao executar comando {cmd_list}: {e}")

    def _get_closest_aucc_color(self, r, g, b):
        colors = {
            'red': (255, 0, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255),
            'teal': (0, 128, 128), 'pink': (255, 192, 203), 'purple': (128, 0, 128),
            'white': (255, 255, 255), 'yellow': (255, 255, 0), 'orange': (255, 165, 0),
            'olive': (128, 128, 0), 'maroon': (128, 0, 0), 'brown': (165, 42, 42),
            'gray': (128, 128, 128), 'skyblue': (135, 206, 235), 'navy': (0, 0, 128),
            'crimson': (220, 20, 60), 'darkgreen': (0, 100, 0), 'lightgreen': (144, 238, 144),
            'gold': (255, 215, 0), 'violet': (238, 130, 238)
        }
        def color_distance(c1, c2):
            return sum((a - b) ** 2 for a, b in zip(c1, c2))
        return min(colors.keys(), key=lambda k: color_distance((r, g, b), colors[k]))

    def set_keyboard_rgb(self, r, g, b, brightness=4):
        closest = self._get_closest_aucc_color(r, g, b)
        self.last_kbd_color_suffix = self._get_aucc_anim_color_suffix(r, g, b)
        self.run_command(['sudo', 'aucc', '-c', closest, '-b', str(brightness)])

    def set_keyboard(self, mode="rainbow", color=None, brightness=4, anim_style="rainbow", use_fixed=False):
        if mode == "static" and color:
            self.run_command(['sudo', 'aucc', '-c', color, '-b', str(brightness)])
        elif mode == "rainbow":
            self.run_command(['sudo', 'aucc', '-s', 'rainbow'])
        elif mode == "anim":
            if use_fixed and anim_style != "rainbow" and self.last_kbd_color_suffix:
                self.run_command(['sudo', 'aucc', '-s', anim_style + self.last_kbd_color_suffix])
            else:
                self.run_command(['sudo', 'aucc', '-s', anim_style])
        elif mode == "off":
            self.run_command(['sudo', 'aucc', '-d'])

    def stop_lightbar_anim(self):
        self.run_command(['sudo', 'pkill', '-f', 'lightbar_anim.py'])
        if self.lb_anim_process:
            self.lb_anim_process = None

    def set_lightbar_anim(self, mode, use_fixed=False):
        self.stop_lightbar_anim()
        if not self.lightbar_available():
            print("Aviso: Lightbar não disponível. Módulo ite_8291_lb não carregado ou hardware ausente.")
            return
        cmd = ['sudo', '-S', 'python3', os.path.join(os.path.dirname(__file__), 'lightbar_anim.py'), mode]
        if use_fixed and mode == "breathing":
            cmd.extend([str(self.last_lb_color[0]), str(self.last_lb_color[1]), str(self.last_lb_color[2])])

        if os.geteuid() == 0:
            cmd = cmd[2:]
            try:
                self.lb_anim_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(e)
            return

        pwd = self.get_sudo_password()
        if not pwd: return
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            p.stdin.write(pwd + '\n')
            p.stdin.flush()
            self.lb_anim_process = p
        except Exception as e:
            print(f"Erro ao iniciar animação da lightbar: {e}")

    def lightbar_available(self):
        """Verifica se o módulo ite_8291_lb está carregado e o caminho sysfs existe."""
        return os.path.exists('/sys/class/leds/rgb:lightbar/brightness')

    def set_lightbar(self, r, g, b, brightness=255):
        self.last_lb_color = (r, g, b)
        self.stop_lightbar_anim()
        if not self.lightbar_available():
            print("Aviso: Lightbar não disponível. Módulo ite_8291_lb não carregado ou hardware ausente.")
            return
        if brightness == 0:
            cmd = ['sudo', 'sh', '-c', 'echo 0 > /sys/class/leds/rgb:lightbar/brightness']
        else:
            cmd = ['sudo', 'sh', '-c', f'echo "{r} {g} {b}" > /sys/class/leds/rgb:lightbar/multi_intensity && echo {brightness} > /sys/class/leds/rgb:lightbar/brightness']
        self.run_command(cmd)

class AvellLEDMaster(QWidget):
    def __init__(self):
        super().__init__()
        self.hw = AvellHardwareManager(self)
        self.initUI()
        self.setupTray()
        self.restore_ui_state()

    def initUI(self):
        # Estilização Dark Mode Moderna
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Ubuntu', sans-serif;
            }
            QFrame {
                border: 1px solid #2c2c2c;
                border-radius: 10px;
                background-color: #1e1e1e;
                margin: 5px;
            }
            QLabel {
                font-weight: bold;
                font-size: 13px;
                color: #007acc;
                padding: 5px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #007acc;
            }
            QPushButton#danger {
                color: #ff5555;
            }
            QPushButton#danger:hover {
                background-color: #442222;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #007acc;
                color: white;
            }
        """)

        layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # --- ABA 1: CONTROLE DE LEDS ---
        self.tab_leds = QWidget()
        self.tab_leds_layout = QVBoxLayout(self.tab_leds)

        # --- PAINEL DO TECLADO ---
        kbd_frame = QFrame()
        kbd_vbox = QVBoxLayout(kbd_frame)
        kbd_vbox.addWidget(QLabel("⌨️ CONTROLE DO TECLADO"))
        
        kbd_anim_layout = QHBoxLayout()
        self.cb_kbd_anim = QComboBox()
        # Mapa: label exibida -> nome interno do aucc
        self._kbd_anim_map = {
            "Rainbow":              "rainbow",
            "Breathing (pulsação)": "breathing",
            "Wave (onda)": "wave",
            "Raindrop (chuva)": "raindrop",
            "Aurora": "aurora",
            "Ripple (ondulação)": "ripple",
            "Random": "random",
            "⭐ Reactive (tecla acende)": "reactive",
            "⭐ Reactive Ripple": "reactiveripple",
            "⭐ Reactive Aurora": "reactiveaurora",
            "Fireworks (fogos)": "fireworks",
            "Marquee": "marquee",
        }
        self.cb_kbd_anim.addItems(list(self._kbd_anim_map.keys()))
        # Seleciona Reactive por padrão
        self.cb_kbd_anim.setCurrentText("⭐ Reactive (tecla acende)")
        self.chk_kbd_fixed = QCheckBox("Cor fixa")
        btn_kbd_anim = QPushButton("Aplicar Animação")
        btn_kbd_anim.clicked.connect(self.apply_kbd_anim)
        kbd_anim_layout.addWidget(self.cb_kbd_anim)
        kbd_anim_layout.addWidget(self.chk_kbd_fixed)
        kbd_anim_layout.addWidget(btn_kbd_anim)
        kbd_vbox.addLayout(kbd_anim_layout)

        # Velocidade da animação do teclado
        kbd_speed_layout = QHBoxLayout()
        kbd_speed_layout.addWidget(QLabel("⏱ Velocidade:"))
        self.sl_kbd_speed = QSlider(Qt.Orientation.Horizontal)
        self.sl_kbd_speed.setMinimum(1)
        self.sl_kbd_speed.setMaximum(10)
        self.sl_kbd_speed.setValue(3)
        self.sl_kbd_speed.setTickInterval(1)
        self.sl_kbd_speed.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sl_kbd_speed.setStyleSheet("""
            QSlider::groove:horizontal { height:6px; background:#2c2c2c; border-radius:3px; }
            QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6600cc, stop:1 #cc00ff); border-radius:3px; }
            QSlider::handle:horizontal { background:#cc00ff; border:2px solid #fff; width:16px; height:16px; margin:-5px 0; border-radius:8px; }
        """)
        self.sp_kbd_speed = QSpinBox()
        self.sp_kbd_speed.setMinimum(1)
        self.sp_kbd_speed.setMaximum(10)
        self.sp_kbd_speed.setValue(3)
        self.sp_kbd_speed.setFixedWidth(50)
        self.sp_kbd_speed.setStyleSheet("background-color:#1e1e1e; color:#e0e0e0; border:1px solid #444; border-radius:4px; padding:2px;")
        self.sl_kbd_speed.valueChanged.connect(self.sp_kbd_speed.setValue)
        self.sp_kbd_speed.valueChanged.connect(self.sl_kbd_speed.setValue)
        kbd_speed_layout.addWidget(self.sl_kbd_speed)
        kbd_speed_layout.addWidget(self.sp_kbd_speed)
        kbd_vbox.addLayout(kbd_speed_layout)

        btn_kbd_color = QPushButton("🎨 Escolher Cor (Teclado)")
        btn_kbd_color.clicked.connect(self.choose_keyboard_color)
        kbd_vbox.addWidget(btn_kbd_color)

        btn_kbd_off = QPushButton("Desligar Teclado")
        btn_kbd_off.setObjectName("danger")
        btn_kbd_off.clicked.connect(self.apply_kbd_off)
        kbd_vbox.addWidget(btn_kbd_off)
        
        self.tab_leds_layout.addWidget(kbd_frame)

        # --- PAINEL DA LIGHTBAR ---
        lb_frame = QFrame()
        lb_vbox = QVBoxLayout(lb_frame)
        lb_vbox.addWidget(QLabel("🏮 LIGHTBAR INFERIOR"))

        lb_anim_layout = QHBoxLayout()
        self.cb_lb_anim = QComboBox()
        self.cb_lb_anim.addItems([
            "rainbow",    # 🌈 Arco-íris
            "breathing",  # 💨 Respiração suave
            "strobe",     # ⚡ Strobe / Flash
            "pulse",      # 💓 Pulso / Coração
            "fire",       # 🔥 Chamas
            "wave",       # 🌊 Onda bicolor
            "aurora",     # 🌌 Aurora Boreal
        ])
        self.chk_lb_fixed = QCheckBox("Cor fixa")
        btn_lb_anim = QPushButton("Aplicar Animação")
        btn_lb_anim.clicked.connect(self.apply_lb_anim)
        lb_anim_layout.addWidget(self.cb_lb_anim)
        lb_anim_layout.addWidget(self.chk_lb_fixed)
        lb_anim_layout.addWidget(btn_lb_anim)
        lb_vbox.addLayout(lb_anim_layout)

        # Preview de cor + botão escolher cor
        lb_color_layout = QHBoxLayout()
        self.lb_color_preview = QFrame()
        self.lb_color_preview.setFixedSize(32, 32)
        self.lb_color_preview.setStyleSheet(
            "background-color: rgb(0, 150, 255); border-radius: 6px; border: 1px solid #444;"
        )
        btn_lb_color = QPushButton("🎨 Escolher Cor (Lightbar)")
        btn_lb_color.clicked.connect(self.choose_lightbar_color)
        lb_color_layout.addWidget(self.lb_color_preview)
        lb_color_layout.addWidget(btn_lb_color)
        lb_vbox.addLayout(lb_color_layout)

        # Slider de Intensidade
        lb_brightness_label = QLabel("💡 Intensidade:")
        lb_vbox.addWidget(lb_brightness_label)

        lb_brightness_layout = QHBoxLayout()
        self.lb_brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.lb_brightness_slider.setMinimum(0)
        self.lb_brightness_slider.setMaximum(100)
        self.lb_brightness_slider.setValue(100)
        self.lb_brightness_slider.setTickInterval(10)
        self.lb_brightness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lb_brightness_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #2c2c2c;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #003399, stop:1 #00aaff);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00aaff;
                border: 2px solid #ffffff;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
        """)

        self.lb_brightness_spin = QSpinBox()
        self.lb_brightness_spin.setMinimum(0)
        self.lb_brightness_spin.setMaximum(100)
        self.lb_brightness_spin.setValue(100)
        self.lb_brightness_spin.setSuffix("%")
        self.lb_brightness_spin.setFixedWidth(68)
        self.lb_brightness_spin.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; border-radius: 4px; padding: 2px;")

        # Sincronizar slider <-> spinbox
        self.lb_brightness_slider.valueChanged.connect(self.lb_brightness_spin.setValue)
        self.lb_brightness_spin.valueChanged.connect(self.lb_brightness_slider.setValue)
        self.lb_brightness_slider.valueChanged.connect(self.on_lb_brightness_changed)

        lb_brightness_layout.addWidget(self.lb_brightness_slider)
        lb_brightness_layout.addWidget(self.lb_brightness_spin)
        lb_vbox.addLayout(lb_brightness_layout)

        btn_lb_off = QPushButton("Desligar Lightbar")
        btn_lb_off.setObjectName("danger")
        btn_lb_off.clicked.connect(self.apply_lb_off)
        lb_vbox.addWidget(btn_lb_off)

        self.tab_leds_layout.addWidget(lb_frame)
        self.tab_leds_layout.addStretch()
        self.tabs.addTab(self.tab_leds, "Controle de LEDs")

        # --- ABA 2: MONITOR DO SISTEMA ---
        self.tab_monitor = QWidget()
        self.tab_monitor_layout = QVBoxLayout(self.tab_monitor)
        self.setup_monitor_tab()
        self.tabs.addTab(self.tab_monitor, "Monitoramento")

        self.setLayout(layout)
        self.setWindowTitle('Avell Control Center')
        self.resize(430, 480)

    def setup_monitor_tab(self):
        # Rede
        self.net_label = QLabel("Rede (Down / Up): Calculando...")
        self.net_chart = NetMirroredChart()
        self.tab_monitor_layout.addWidget(self.net_label)
        self.tab_monitor_layout.addWidget(self.net_chart)

        # CPU
        self.cpu_label = QLabel("Uso de CPU: Calculando...")
        self.cpu_chart = CpuAreaChart()
        self.tab_monitor_layout.addWidget(self.cpu_label)
        self.tab_monitor_layout.addWidget(self.cpu_chart)
        
        # RAM
        self.ram_label = QLabel("Uso de RAM: Calculando...")
        self.ram_chart = RamStackedBar()
        self.tab_monitor_layout.addWidget(self.ram_label)
        self.tab_monitor_layout.addWidget(self.ram_chart)
        
        # Disco
        disk_layout = QHBoxLayout()
        self.disk_label = QLabel("Uso de Disco (/): Calculando...")
        self.disk_chart = DiskDonutChart()
        disk_layout.addWidget(self.disk_label)
        disk_layout.addWidget(self.disk_chart)
        self.tab_monitor_layout.addLayout(disk_layout)
        
        self.tab_monitor_layout.addStretch()

        self.last_cpu_idle = 0
        self.last_cpu_total = 0
        self.last_net_rx = 0
        self.last_net_tx = 0

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_monitor_stats)
        self.monitor_timer.start(1000) # Fast update
        self.update_monitor_stats()
        
    def update_monitor_stats(self):
        # Network
        try:
            rx = 0
            tx = 0
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
                for line in lines[2:]:
                    parts = line.split(':')
                    if len(parts) == 2:
                        iface = parts[0].strip()
                        if iface != 'lo':
                            data = parts[1].split()
                            rx += int(data[0])
                            tx += int(data[8])
            
            if self.last_net_rx > 0:
                dl_rate = rx - self.last_net_rx
                ul_rate = tx - self.last_net_tx
                self.net_chart.update_values(dl_rate, ul_rate)
                
                def format_speed(bps):
                    if bps < 1024: return f"{bps} B/s"
                    elif bps < 1024**2: return f"{bps/1024:.1f} KB/s"
                    else: return f"{bps/1024**2:.1f} MB/s"
                    
                self.net_label.setText(f"Rede ↓ {format_speed(dl_rate)}  |  ↑ {format_speed(ul_rate)}")
                
            self.last_net_rx = rx
            self.last_net_tx = tx
        except Exception: pass

        # CPU
        try:
            with open('/proc/stat', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('cpu '):
                        parts = [int(x) for x in line.split()[1:]]
                        idle = parts[3] + parts[4]
                        total = sum(parts)
                        idle_delta = idle - self.last_cpu_idle
                        total_delta = total - self.last_cpu_total
                        if total_delta > 0:
                            usage = 100.0 * (1.0 - idle_delta / total_delta)
                            self.cpu_chart.update_value(usage)
                            self.cpu_label.setText(f"Uso de CPU: {usage:.1f}%")
                        self.last_cpu_idle = idle
                        self.last_cpu_total = total
                        break
        except Exception: pass

        # RAM
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f.readlines():
                    parts = line.split(':')
                    if len(parts) == 2:
                        meminfo[parts[0].strip()] = int(parts[1].split()[0])
            total_ram = meminfo.get('MemTotal', 1)
            avail_ram = meminfo.get('MemAvailable', 0)
            used_ram = total_ram - avail_ram
            ram_pct = (used_ram / total_ram) * 100
            self.ram_chart.update_value(ram_pct)
            self.ram_label.setText(f"Uso de RAM: {ram_pct:.1f}% ({used_ram/1024/1024:.1f} GB / {total_ram/1024/1024:.1f} GB)")
        except Exception: pass
            
        # Disk
        try:
            st = os.statvfs('/')
            total_disk = st.f_blocks * st.f_frsize
            free_disk = st.f_bavail * st.f_frsize
            used_disk = total_disk - free_disk
            if total_disk > 0:
                disk_pct = (used_disk / total_disk) * 100
                self.disk_chart.update_value(disk_pct, f"{disk_pct:.1f}%")
                self.disk_label.setText(f"Uso de Disco (/):\n{used_disk/1024**3:.1f} GB / {total_disk/1024**3:.1f} GB")
        except Exception: pass

    def restore_ui_state(self):
        """Restaura o valor do slider e preview de cor com base no JSON salvo."""
        config_path = os.path.expanduser("~/.config/avell-gui-settings.json")
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, "r") as f:
                state = json.load(f)
            # Restaura intensidade (salva em 0-100)
            brightness = min(100, state.get("lb_brightness", 100))
            self.lb_brightness_slider.blockSignals(True)
            self.lb_brightness_slider.setValue(brightness)
            self.lb_brightness_spin.setValue(brightness)
            self.lb_brightness_slider.blockSignals(False)
            # Restaura preview de cor
            lb_color = state.get("lb_color")
            if lb_color and len(lb_color) == 3:
                r, g, b = lb_color
                self.hw.last_lb_color = (r, g, b)
                self.lb_color_preview.setStyleSheet(
                    f"background-color: rgb({r},{g},{b}); border-radius: 6px; border: 1px solid #444;"
                )
        except Exception as e:
            print(f"Aviso: não foi possível restaurar UI state: {e}")

    def save_current_state(self, updates):
        config_dir = os.path.expanduser("~/.config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "avell-gui-settings.json")
        state = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    state = json.load(f)
            except: pass
        state.update(updates)
        try:
            with open(config_path, "w") as f:
                json.dump(state, f)
        except: pass

    def apply_kbd_anim(self):
        label = self.cb_kbd_anim.currentText()
        anim = self._kbd_anim_map.get(label, label)  # fallback para o próprio texto
        fixed = self.chk_kbd_fixed.isChecked()
        speed = self.sl_kbd_speed.value()
        # Monta o nome do estilo com sufixo de cor se "cor fixa" estiver marcada
        style = anim
        if fixed and self.hw.last_kbd_color_suffix:
            style = anim + self.hw.last_kbd_color_suffix
        self.hw.run_command(['sudo', 'aucc', '-s', style, '--speed', str(speed)])
        self.save_current_state({"kbd_mode": "anim", "kbd_anim": anim, "kbd_fixed": fixed,
                                  "kbd_suffix": self.hw.last_kbd_color_suffix, "kbd_speed": speed})

    def apply_kbd_off(self):
        self.hw.set_keyboard("off")
        self.save_current_state({"kbd_mode": "off", "kbd_rgb": None})

    def choose_keyboard_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.hw.set_keyboard_rgb(color.red(), color.green(), color.blue())
            self.save_current_state({"kbd_mode": None, "kbd_rgb": [color.red(), color.green(), color.blue()]})

    def apply_lb_anim(self):
        anim = self.cb_lb_anim.currentText()
        fixed = self.chk_lb_fixed.isChecked()
        self.hw.set_lightbar_anim(anim, use_fixed=fixed)
        self.save_current_state({"lb_mode": "anim", "lb_anim": anim, "lb_fixed": fixed, "lb_color": self.hw.last_lb_color})

    def apply_lb_off(self):
        self.lb_brightness_slider.blockSignals(True)
        self.lb_brightness_slider.setValue(0)
        self.lb_brightness_spin.setValue(0)
        self.lb_brightness_slider.blockSignals(False)
        self.hw.set_lightbar(0, 0, 0, brightness=0)
        self.save_current_state({"lb_mode": "off", "lb_brightness": 0})

    def on_lb_brightness_changed(self, value):
        """Chamado ao mover o slider — aplica a intensidade na cor atual em tempo real.
        O slider vai de 0-100 (%) e é mapeado para 0-255 para o hardware."""
        r, g, b = self.hw.last_lb_color
        hw_brightness = round(value * 255 / 100)
        self.hw.set_lightbar(r, g, b, brightness=hw_brightness)
        self.save_current_state({"lb_mode": "static", "lb_color": [r, g, b], "lb_brightness": value})

    def choose_lightbar_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            pct = self.lb_brightness_slider.value()  # 0-100
            hw_brightness = round(pct * 255 / 100)
            self.lb_color_preview.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border-radius: 6px; border: 1px solid #444;"
            )
            self.hw.set_lightbar(r, g, b, brightness=hw_brightness)
            self.save_current_state({"lb_mode": "static", "lb_color": [r, g, b], "lb_brightness": pct})

    def setupTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("preferences-desktop-keyboard"))
        
        tray_menu = QMenu()
        
        show_action = QAction("Mostrar", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--boot', action='store_true', help='Rodar sem interface gráfica para aplicar configurações')
    parser.add_argument('--config', type=str, default="", help='Caminho do arquivo de configuração JSON')
    args, unknown = parser.parse_known_args()

    if args.boot:
        if args.config and os.path.exists(args.config):
            try:
                with open(args.config, "r") as f:
                    state = json.load(f)
                hw = AvellHardwareManager()
                
                # Aplica teclado
                if state.get("kbd_mode"):
                    hw.last_kbd_color_suffix = state.get("kbd_suffix", "")
                    hw.set_keyboard(mode=state["kbd_mode"], anim_style=state.get("kbd_anim"), use_fixed=state.get("kbd_fixed", False))
                elif state.get("kbd_rgb"):
                    hw.set_keyboard_rgb(*state["kbd_rgb"])
                    
                # Aplica lightbar
                if state.get("lb_mode") == "anim":
                    hw.last_lb_color = state.get("lb_color", (0,150,255))
                    hw.set_lightbar_anim(state.get("lb_anim"), use_fixed=state.get("lb_fixed", False))
                elif state.get("lb_mode") == "static":
                    hw.set_lightbar(*state.get("lb_color", (0,150,255)), brightness=state.get("lb_brightness", 255))
                elif state.get("lb_mode") == "off":
                    hw.set_lightbar(0,0,0,0)
            except Exception as e:
                print(f"Erro ao aplicar boot config: {e}")
        sys.exit(0)

    app = QApplication(sys.argv)
    ex = AvellLEDMaster()
    ex.show()
    sys.exit(app.exec())
