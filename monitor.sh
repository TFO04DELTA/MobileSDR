#!/bin/bash

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_kismet() {
    if pgrep -x "kismet" >/dev/null; then
        echo -e "${GREEN}Kismet: Running${NC}"
        return 0
    else
        echo -e "${RED}Kismet: Not Running${NC}"
        return 1
    fi
}

check_monitor_mode() {
    monitor_found=false
    for iface in $(iwconfig 2>/dev/null | grep -o '^[[:alnum:]]*'); do
        if iwconfig $iface 2>/dev/null | grep -q "Mode:Monitor"; then
            echo -e "${GREEN}Monitor Mode: Active on $iface${NC}"
            monitor_found=true
            return 0
        fi
    done
    
    if ! $monitor_found; then
        echo -e "${RED}Monitor Mode: Not Active${NC}"
        return 1
    fi
}

check_gps() {
    if systemctl is-active --quiet gpsd; then
        gps_data=$(timeout 2 gpspipe -w -n 5 2>/dev/null)
        
        if [ $? -eq 124 ]; then
            echo -e "${YELLOW}GPS: Timeout reading data${NC}"
            return 1
        fi
        
        if [[ $gps_data == *"\"mode\":3"* ]]; then
            echo -e "${GREEN}GPS: 3D Fix${NC}"
            return 0
        elif [[ $gps_data == *"\"mode\":2"* ]]; then
            echo -e "${GREEN}GPS: 2D Fix${NC}"
            return 0
        else
            echo -e "${RED}GPS: No Fix${NC}"
            return 1
        fi
    else
        echo -e "${RED}GPS Service: Not Running${NC}"
        return 1
    fi
}

while true; do
    clear
    echo "=== System Status ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "===================="
    
    check_kismet
    check_monitor_mode
    check_gps
    
    echo "===================="
    sleep 5
done
