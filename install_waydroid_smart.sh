#!/usr/bin/env bash

# Salir de inmediato si ocurre un error
set -e

# Paleta de colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CLEAR='\033[0m'

# ======================================================
# DETECCIÓN DE DISTRIBUCIÓN Y GESTOR DE PAQUETES
# ======================================================
detect_environment() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_NAME="${NAME:-Linux}"
        DISTRO_ID="$ID"
        DISTRO_FAMILY="${ID_LIKE:-$ID}"
    else
        echo -e "${RED}[!] ERROR: No se pudo detectar el sistema (/etc/os-release no existe).${CLEAR}"
        exit 1
    fi

    case "$DISTRO_ID" in
        arch|cachyos|manjaro|endeavouros|garuda)
            PKG_MANAGER="pacman"
            ;;
        ubuntu|debian|pop|mint|elementary)
            PKG_MANAGER="apt"
            ;;
        fedora|nobara|rhel|centos|rocky)
            PKG_MANAGER="dnf"
            ;;
        opensuse*|suse)
            PKG_MANAGER="zypper"
            ;;
        *)
            case "$DISTRO_FAMILY" in
                *arch*) PKG_MANAGER="pacman" ;;
                *debian*|*ubuntu*) PKG_MANAGER="apt" ;;
                *fedora*|*rhel*) PKG_MANAGER="dnf" ;;
                *suse*) PKG_MANAGER="zypper" ;;
                *)
                    echo -e "${RED}[!] ERROR: Distribución no soportada: $DISTRO_NAME${CLEAR}"
                    exit 1
                    ;;
            esac
            ;;
    esac
}

install_dependencies() {
    echo -e "\n${YELLOW}[1/7] Instalando paquetes y dependencias esenciales (${PKG_MANAGER})...${CLEAR}"
    
    case "$PKG_MANAGER" in
        pacman)
            sudo pacman -S --needed --noconfirm waydroid lzip python git dnsmasq iptables
            ;;
        apt)
            # 1. Asegurar herramientas base necesarias
            sudo apt update -y
            sudo apt install -y curl ca-certificates lzip python3 python3-venv python3-pip git dnsmasq iptables

            # 2. Si waydroid no está en los repositorios locales, agregar el repo oficial de Waydroid
            if ! apt-cache show waydroid >/dev/null 2>&1; then
                echo -e "${YELLOW}[!] Repositorio de Waydroid no detectado. Configurándolo automáticamente...${CLEAR}"
                curl -s https://repo.waydro.id | sudo bash
                sudo apt update -y
            fi

            # 3. Instalar Waydroid
            sudo apt install -y waydroid
            ;;
        dnf)
            sudo dnf install -y waydroid lzip python3 git dnsmasq iptables
            ;;
        zypper)
            sudo zypper install -y waydroid lzip python3 git dnsmasq iptables
            ;;
    esac
}
# Ejecutar detección inicial
detect_environment

echo -e "${BLUE}======================================================${CLEAR}"
echo -e "${BLUE}   Waydroid Installer Universal - $DISTRO_NAME   ${CLEAR}"
echo -e "${BLUE}======================================================${CLEAR}"
echo -e "${GREEN}[✓] Sistema detectado: $DISTRO_NAME ($PKG_MANAGER)${CLEAR}"

# 1. Instalación de dependencias del sistema según la distro
install_dependencies

# 2. Configuración de Red automatizada (IP Forwarding)
echo -e "\n${YELLOW}[2/7] Habilitando el reenvío de IP (IP Forwarding)...${CLEAR}"
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/30-waydroid.conf > /dev/null
sudo sysctl --system

# Ajustar reglas si usas UFW (Firewall)
if systemctl is-active --quiet ufw; then
    echo -e "${YELLOW}[!] UFW activo detectado. Creando excepciones para 'waydroid0'...${CLEAR}"
    sudo ufw route allow in on waydroid0
    sudo ufw allow in on waydroid0
    sudo ufw reload
fi

# 3. Activación del servicio del contenedor
echo -e "\n${YELLOW}[3/7] Activando el servicio base de Waydroid...${CLEAR}"
sudo systemctl enable --now waydroid-container

# 4. Inicialización de la imagen limpia (Vanilla)
echo -e "\n${YELLOW}[4/7] Descargando e inicializando imagen Vanilla (Sin GApps)...${CLEAR}"
if [ -d "/var/lib/waydroid/cells" ] && [ "$(ls -A /var/lib/waydroid/cells)" ]; then
    echo -e "${GREEN}-> El sistema ya cuenta con una imagen base. Saltando descarga...${CLEAR}"
else
    sudo waydroid init -f
fi

# Forzar reinicio para levantar la interfaz de red waydroid0 correctamente
sudo systemctl restart waydroid-container
sleep 3

# 5. Sincronización automática de Fecha, Hora y Zona Horaria
echo -e "\n${YELLOW}[5/7] Sincronizando la hora y zona horaria de la PC con Android...${CLEAR}"
HOST_TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || true)
if [ -z "$HOST_TZ" ]; then
    HOST_TZ=$(readlink /etc/localtime | sed 's#.*/zoneinfo/##')
fi
echo -e "${BLUE}-> Zona horaria detectada: $HOST_TZ${CLEAR}"
sudo waydroid prop set persist.sys.timezone "$HOST_TZ"

# 6. Descarga e inyección del Traductor ARM (Libhoudini)
echo -e "\n${YELLOW}[6/7] Instalando traductor Libhoudini para compatibilidad ARM...${CLEAR}"
TMP_DIR="/tmp/waydroid_setup"
rm -rf "$TMP_DIR" && mkdir -p "$TMP_DIR" && cd "$TMP_DIR"

git clone https://github.com/casualsnek/waydroid_script.git
cd waydroid_script

sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt
sudo ./venv/bin/python3 main.py install libhoudini

# 7. ENMASCARAMIENTO INTELIGENTE DE LANZADORES DE GESTIÓN
echo -e "\n${YELLOW}[7/7] Ocultando herramientas de gestión (Tus APKs sí se verán)...${CLEAR}"

mkdir -p ~/.local/share/applications

for file in /usr/share/applications/*waydroid*.desktop /usr/share/applications/*Waydroid*.desktop; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        cp "$file" ~/.local/share/applications/
        sed -i '/NoDisplay=/d' ~/.local/share/applications/"$filename"
        echo "NoDisplay=true" >> ~/.local/share/applications/"$filename"
        echo -e "${GREEN}-> Ocultado con éxito:${CLEAR} $filename"
    fi
done

# Reinicio maestro definitivo
echo -e "\n${YELLOW}[*] Aplicando configuraciones finales...${CLEAR}"
sudo systemctl restart waydroid-container

echo -e "\n${GREEN}======================================================${CLEAR}"
echo -e "${GREEN}   ¡Proyecto Listo! Waydroid configurado al 100%       ${CLEAR}"
echo -e "${GREEN}======================================================${CLEAR}"
echo -e "• Red interna e Internet: ${GREEN}Habilitados${CLEAR}"
echo -e "• Zona horaria del host: ${GREEN}Sincronizada${CLEAR}"
echo -e "• Soporte APK ARM (Libhoudini): ${GREEN}Operativo${CLEAR}"
echo -e "• Iconos de gestión de Waydroid: ${RED}Ocultados${CLEAR}"
echo -e "• Integración de nuevas APKs en el menú: ${GREEN}Habilitada (Automática)${CLEAR}"
echo -e "\nRecuerda arrancar el entorno la primera vez desde la terminal con:"
echo -e "  ${BLUE}waydroid show-full-ui${CLEAR}\n"