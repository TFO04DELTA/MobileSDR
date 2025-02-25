#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import sys
import os
import json
import time
import threading
import queue
import serial
import pynmea2
import requests
from datetime import datetime, timedelta
import pathlib
import sqlite3
import glob
import webbrowser
from subprocess import Popen, PIPE
import tempfile
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

def check_requirements():
    """Check and install required packages"""
    required_packages = {
        'pynmea2': 'For GPS data parsing',
        'requests': 'For WiGLE API'
    }
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        msg = "Some required packages are missing. Would you like to install them?\n\n"
        for package in missing_packages:
            msg += f"• {package} - {required_packages[package]}\n"
        
        if messagebox.askyesno("Missing Requirements", msg):
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
                messagebox.showinfo("Success", "Packages installed successfully! Please restart the application.")
                sys.exit(0)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to install packages: {e}\n\nPlease run:\nsudo pip3 install {' '.join(missing_packages)}")
                sys.exit(1)
        else:
            sys.exit(1)

def check_system_requirements():
    """Check for required system tools"""
    required_tools = {
        'kismet': 'Wireless network monitoring',
        'airmon-ng': 'Monitor mode control',
        'iwconfig': 'Wireless interface management'
    }
    
    missing_tools = []
    for tool in required_tools:
        if not subprocess.run(['which', tool], capture_output=True).returncode == 0:
            missing_tools.append(tool)
    
    if missing_tools:
        msg = "Some required system tools are missing. Would you like to install them?\n\n"
        for tool in missing_tools:
            msg += f"• {tool} - {required_tools[tool]}\n"
        
        if messagebox.askyesno("Missing System Tools", msg):
            try:
                cmd = ['sudo', 'apt-get', 'install', '-y'] + missing_tools
                subprocess.check_call(cmd)
                messagebox.showinfo("Success", "Tools installed successfully!")
            except Exception as e:
                messagebox.showerror("Error", 
                    f"Failed to install tools: {e}\n\n"
                    f"Please run:\nsudo apt-get install {' '.join(missing_tools)}")
                sys.exit(1)
        else:
            sys.exit(1)

# Run requirement checks before importing other modules
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window during checks
    check_requirements()
    check_system_requirements()
    root.destroy()  # Clean up the hidden window

# Now import the rest of the required modules
import json
import time
import threading
import queue
import serial
import pynmea2
import requests
import webbrowser
from datetime import datetime, timedelta
import tempfile

class ChasingYourTailGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('Chasing Your Tail NG')
        self.root.geometry('1200x800')
        
        # Initialize configuration
        self.config = {
            'wigle': {'api_key': ''},
            'gps': {'device': '/dev/ttyACM0', 'baud_rate': 9600},
            'monitor': {'interface': ''}
        }
        self.load_config()
        
        # Create status indicators
        self.setup_status_indicators()
        
        # Create main notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create frames for each tab
        self.control_frame = ttk.Frame(self.notebook)
        self.tracking_frame = ttk.Frame(self.notebook)
        self.gps_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        
        # Add frames to notebook
        self.notebook.add(self.control_frame, text='Control Panel')
        self.notebook.add(self.tracking_frame, text='Device Tracking')
        self.notebook.add(self.gps_frame, text='GPS')
        self.notebook.add(self.settings_frame, text='Settings')
        
        # Setup each tab
        self.setup_control_tab()
        self.setup_tracking_tab()
        self.setup_gps_tab()
        self.setup_settings_tab()
        
        # Create output log at bottom
        self.setup_output_log()
        
        # Initialize states
        self.monitoring = False
        self.gps_running = False
        self.device_locations = {}
        self.current_location = None
        
        # Load ignore lists
        self.load_ignore_lists()

    def setup_status_indicators(self):
        """Setup status indicator lights"""
        status_frame = ttk.LabelFrame(self.root, text='System Status')
        status_frame.pack(fill='x', padx=5, pady=5)
        
        self.status_indicators = {}
        for service in ['Kismet', 'Monitor Mode', 'GPS', 'Tracking']:
            frame = ttk.Frame(status_frame)
            frame.pack(side='left', padx=10)
            
            self.status_indicators[service] = tk.Canvas(frame, width=15, height=15)
            self.status_indicators[service].pack(side='left', padx=2)
            self.status_indicators[service].create_oval(2, 2, 13, 13, fill='gray')
            
            ttk.Label(frame, text=service).pack(side='left')

    def setup_output_log(self):
        """Setup output log frame"""
        log_frame = ttk.LabelFrame(self.root, text='Log Output')
        log_frame.pack(fill='x', padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(log_frame, height=6)
        self.output_text.pack(fill='x', padx=5, pady=5)

    def setup_control_tab(self):
        """Setup control panel tab"""
        # Interface selection
        interface_frame = ttk.LabelFrame(self.control_frame, text='Interface Control')
        interface_frame.pack(fill='x', padx=5, pady=5)
        
        # Refresh interface list button
        ttk.Button(interface_frame, text='Refresh Interfaces', 
                   command=self.refresh_interfaces).pack(side='right', padx=5)
        
        self.interface_var = tk.StringVar()
        interfaces = self.get_wireless_interfaces()
        
        ttk.Label(interface_frame, text='Select Interface:').pack(side='left', padx=5)
        self.interface_combo = ttk.Combobox(interface_frame, textvariable=self.interface_var, 
                                          values=interfaces)
        self.interface_combo.pack(side='left', padx=5)
        
        # Service Control Frame
        service_frame = ttk.LabelFrame(self.control_frame, text='Service Controls')
        service_frame.pack(fill='x', padx=5, pady=5)
        
        # Kill processes button
        ttk.Button(service_frame, text='Kill Interfering Processes', 
                   command=self.kill_processes).pack(side='left', padx=5)
        
        # Monitor mode controls
        self.monitor_start_button = ttk.Button(service_frame, text='Enable Monitor Mode', 
                                             command=self.enable_monitor_mode)
        self.monitor_start_button.pack(side='left', padx=5)
        
        self.monitor_stop_button = ttk.Button(service_frame, text='Disable Monitor Mode', 
                                            command=self.disable_monitor_mode,
                                            state='disabled')
        self.monitor_stop_button.pack(side='left', padx=5)
        
        # Kismet controls
        self.kismet_start_button = ttk.Button(service_frame, text='Start Kismet', 
                                            command=self.start_kismet)
        self.kismet_start_button.pack(side='left', padx=5)
        
        self.kismet_stop_button = ttk.Button(service_frame, text='Stop Kismet', 
                                           command=self.stop_kismet,
                                           state='disabled')
        self.kismet_stop_button.pack(side='left', padx=5)
        
        # Device Tracking Frame
        tracking_frame = ttk.LabelFrame(self.control_frame, text='Device Tracking')
        tracking_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Tracking controls
        control_frame = ttk.Frame(tracking_frame)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        self.tracking_start_button = ttk.Button(control_frame, text='Start Tracking', 
                                              command=self.start_tracking)
        self.tracking_start_button.pack(side='left', padx=5)
        
        self.tracking_stop_button = ttk.Button(control_frame, text='Stop Tracking', 
                                             command=self.stop_tracking,
                                             state='disabled')
        self.tracking_stop_button.pack(side='left', padx=5)
        
        # Ignore List Frame
        ignore_frame = ttk.LabelFrame(tracking_frame, text='Ignore Lists')
        ignore_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # MAC Address ignore list
        mac_frame = ttk.Frame(ignore_frame)
        mac_frame.pack(fill='x', padx=5, pady=2)
        
        self.mac_entry = ttk.Entry(mac_frame)
        self.mac_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        ttk.Button(mac_frame, text='Add MAC', 
                   command=lambda: self.add_to_ignore('mac')).pack(side='left', padx=5)
        
        # SSID ignore list
        ssid_frame = ttk.Frame(ignore_frame)
        ssid_frame.pack(fill='x', padx=5, pady=2)
        
        self.ssid_entry = ttk.Entry(ssid_frame)
        self.ssid_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        ttk.Button(ssid_frame, text='Add SSID', 
                   command=lambda: self.add_to_ignore('ssid')).pack(side='left', padx=5)
        
        # Ignore lists display
        lists_frame = ttk.Frame(ignore_frame)
        lists_frame.pack(fill='both', expand=True, padx=5, pady=2)
        
        # MAC list
        mac_list_frame = ttk.Frame(lists_frame)
        mac_list_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        ttk.Label(mac_list_frame, text='Ignored MACs:').pack()
        self.mac_listbox = tk.Listbox(mac_list_frame, height=5)
        self.mac_listbox.pack(fill='both', expand=True)
        
        # SSID list
        ssid_list_frame = ttk.Frame(lists_frame)
        ssid_list_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        ttk.Label(ssid_list_frame, text='Ignored SSIDs:').pack()
        self.ssid_listbox = tk.Listbox(ssid_list_frame, height=5)
        self.ssid_listbox.pack(fill='both', expand=True)

    def refresh_interfaces(self):
        """Refresh wireless interface list"""
        interfaces = self.get_wireless_interfaces()
        self.interface_combo['values'] = interfaces
        self.log_output("Refreshed interface list")

    def kill_processes(self):
        """Kill interfering processes"""
        try:
            subprocess.run(['sudo', 'airmon-ng', 'check', 'kill'], check=True)
            self.log_output("Killed interfering processes")
        except Exception as e:
            self.log_output(f"Error killing processes: {e}")

    def start_tracking(self):
        """Start device tracking"""
        try:
            if not self.interface_var.get():
                messagebox.showerror('Error', 'Please select an interface')
                return
            
            self.monitoring = True
            self.tracking_start_button.config(state='disabled')
            self.tracking_stop_button.config(state='normal')
            self.update_status_indicator('Tracking', 'running')
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self.monitor_devices, daemon=True)
            self.monitor_thread.start()
            
            self.log_output("Started device tracking")
            
        except Exception as e:
            self.log_output(f"Error starting tracking: {e}")
            self.update_status_indicator('Tracking', 'error')

    def stop_tracking(self):
        """Stop device tracking"""
        try:
            self.monitoring = False
            self.tracking_start_button.config(state='normal')
            self.tracking_stop_button.config(state='disabled')
            self.update_status_indicator('Tracking', 'stopped')
            
            self.log_output("Stopped device tracking")
            
        except Exception as e:
            self.log_output(f"Error stopping tracking: {e}")

    def monitor_devices(self):
        """Monitor for devices"""
        while self.monitoring:
            try:
                # Read MAC addresses and SSIDs from ignore lists
                ignored_macs = set(self.mac_listbox.get(0, tk.END))
                ignored_ssids = set(self.ssid_listbox.get(0, tk.END))
                
                # Your device monitoring code here
                # Example: Read from kismet or directly from interface
                
                # Process each detected device
                # Example structure:
                """
                if mac not in ignored_macs and ssid not in ignored_ssids:
                    if self.current_location:  # If GPS is active
                        self.record_device_location(mac, ssid)
                    self.update_device_display(mac, ssid, rssi)
                """
                
                time.sleep(1)  # Prevent CPU overload
                
            except Exception as e:
                self.log_output(f"Monitoring error: {e}")
                time.sleep(1)

    def update_device_display(self, mac, ssid, rssi):
        """Update device display in time windows"""
        try:
            current_time = datetime.now()
            
            # Find appropriate time window
            for window in self.time_windows.values():
                window.insert('', 'end', values=(mac, 'Probe Request', ssid, current_time.strftime('%H:%M:%S')))
                
                # Keep only last 100 entries per window
                if window.get_children().__len__() > 100:
                    window.delete(window.get_children()[0])
                
        except Exception as e:
            self.log_output(f"Error updating display: {e}")

    def load_ignore_lists(self):
        """Load ignore lists from files"""
        try:
            # Load MAC addresses
            if os.path.exists('mac_ignore.txt'):
                with open('mac_ignore.txt', 'r') as f:
                    for line in f:
                        mac = line.strip()
                        if mac:
                            self.mac_listbox.insert(tk.END, mac)
            
            # Load SSIDs
            if os.path.exists('ssid_ignore.txt'):
                with open('ssid_ignore.txt', 'r') as f:
                    for line in f:
                        ssid = line.strip()
                        if ssid:
                            self.ssid_listbox.insert(tk.END, ssid)
                            
        except Exception as e:
            self.log_output(f"Error loading ignore lists: {e}")

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            self.log_output(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            self.log_output("Configuration saved")
        except Exception as e:
            self.log_output(f"Error saving config: {e}")

    def log_output(self, message):
        """Log message to output text widget"""
        timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
        if hasattr(self, 'output_text'):
            self.output_text.insert(tk.END, f"{timestamp} {message}\n")
            self.output_text.see(tk.END)
        print(f"{timestamp} {message}")

    def setup_tracking_tab(self):
        """Setup device tracking tab"""
        # Time windows frame
        time_windows_frame = ttk.LabelFrame(self.tracking_frame, text='Time Windows')
        time_windows_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create time window sections
        self.time_windows = {}
        for window in ['0-5 min', '5-10 min', '10-15 min', '15-20 min']:
            frame = ttk.LabelFrame(time_windows_frame, text=window)
            frame.pack(fill='x', padx=5, pady=2)
            
            tree = ttk.Treeview(frame, columns=('MAC', 'Type', 'SSID', 'Last Seen'),
                               show='headings', height=4)
            for col in ['MAC', 'Type', 'SSID', 'Last Seen']:
                tree.heading(col, text=col)
            tree.pack(fill='x', padx=2, pady=2)
            
            self.time_windows[window] = tree

    def setup_gps_tab(self):
        """Setup GPS tracking tab"""
        # GPS Control buttons
        control_frame = ttk.LabelFrame(self.gps_frame, text='GPS Control')
        control_frame.pack(fill='x', padx=5, pady=5)
        
        self.gps_start_button = ttk.Button(control_frame, text='Start GPS', 
                                         command=self.start_gps)
        self.gps_start_button.pack(side='left', padx=5, pady=5)
        
        self.gps_stop_button = ttk.Button(control_frame, text='Stop GPS', 
                                        command=self.stop_gps, state='disabled')
        self.gps_stop_button.pack(side='left', padx=5, pady=5)
        
        # GPS Status
        status_frame = ttk.LabelFrame(self.gps_frame, text='GPS Status')
        status_frame.pack(fill='x', padx=5, pady=5)
        
        self.gps_status = {
            'status': tk.StringVar(value='Not Connected'),
            'lat': tk.StringVar(value='--'),
            'lon': tk.StringVar(value='--'),
            'satellites': tk.StringVar(value='--'),
            'quality': tk.StringVar(value='--'),
            'speed': tk.StringVar(value='--'),
            'altitude': tk.StringVar(value='--')
        }
        
        for key, var in self.gps_status.items():
            frame = ttk.Frame(status_frame)
            frame.pack(fill='x', padx=2, pady=1)
            ttk.Label(frame, text=f"{key.title()}: ").pack(side='left')
            ttk.Label(frame, textvariable=var).pack(side='left')
        
        # GPS Location History
        history_frame = ttk.LabelFrame(self.gps_frame, text='Location History')
        history_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.location_tree = ttk.Treeview(history_frame, 
                                        columns=('Time', 'Lat', 'Long', 'Device', 'SSID'),
                                        show='headings')
        for col in ['Time', 'Lat', 'Long', 'Device', 'SSID']:
            self.location_tree.heading(col, text=col)
        self.location_tree.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Export button
        ttk.Button(self.gps_frame, text='Export GPS Data', 
                   command=self.export_gps_data).pack(padx=5, pady=5)

    def start_gps(self):
        """Start GPS monitoring"""
        try:
            # Check if GPS device is available
            if not os.path.exists(self.config['gps']['device']):
                messagebox.showerror('Error', f"GPS device {self.config['gps']['device']} not found")
                return
            
            # Check if device is busy
            try:
                self.gps_device = serial.Serial(
                    self.config['gps']['device'],
                    self.config['gps']['baud_rate'],
                    timeout=1,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
            except serial.SerialException as e:
                if 'Device or resource busy' in str(e):
                    # Try to release the device
                    subprocess.run(['sudo', 'systemctl', 'stop', 'gpsd'], check=False)
                    time.sleep(1)
                    self.gps_device = serial.Serial(
                        self.config['gps']['device'],
                        self.config['gps']['baud_rate'],
                        timeout=1,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE
                    )
            
            self.gps_running = True
            self.gps_start_button.config(state='disabled')
            self.gps_stop_button.config(state='normal')
            self.update_status_indicator('GPS', 'running')
            
            # Start GPS thread
            self.gps_thread = threading.Thread(target=self.monitor_gps, daemon=True)
            self.gps_thread.start()
            
            self.log_output("GPS monitoring started")
            
        except Exception as e:
            self.log_output(f"Error starting GPS: {e}")
            self.update_status_indicator('GPS', 'error')

    def stop_gps(self):
        """Stop GPS monitoring"""
        try:
            self.gps_running = False
            if hasattr(self, 'gps_device'):
                self.gps_device.close()
            
            self.gps_start_button.config(state='normal')
            self.gps_stop_button.config(state='disabled')
            self.update_status_indicator('GPS', 'stopped')
            
            self.log_output("GPS monitoring stopped")
            
        except Exception as e:
            self.log_output(f"Error stopping GPS: {e}")

    def update_status_indicator(self, service, status):
        """Update status indicator color"""
        colors = {
            'running': 'green',
            'stopped': 'gray',
            'error': 'red',
            'warning': 'yellow'
        }
        
        if service in self.status_indicators:
            self.status_indicators[service].create_oval(
                2, 2, 13, 13, 
                fill=colors.get(status, 'gray')
            )

    def setup_settings_tab(self):
        """Setup settings tab"""
        # WiGLE settings
        wigle_frame = ttk.LabelFrame(self.settings_frame, text='WiGLE API Settings')
        wigle_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(wigle_frame, text='API Key:').pack(padx=5, pady=2)
        self.wigle_api_key = ttk.Entry(wigle_frame, show='*')
        self.wigle_api_key.pack(fill='x', padx=5, pady=2)
        
        if 'wigle' in self.config and 'api_key' in self.config['wigle']:
            self.wigle_api_key.insert(0, self.config['wigle']['api_key'])
        
        ttk.Button(wigle_frame, text='Save Settings', 
                   command=self.save_config).pack(padx=5, pady=2)

    def test_wigle_api(self):
        """Test WiGLE API connection"""
        api_key = self.wigle_api_key.get()
        try:
            response = requests.get(
                'https://api.wigle.net/api/v2/profile/user',
                headers={'Authorization': f'Basic {api_key}'}
            )
            if response.status_code == 200:
                messagebox.showinfo('Success', 'WiGLE API connection successful!')
            else:
                messagebox.showerror('Error', 'Invalid API key or connection failed')
        except Exception as e:
            messagebox.showerror('Error', f'Connection error: {e}')

    def save_settings(self):
        """Save settings to config file"""
        config['wigle']['api_key'] = self.wigle_api_key.get()
        try:
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo('Success', 'Settings saved successfully!')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save settings: {e}')

    def check_wigle_data(self, ssid):
        """Query WiGLE for SSID information"""
        try:
            api_key = self.wigle_api_key.get()
            response = requests.get(
                'https://api.wigle.net/api/v2/network/search',
                params={'ssid': ssid},
                headers={'Authorization': f'Basic {api_key}'}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return len(data['results'])
            return 0
        except Exception as e:
            self.log_output(f"WiGLE API error: {e}")
            return 0

    def update_status(self):
        """Update status indicators periodically"""
        while True:
            try:
                # Run monitor.sh and parse output
                result = subprocess.run(['./monitor.sh'], 
                                     capture_output=True, 
                                     text=True, 
                                     timeout=5)
                
                # Parse output and update status labels
                output = result.stdout
                
                if "kismet up" in output.lower():
                    self.kismet_status.config(text="Kismet: Running")
                else:
                    self.kismet_status.config(text="Kismet: Stopped")
                    
                if "Monitor Mode Detected" in output:
                    self.monitor_status.config(text="Monitor Mode: Enabled")
                else:
                    self.monitor_status.config(text="Monitor Mode: Disabled")
                    
                # Add GPS status check
                gps_status = self.check_gps_status()
                self.gps_status.config(text=f"GPS: {gps_status}")
                
                # Add WiFi interface check
                wifi_status = self.check_wifi_status()
                self.wifi_status.config(text=f"WiFi: {wifi_status}")
                
            except Exception as e:
                print(f"Status update error: {e}")
            
            time.sleep(5)

    def check_gps_status(self):
        """Check GPS daemon status"""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'gpsd'],
                                  capture_output=True, text=True)
            return "Running" if result.stdout.strip() == "active" else "Stopped"
        except:
            return "Unknown"

    def check_wifi_status(self):
        """Check WiFi interface status"""
        try:
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            return "Connected" if "ESSID:" in result.stdout else "Disconnected"
        except:
            return "Unknown"

    # Control functions
    def start_kismet(self):
        """Start Kismet service"""
        try:
            # Kill any existing Kismet process
            subprocess.run(['sudo', 'killall', 'kismet'], check=False)
            time.sleep(1)
            
            # Start Kismet with selected interface
            interface = self.interface_var.get()
            if not interface:
                messagebox.showerror('Error', 'Please select an interface')
                return
            
            cmd = ['sudo', 'kismet', '-c', interface]
            self.kismet_process = subprocess.Popen(cmd, 
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
            
            time.sleep(2)  # Wait for Kismet to start
            
            # Check if Kismet is running
            if subprocess.run(['pgrep', 'kismet'], capture_output=True).returncode == 0:
                self.update_status_indicator('Kismet', 'running')
                self.kismet_start_button.config(state='disabled')
                self.kismet_stop_button.config(state='normal')
                self.log_output("Started Kismet")
            else:
                raise Exception("Failed to start Kismet")
            
        except Exception as e:
            self.log_output(f"Error starting Kismet: {e}")
            self.update_status_indicator('Kismet', 'error')

    def stop_kismet(self):
        """Stop Kismet service"""
        try:
            # Try graceful shutdown first
            subprocess.run(['killall', 'kismet'], check=True)
            
            # Force kill if still running
            result = subprocess.run(['pgrep', 'kismet'], capture_output=True)
            if result.returncode == 0:
                subprocess.run(['sudo', 'killall', '-9', 'kismet'], check=True)
            
            self.update_status_indicator('Kismet', 'stopped')
            self.kismet_start_button.config(state='normal')
            self.kismet_stop_button.config(state='disabled')
            self.log_output("Stopped Kismet")
            
        except Exception as e:
            self.log_output(f"Error stopping Kismet: {e}")
            self.update_status_indicator('Kismet', 'error')

    def enable_monitor_mode(self):
        """Enable monitor mode on selected interface"""
        interface = self.interface_var.get()
        if not interface:
            messagebox.showerror('Error', 'Please select an interface')
            return
            
        try:
            # Kill potentially interfering processes
            subprocess.run(['sudo', 'airmon-ng', 'check', 'kill'], check=True)
            
            # Enable monitor mode
            subprocess.run(['sudo', 'airmon-ng', 'start', interface], check=True)
            
            self.update_status_indicator('Monitor Mode', 'running')
            self.monitor_start_button.config(state='disabled')
            self.monitor_stop_button.config(state='normal')
            self.log_output(f"Enabled monitor mode on {interface}")
            
        except Exception as e:
            self.log_output(f"Error enabling monitor mode: {e}")
            self.update_status_indicator('Monitor Mode', 'error')

    def disable_monitor_mode(self):
        """Disable monitor mode on selected interface"""
        interface = self.interface_var.get()
        try:
            subprocess.run(['sudo', 'airmon-ng', 'stop', interface], check=True)
            
            self.update_status_indicator('Monitor Mode', 'stopped')
            self.monitor_start_button.config(state='normal')
            self.monitor_stop_button.config(state='disabled')
            self.log_output(f"Disabled monitor mode on {interface}")
            
        except Exception as e:
            self.log_output(f"Error disabling monitor mode: {e}")
            self.update_status_indicator('Monitor Mode', 'error')

    def run_probe_analyzer(self):
        subprocess.Popen(['python3', 'probe_analyzer.py'])
        self.log_output("Running probe analyzer...")

    # Ignore list management
    def add_to_ignore(self, list_type):
        """Add item to ignore list"""
        try:
            if list_type == 'mac':
                mac = self.mac_entry.get().strip().upper()
                if mac and len(mac) == 17:  # Basic MAC format check
                    self.mac_listbox.insert(tk.END, mac)
                    self.mac_entry.delete(0, tk.END)
                    self.save_ignore_list('mac')
                else:
                    messagebox.showerror('Error', 'Invalid MAC address format')
            else:  # SSID
                ssid = self.ssid_entry.get().strip()
                if ssid:
                    self.ssid_listbox.insert(tk.END, ssid)
                    self.ssid_entry.delete(0, tk.END)
                    self.save_ignore_list('ssid')
                
        except Exception as e:
            self.log_output(f"Error adding to ignore list: {e}")

    def save_ignore_list(self, list_type):
        """Save ignore list to file"""
        try:
            filename = 'mac_ignore.txt' if list_type == 'mac' else 'ssid_ignore.txt'
            listbox = self.mac_listbox if list_type == 'mac' else self.ssid_listbox
            
            with open(filename, 'w') as f:
                for i in range(listbox.size()):
                    f.write(listbox.get(i) + '\n')
                
            self.log_output(f"Saved {list_type} ignore list")
            
        except Exception as e:
            self.log_output(f"Error saving ignore list: {e}")

    def get_wireless_interfaces(self):
        """Get list of wireless interfaces"""
        try:
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if line and not line.startswith(' '):
                    interface = line.split()[0]
                    interfaces.append(interface)
            return interfaces
        except Exception as e:
            self.log_output(f"Error getting wireless interfaces: {e}")
            return []

    def monitor_gps(self):
        """Monitor GPS data"""
        while self.gps_running:
            try:
                if self.gps_device.in_waiting:
                    # Read raw NMEA sentence
                    line = self.gps_device.readline()
                    
                    try:
                        # Try to decode as NMEA (ASCII)
                        line = line.decode('ascii', errors='ignore')
                        
                        # Only process NMEA sentences
                        if line.startswith('$'):
                            msg = pynmea2.parse(line)
                            
                            if isinstance(msg, pynmea2.GGA):
                                # Update GPS status
                                self.gps_status['lat'].set(f"{msg.latitude:.6f}° {'N' if msg.lat_dir == 'N' else 'S'}")
                                self.gps_status['lon'].set(f"{msg.longitude:.6f}° {'E' if msg.lon_dir == 'E' else 'W'}")
                                self.gps_status['satellites'].set(str(msg.num_satellites))
                                self.gps_status['quality'].set(self.get_fix_quality(msg.gps_qual))
                                
                                # Store current location
                                self.current_location = (msg.latitude, msg.longitude)
                                
                            elif isinstance(msg, pynmea2.VTG):
                                # Update speed if available
                                if hasattr(msg, 'spd_over_grnd_kmph'):
                                    self.gps_status['speed'].set(f"{msg.spd_over_grnd_kmph:.1f} km/h")
                                
                    except UnicodeDecodeError:
                        # Skip invalid data
                        continue
                    except pynmea2.ParseError:
                        # Skip invalid NMEA sentences
                        continue
                    
                time.sleep(0.1)  # Prevent CPU overload
                
            except Exception as e:
                self.log_output(f"GPS monitoring error: {str(e)}")
                time.sleep(1)  # Wait before retrying

    def get_fix_quality(self, qual):
        """Convert GPS quality indicator to string"""
        quality_map = {
            0: 'No Fix',
            1: 'GPS Fix',
            2: 'DGPS Fix',
            3: 'PPS Fix',
            4: 'RTK Fix',
            5: 'Float RTK',
            6: 'Estimated',
            7: 'Manual',
            8: 'Simulation'
        }
        return quality_map.get(qual, 'Unknown')

    def update_location(self, msg):
        """Update device location"""
        self.gps_status['lat'].set(f"{msg.lat:.6f}")
        self.gps_status['lon'].set(f"{msg.lon:.6f}")
        self.gps_status['satellites'].set(f"{msg.num_sats}")
        self.gps_status['quality'].set(msg.gps_qual)
        self.gps_status['speed'].set(f"{msg.spd_over_grnd:.2f} km/h")
        self.gps_status['altitude'].set(f"{msg.altitude:.2f} m")
        self.location_tree.insert('', 'end', values=(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            self.gps_status['lat'].get(),
            self.gps_status['lon'].get(),
            'GPS',
            'N/A'
        ))

    def export_gps_data(self):
        """Export GPS data to file"""
        data = self.location_tree.get_children()
        if not data:
            messagebox.showinfo('Info', 'No GPS data to export')
            return
        
        filename = f"gps_data_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        with open(filename, 'w') as f:
            f.write("Time,Latitude,Longitude,Device,SSID\n")
            for record in data:
                values = self.location_tree.item(record)['values']
                f.write(f"{','.join(values)}\n")
        
        messagebox.showinfo('Success', f"GPS data exported to {filename}")

def main():
    root = tk.Tk()
    app = ChasingYourTailGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
