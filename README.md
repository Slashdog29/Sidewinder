# Sidewinder APK Manager 🐍📦

Sidewinder es una herramienta gráfica de automatización construida en **Python 3** y **PyQt6**. Su objetivo principal es facilitar la gestión, inyección y desinstalación aislada y *headless* de paquetes Android (`.apk`) sobre el entorno **Waydroid** en sistemas Linux.

La aplicación resuelve los congelamientos de interfaz mediante el uso de subprocesos avanzados (`QThread`) y cuenta con elevación de privilegios integrada a través de `pkexec` para gestionar aplicaciones sin romper las políticas de seguridad de la shell de Android.

---

## 🐧 Sistemas Operativos Compatibles

Sidewinder está diseñado exclusivamente para el ecosistema **GNU/Linux**. 

* **Distribución Base:** Es universal para cualquier distribución Linux que soporte Waydroid (Ubuntu, Fedora, Debian, etc.), pero está **altamente optimizado y testeado en Arch Linux**.
* **Servidor Gráfico Obligatorio:** Requiere un entorno basado en **Wayland** (o compositores como Hyprland, Sway, GNOME/KDE en modo Wayland) para que Waydroid pueda renderizar las aplicaciones nativamente.

---

## ✨ Características Principales

* **Sincronización Inteligente:** Comprueba el estado del contenedor y de la sesión al arrancar. Si están apagados, los despierta automáticamente.
* **Instalación Sideload Headless:** Busca e inyecta cualquier archivo `.apk` local hacia el contenedor Android con un solo clic.
* **Gestor de Aplicaciones Integrado:** Escanea los archivos `.desktop` de Waydroid para listar, refrescar y ordenar tus apps instaladas.
* **Desinstalación con un Clic:** Olvídate del error `Action "shell" needs root access`. Sidewinder eleva privilegios de forma gráfica y segura con Polkit (`pkexec`).
* **Auto-Instalación Dinámica:** Al ejecutarse por primera vez, el script detecta su ubicación actual y genera automáticamente su propio lanzador `.desktop` en `~/.local/share/applications` para que aparezca de inmediato en tu menú de aplicaciones (Rofi, Wofi o launchers tradicionales).

---

## 📂 Estructura del Repositorio

| Archivo / Directorio | Descripción |
| :--- | :--- |
| `Sidewinder.py` | Script principal en Python. Contiene la interfaz gráfica en PyQt6 y la lógica de los hilos de ejecución. |
| `install_waydroid_smart.sh` | Script de terminal automatizado para la instalación y puesta a punto inicial del entorno Waydroid. |
| `assets/` | Carpeta destinada a recursos del proyecto, capturas de pantalla o el icono oficial de la aplicación. |

---

## 🛠️ Requisitos previos

Asegúrate de contar con las siguientes herramientas instaladas en tu sistema (ejemplo de instalación en Arch Linux):

```bash
sudo pacman -S git python python-pyqt6 waydroid polkit
```

##**🚀 Instalación y Uso Rápido**

**1. Clonar el repositorio**
Abre tu terminal y descarga el proyecto directamente con este comando:
```Bash
git clone [https://github.com/Slashdog29/Sidewinder.git](https://github.com/Slashdog29/Sidewinder.git) && cd Sidewinder
```

**2. Configurar Waydroid (Opcional)**
Si aún no has inicializado el entorno Android en tu sistema, ejecuta el asistente inteligente incluido:
```Bash
chmod +x install_waydroid_smart.sh
./install_waydroid_smart.sh
```

**3. Lanzar y Auto-Instalar**
Dale permisos de ejecución al script principal de Python y arráncalo:
```Bash
chmod +x Sidewinder.py
./Sidewinder.py
````
**Nota: En esta primera ejecución, Sidewinder se registrará solo en tu sistema. A partir de ahora podrás abrirlo directamente desde tu lanzador de aplicaciones de Linux buscando "Sidewinder".**
