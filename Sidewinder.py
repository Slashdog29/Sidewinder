#!/usr/bin/env python3
import sys
import os
import subprocess
import time
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QProgressBar, 
                             QMessageBox, QTabWidget, QListWidget, QListWidgetItem)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

# HILO 1: Encargado exclusivamente de despertar y comprobar Waydroid al arrancar
class WaydroidInitWorker(QThread):
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            self.status_signal.emit("Comprobando servicio base de Waydroid...")
            self.progress_signal.emit(15)
            
            status_check = subprocess.run(["waydroid", "status"], capture_output=True, text=True)
            status_clean = "".join(status_check.stdout.lower().split())
            
            if "container:running" not in status_clean:
                self.status_signal.emit("Activando servicio (Pon tu contraseña)...")
                run_container = subprocess.run(["pkexec", "systemctl", "start", "waydroid-container"], capture_output=True)
                if run_container.returncode != 0:
                    self.finished_signal.emit(False, "No se pudo iniciar el servicio base (Permiso denegado).")
                    return
                time.sleep(2)

            status_check = subprocess.run(["waydroid", "status"], capture_output=True, text=True)
            status_clean = "".join(status_check.stdout.lower().split())

            if "session:running" not in status_clean:
                self.status_signal.emit("Levantando entorno Android en segundo plano...")
                self.progress_signal.emit(45)
                
                env_actual = os.environ.copy()
                subprocess.Popen(
                    ["waydroid", "session", "start"], 
                    env=env_actual,
                    start_new_session=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                
                session_ready = False
                for i in range(25):
                    time.sleep(1)
                    check = subprocess.run(["waydroid", "status"], capture_output=True, text=True)
                    check_clean = "".join(check.stdout.lower().split())
                    
                    if "session:running" in check_clean:
                        session_ready = True
                        break
                    self.status_signal.emit(f"Sincronizando con Android... ({i+1}s)")
                    self.progress_signal.emit(45 + i * 2)
                
                if not session_ready:
                    self.finished_signal.emit(False, "El entorno de Android tardó demasiado en responder.")
                    return

            self.progress_bar.setValue(100) if hasattr(self, 'progress_bar') else None
            self.finished_signal.emit(True, "Waydroid se encuentra activo y listo.")

        except Exception as e:
            self.finished_signal.emit(False, f"Error crítico al inicializar: {str(e)}")


# HILO 2: Encargado únicamente de inyectar la APK de forma segura
class WaydroidInstallWorker(QThread):
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, apk_path):
        super().__init__()
        self.apk_path = apk_path

    def run(self):
        try:
            self.status_signal.emit(f"Instalando: {os.path.basename(self.apk_path)}...")
            self.progress_signal.emit(50)
            
            result = subprocess.run(["waydroid", "app", "install", self.apk_path], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, f"¡Instalación exitosa!\n\n{os.path.basename(self.apk_path)} ya está disponible.")
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                self.finished_signal.emit(False, f"Waydroid rechazó la APK:\n{error_msg}")
        except Exception as e:
            self.finished_signal.emit(False, f"Error en la instalación: {str(e)}")


# HILO 3: Encargado de desinstalar aplicaciones usando elevación de privilegios gráficos (pkexec)
class WaydroidUninstallWorker(QThread):
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, package_name, app_name):
        super().__init__()
        self.package_name = package_name
        self.app_name = app_name

    def run(self):
        try:
            self.status_signal.emit(f"Removiendo {self.app_name} (Pon tu contraseña)...")
            
            # Agregamos pkexec para otorgar el acceso root requerido por la acción shell del contenedor
            result = subprocess.run(["pkexec", "waydroid", "shell", "pm", "uninstall", self.package_name], capture_output=True, text=True)
            
            if result.returncode == 0 or "success" in result.stdout.lower():
                self.finished_signal.emit(True, f"¡{self.app_name} ha sido desinstalada con éxito!")
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                self.finished_signal.emit(False, f"No se pudo desinstalar:\n{error_msg}")
        except Exception as e:
            self.finished_signal.emit(False, f"Error crítico al desinstalar: {str(e)}")


class SidewinderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.check_waydroid_status()

    def init_ui(self):
        self.setWindowTitle("Sidewinder APK Manager")
        self.setFixedSize(540, 400)
        
        self.setStyleSheet("""
            QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', Arial, sans-serif; }
            QTabWidget::pane { border: 1px solid #45475a; background: #1e1e2e; border-radius: 6px; top: -1px; }
            QTabBar::tab { background: #11111b; color: #a6adc8; padding: 10px 20px; border: 1px solid #45475a; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; }
            QTabBar::tab:selected { background: #313244; color: #cba6f7; border-color: #45475a; }
            QTabBar::tab:disabled { color: #45475a; background: #11111b; border-color: #1e1e2e; }
            QPushButton { background-color: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 10px; font-weight: bold; }
            QPushButton:hover { background-color: #45475a; border: 1px solid #cba6f7; }
            QPushButton:disabled { background-color: #181825; color: #585b70; border: 1px solid #313244; }
            QListWidget { background-color: #11111b; border: 1px solid #45475a; border-radius: 6px; padding: 5px; }
            QListWidget::item { padding: 10px; border-radius: 4px; color: #cdd6f4; }
            QListWidget::item:hover { background-color: #313244; }
            QListWidget::item:selected { background-color: #45475a; color: #cba6f7; font-weight: bold; }
            QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; background-color: #11111b; }
            QProgressBar::chunk { background-color: #cba6f7; border-radius: 3px; }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.global_status_label = QLabel("Inicializando software...")
        self.global_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.global_status_label.setStyleSheet("color: #f9e2af; font-style: italic; font-weight: bold;")
        main_layout.addWidget(self.global_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.tabs = QTabWidget()
        
        # TAB 1: INSTALADOR
        self.tab_install = QWidget()
        self.init_tab_install()
        self.tabs.addTab(self.tab_install, "Instalar APK")

        # TAB 2: GESTOR
        self.tab_manage = QWidget()
        self.init_tab_manage()
        self.tabs.addTab(self.tab_manage, "Mis Aplicaciones")
        self.tabs.setTabEnabled(1, False)

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.selected_apk = None

    def init_tab_install(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel("Sidewinder Sideload")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #cba6f7;")
        layout.addWidget(self.title_label)

        self.file_label = QLabel("Por favor, espera a que Waydroid se sincronice...")
        self.file_label.setWordWrap(True)
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setStyleSheet("color: #a6adc8; font-style: italic;")
        layout.addWidget(self.file_label)

        btn_layout = QHBoxLayout()
        self.btn_browse = QPushButton("Buscar APK")
        self.btn_browse.setEnabled(False)
        self.btn_browse.clicked.connect(self.browse_apk)
        
        self.btn_install = QPushButton("Instalar")
        self.btn_install.setEnabled(False)
        self.btn_install.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold;")
        self.btn_install.clicked.connect(self.start_installation)
        
        btn_layout.addWidget(self.btn_browse)
        btn_layout.addWidget(self.btn_install)
        layout.addLayout(btn_layout)
        self.tab_install.setLayout(layout)

    def init_tab_manage(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        layout.addWidget(QLabel("Selecciona una aplicación para eliminarla:"))

        self.app_list_widget = QListWidget()
        layout.addWidget(self.app_list_widget)

        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refrescar Lista")
        self.btn_refresh.clicked.connect(self.load_installed_apps)
        
        self.btn_uninstall = QPushButton("Desinstalar Selección")
        self.btn_uninstall.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold;")
        self.btn_uninstall.clicked.connect(self.start_uninstallation)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_uninstall)
        layout.addLayout(btn_layout)
        self.tab_manage.setLayout(layout)

    def check_waydroid_status(self):
        self.tabs.setTabEnabled(1, False)
        self.btn_browse.setEnabled(False)
        self.btn_install.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        self.init_worker = WaydroidInitWorker()
        self.init_worker.status_signal.connect(self.update_global_status)
        self.init_worker.progress_signal.connect(self.progress_bar.setValue)
        self.init_worker.finished_signal.connect(self.init_done)
        self.init_worker.start()

    def update_global_status(self, text):
        self.global_status_label.setText(text)

    def init_done(self, success, message):
        self.progress_bar.hide()
        if success:
            self.global_status_label.setText("Sistema Operativo Android: CONECTADO Y SEGURO")
            self.global_status_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.file_label.setText("Selecciona un archivo .apk local para comenzar")
            self.file_label.setStyleSheet("color: #cdd6f4; font-style: normal;")
            self.btn_browse.setEnabled(True)
            self.tabs.setTabEnabled(1, True)
            self.load_installed_apps()
        else:
            self.global_status_label.setText(f"Error: {message}")
            self.global_status_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
            self.btn_browse.setText("Reintentar Conexión")
            self.btn_browse.setEnabled(True)
            try: self.btn_browse.clicked.disconnect()
            except: pass
            self.btn_browse.clicked.connect(self.reset_to_retry)

    def reset_to_retry(self):
        self.btn_browse.setText("Buscar APK")
        self.btn_browse.clicked.disconnect()
        self.btn_browse.clicked.connect(self.browse_apk)
        self.check_waydroid_status()

    def browse_apk(self):
        file_filter = "Android Package (*.apk)"
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir archivo APK", os.path.expanduser("~"), file_filter)
        if filename:
            self.selected_apk = filename
            self.file_label.setText(f"Listo para inyectar:\n{os.path.basename(filename)}")
            self.file_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
            self.btn_install.setEnabled(True)

    def start_installation(self):
        if not self.selected_apk:
            return
        self.btn_browse.setEnabled(False)
        self.btn_install.setEnabled(False)
        self.tabs.setTabEnabled(1, False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.install_worker = WaydroidInstallWorker(self.selected_apk)
        self.install_worker.status_signal.connect(self.update_global_status)
        self.install_worker.progress_signal.connect(self.progress_bar.setValue)
        self.install_worker.finished_signal.connect(self.installation_done)
        self.install_worker.start()

    def installation_done(self, success, message):
        self.progress_bar.hide()
        self.btn_browse.setEnabled(True)
        self.tabs.setTabEnabled(1, True)
        self.global_status_label.setText("Sistema Operativo Android: CONECTADO Y SEGURO")
        
        if success:
            QMessageBox.information(self, "Proceso Completado", message)
            self.file_label.setText("Selecciona un archivo .apk local para comenzar")
            self.file_label.setStyleSheet("color: #cdd6f4;")
            self.btn_install.setEnabled(False)
            self.selected_apk = None
            self.load_installed_apps()
        else:
            QMessageBox.critical(self, "Fallo de Operación", message)

    def load_installed_apps(self):
        self.app_list_widget.clear()
        app_dir = os.path.expanduser("~/.local/share/applications")
        
        if not os.path.exists(app_dir):
            return

        apps = []
        for filename in os.listdir(app_dir):
            if filename.startswith("waydroid.") and filename.endswith(".desktop"):
                package_name = filename[9:-8]
                display_name = package_name
                
                try:
                    with open(os.path.join(app_dir, filename), "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("Name="):
                                display_name = line.split("=", 1)[1].strip()
                                break
                except:
                    pass
                
                apps.append({"name": display_name, "package": package_name})

        apps.sort(key=lambda x: x["name"].lower())

        for app_info in apps:
            item = QListWidgetItem(f"{app_info['name']}   ({app_info['package']})")
            item.setData(Qt.ItemDataRole.UserRole, app_info['package'])
            item.setData(Qt.ItemDataRole.DisplayRole, app_info['name'])
            self.app_list_widget.addItem(item)

    def start_uninstallation(self):
        selected_item = self.app_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Atención", "Por favor, selecciona una aplicación de la lista.")
            return

        package_name = selected_item.data(Qt.ItemDataRole.UserRole)
        app_name = selected_item.data(Qt.ItemDataRole.DisplayRole)

        confirm = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Estás seguro de que deseas desinstalar por completo {app_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.btn_refresh.setEnabled(False)
            self.btn_uninstall.setEnabled(False)
            self.btn_browse.setEnabled(False)
            self.tabs.setTabEnabled(0, False)
            self.progress_bar.setValue(50)
            self.progress_bar.show()

            self.uninstall_worker = WaydroidUninstallWorker(package_name, app_name)
            self.uninstall_worker.status_signal.connect(self.update_global_status)
            self.uninstall_worker.finished_signal.connect(self.uninstallation_done)
            self.uninstall_worker.start()

    def uninstallation_done(self, success, message):
        self.progress_bar.hide()
        self.btn_refresh.setEnabled(True)
        self.btn_uninstall.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.tabs.setTabEnabled(0, True)
        self.global_status_label.setText("Sistema Operativo Android: CONECTADO Y SEGURO")

        if success:
            QMessageBox.information(self, "Eliminación Exitosa", message)
            self.load_installed_apps()
        else:
            QMessageBox.critical(self, "Error de Desinstalación", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SidewinderApp()
    window.show()
    sys.exit(app.exec())