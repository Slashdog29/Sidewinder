#!/usr/bin/env bash

# Salir de inmediato si ocurre un error
set -e

# Paleta de colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CLEAR='\033[0m'

echo -e "${BLUE}======================================================${CLEAR}"
echo -e "${BLUE}   Waydroid Installer (Smart Menu Sync) - ARCH        ${CLEAR}"
echo -e "${BLUE}======================================================${CLEAR}"

# 1. Control de exclusividad: Solo Arch Linux y derivados
if [ ! -f /etc/arch-release ] && ! grep -qi "arch" /etc/os-release; then
    echo -e "${RED}[!] ERROR: Este script está diseñado exclusivamente para Arch Linux o sus variantes.${CLEAR}"
    exit 1
fi
echo -e "${GREEN}[✓] Sistema compatible verificado (Base Arch).${CLEAR}"

# 2. Instalación de dependencias del sistema y de red
echo -e "\n${YELLOW}[1/7] Instalando paquetes y dependencias esenciales...${CLEAR}"
sudo pacman -S --needed waydroid lzip python git dnsmasq iptables --noconfirm

# 3. Configuración de Red automatizada (IP Forwarding)
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

# 4. Activación del servicio del contenedor
echo -e "\n${YELLOW}[3/7] Activando el servicio base de Waydroid...${CLEAR}"
sudo systemctl enable --now waydroid-container

# 5. Inicialización de la imagen limpia (Vanilla)
echo -e "\n${YELLOW}[4/7] Descargando e inicializando imagen Vanilla (Sin GApps)...${CLEAR}"
if [ -d "/var/lib/waydroid/cells" ] && [ "$(ls -A /var/lib/waydroid/cells)" ]; then
    echo -e "${GREEN}-> El sistema ya cuenta con una imagen base. Saltando descarga...${CLEAR}"
else
    sudo waydroid init -f
fi

# Forzar reinicio para levantar la interfaz de red waydroid0 correctamente
sudo systemctl restart waydroid-container
sleep 3

# 6. Sincronización automática de Fecha, Hora y Zona Horaria
echo -e "\n${YELLOW}[5/7] Sincronizando la hora y zona horaria de la PC con Android...${CLEAR}"
HOST_TZ=$(timedatectl show --property=Timezone --value)
if [ -z "$HOST_TZ" ]; then
    HOST_TZ=$(readlink /etc/localtime | sed 's#.*/zoneinfo/##')
fi
echo -e "${BLUE}-> Zona horaria detectada: $HOST_TZ${CLEAR}"
sudo waydroid prop set persist.sys.timezone "$HOST_TZ"

# 7. Descarga e inyección del Traductor ARM (Libhoudini)
echo -e "\n${YELLOW}[6/7] Instalando traductor Libhoudini para compatibilidad ARM...${CLEAR}"
TMP_DIR="/tmp/waydroid_setup"
rm -rf "$TMP_DIR" && mkdir -p "$TMP_DIR" && cd "$TMP_DIR"

git clone https://github.com/casualsnek/waydroid_script.git
cd waydroid_script

sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt
sudo ./venv/bin/python3 main.py install libhoudini

# 8. ENMASCARAMIENTO INTELIGENTE DE LANZADORES DE GESTIÓN
echo -e "\n${YELLOW}[7/7] Ocultando herramientas de gestión (Tus APKs sí se verán)...${CLEAR}"

# Asegurar que el directorio local del usuario existe
mkdir -p ~/.local/share/applications

# Buscamos los lanzadores de administración del sistema para clonarlos y ocultarlos
for file in /usr/share/applications/*waydroid*.desktop /usr/share/applications/*Waydroid*.desktop; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        # Copiar el acceso directo global a tu espacio de usuario
        cp "$file" ~/.local/share/applications/
        # Limpiar cualquier regla previa de visualización e inyectar el modo oculto
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
echo -e "======================================================${CLEAR}"
echo -e "• Red interna e Internet: ${GREEN}Habilitados${CLEAR}"
echo -e "• Zona horaria del host: ${GREEN}Sincronizada${CLEAR}"
echo -e "• Soporte APK ARM (Libhoudini): ${GREEN}Operativo${CLEAR}"
echo -e "• Iconos de gestión de Waydroid: ${RED}Ocultados${CLEAR}"
echo -e "• Integración de nuevas APKs en el menú: ${GREEN}Habilitada (Automática)${CLEAR}"
echo -e "\nRecuerda arrancar el entorno la primera vez desde la terminal con:"
echo -e "  ${BLUE}waydroid show-full-ui${CLEAR}\n"