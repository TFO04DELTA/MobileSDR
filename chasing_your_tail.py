### Chasing Your Tail V04_15_22
### @matt0177
### Released under the MIT License https://opensource.org/licenses/MIT
###

import sqlite3
import time
from datetime import datetime, timedelta
import glob
import os
import json
import pathlib
import signal
import sys

with open('config.json', 'r') as f:
    config = json.load(f)

### Check for/make subdirectories for logs, ignore lists etc.
cyt_sub = pathlib.Path(config['paths']['log_dir'])
cyt_sub.mkdir(parents=True, exist_ok=True)

print ('Current Time: ' + time.strftime('%Y-%m-%d %H:%M:%S'))

### Create Log file

log_file_name = f'./logs/cyt_log_{time.strftime("%m%d%y_%H%M%S")}'

cyt_log = open(log_file_name,"w", buffering=1) 


#######Import ignore list and alert if not found

non_alert_ssid_list = []
ssid_list_path = pathlib.Path('./ignore_lists') / config['paths']['ignore_lists']['ssid']
if ssid_list_path.exists():
    with open(ssid_list_path, 'r') as f:
        exec(f.read())  # This will execute the line that sets non_alert_ssid_list

if non_alert_ssid_list:
	pass
else:
    print ("No Probed SSID Ignore List Found!")
    cyt_log.write("No Probed SSID Ignore List Found! \n")
    
probe_ignore_list = non_alert_ssid_list

ignore_list = []
ignore_list_path = pathlib.Path('./ignore_lists') / config['paths']['ignore_lists']['mac']
if ignore_list_path.exists():
    with open(ignore_list_path, 'r') as f:
        exec(f.read())  # This will execute the line that sets ignore_list

if ignore_list:
	pass
else:
    print ("No Ignore List Found!")
    cyt_log.write("No Ignore List Found! \n")
    
    
print ('{} MACs added to ignore list.'.format(len(ignore_list)))
print ('{} Probed SSIDs added to ignore list.'.format(len(probe_ignore_list)))
cyt_log.write ('{} MACs added to ignore list. \n'.format(len(ignore_list)))
cyt_log.write ('{} Probed SSIDs added to ignore list. \n'.format(len(probe_ignore_list)))

### Set Initial Variables
db_path = config['paths']['kismet_logs']

###Initialize Lists
current_macs = []
five_ten_min_ago_macs = []
ten_fifteen_min_ago_macs = []
fifteen_twenty_min_ago_macs = []
current_ssids = []
five_ten_min_ago_ssids = []
ten_fifteen_min_ago_ssids = []
fifteen_twenty_min_ago_ssids = []

past_five_mins_macs = []
past_five_mins_ssids = []

### Calculate Time Variables
two_mins_ago = datetime.now() + timedelta(minutes=-2)  
unixtime_2_ago = time.mktime(two_mins_ago.timetuple())  ### Two Minute time used for current results
five_mins_ago = datetime.now() + timedelta(minutes=-5)
unixtime_5_ago = time.mktime(five_mins_ago.timetuple())
ten_mins_ago = datetime.now() + timedelta(minutes=-10)
unixtime_10_ago = time.mktime(ten_mins_ago.timetuple())
fifteen_mins_ago = datetime.now() + timedelta(minutes=-15)
unixtime_15_ago = time.mktime(fifteen_mins_ago.timetuple())
twenty_mins_ago = datetime.now() + timedelta(minutes=-20)
unixtime_20_ago = time.mktime(twenty_mins_ago.timetuple())

######Find Newest DB file
list_of_files = glob.glob(db_path)
latest_file = max(list_of_files, key=os.path.getctime)
print ("Pulling data from: {}".format(latest_file))
cyt_log.write ("Pulling data from: {} \n".format(latest_file))
con = sqlite3.connect(latest_file) ## kismet DB to point at

######Initialize macs past five minutes

def sql_fetch_past_5(con): 
    cursorObj = con.cursor()
    cursorObj.execute("SELECT devmac FROM devices WHERE last_time >= {}".format(unixtime_5_ago)) 
    rows = cursorObj.fetchall()
    for row in rows:
        #print(row)
        stripped_val = str(row).replace("(","").replace(")","").replace("'","").replace(",","")
        
        if stripped_val in ignore_list:
            pass
        else:
            #print ("new one!")
            past_five_mins_macs.append(stripped_val)

sql_fetch_past_5(con)

print ("{} MACS added to the within the past 5 mins list".format(len(past_five_mins_macs)))
cyt_log.write ("{} MACS added to the within the past 5 mins list \n".format(len(past_five_mins_macs)))
######Initialize macs five to ten minutes ago

def sql_fetch_5_to_10(con): 
    cursorObj = con.cursor()
    cursorObj.execute("SELECT devmac FROM devices WHERE last_time <= {} AND last_time >= {} ".format(unixtime_5_ago, unixtime_10_ago)) 
    rows = cursorObj.fetchall()
    for row in rows:
        #print(row)
        stripped_val = str(row).replace("(","").replace(")","").replace("'","").replace(",","")
        
        if stripped_val in ignore_list:
            pass
        else:
            #print ("new one!")
            five_ten_min_ago_macs.append(stripped_val)

sql_fetch_5_to_10(con)

print ("{} MACS added to the 5 to 10 mins ago list".format(len(five_ten_min_ago_macs)))
cyt_log.write ("{} MACS added to the 5 to 10 mins ago list \n".format(len(five_ten_min_ago_macs)))

######Initialize macs ten to fifteen minutes ago

def sql_fetch_10_to_15(con):
    cursorObj = con.cursor()
    cursorObj.execute("SELECT devmac FROM devices WHERE last_time <= {} AND last_time >= {} ".format(unixtime_10_ago, unixtime_15_ago)) 
    rows = cursorObj.fetchall()
    for row in rows:
        #print(row)
        stripped_val = str(row).replace("(","").replace(")","").replace("'","").replace(",","")
		        
        if stripped_val in ignore_list:
            pass
        else:
            #print ("new one!")
            ten_fifteen_min_ago_macs.append(stripped_val)
        

sql_fetch_10_to_15(con)

print ("{} MACS added to the 10 to 15 mins ago list".format(len(ten_fifteen_min_ago_macs)))
cyt_log.write ("{} MACS added to the 10 to 15 mins ago list \n".format(len(ten_fifteen_min_ago_macs)))

######Initialize macs fifteen to twenty minutes ago

def sql_fetch_15_to_20(con):
    cursorObj = con.cursor()
    cursorObj.execute("SELECT devmac FROM devices WHERE last_time <= {} AND last_time >= {} ".format(unixtime_15_ago, unixtime_20_ago)) 
    rows = cursorObj.fetchall()
    for row in rows:
        #print(row)
        stripped_val = str(row).replace("(","").replace(")","").replace("'","").replace(",","")
		
        if stripped_val in ignore_list:
            pass
        else:
            #print ("new one!")
            fifteen_twenty_min_ago_macs.append(stripped_val)
        

sql_fetch_15_to_20(con)

print ("{} MACS added to the 15 to 20 mins ago list".format(len(fifteen_twenty_min_ago_macs)))
cyt_log.write("{} MACS added to the 15 to 20 mins ago list \n".format(len(fifteen_twenty_min_ago_macs)))

######Initialize probe requests past 5 minutes

def probe_request_sql_fetch(con, start_time, end_time=None, target_list=None):
    """Generic probe request fetcher
    Args:
        con: Database connection
        start_time: Start time in unix timestamp
        end_time: Optional end time in unix timestamp
        target_list: List to append results to
    """
    query = "SELECT devmac, type, device FROM devices WHERE last_time >= ?"
    params = [start_time]
    if end_time:
        query += " AND last_time <= ?"
        params.append(end_time)
        
    cursorObj = con.cursor()
    cursorObj.execute(query, params)
    rows = cursorObj.fetchall()
    
    for row in rows:
        raw_device_json = json.loads(str(row[2], errors='ignore'))
        if 'dot11.probedssid.ssid' in str(row):
            ssid = raw_device_json["dot11.device"]["dot11.device.last_probed_ssid_record"]["dot11.probedssid.ssid"]
            if ssid and ssid not in probe_ignore_list:
                target_list.append(ssid)

probe_request_sql_fetch(con, unixtime_5_ago, unixtime_10_ago, past_five_mins_ssids)

print ("{} Probed SSIDs added to the within the past 5 minutes list".format(len(past_five_mins_ssids)))
cyt_log.write ("{} Probed SSIDs added to the within the past 5 minutes list \n".format(len(past_five_mins_ssids)))

######Initialize probe requests five to ten minutes ago

probe_request_sql_fetch(con, unixtime_5_ago, unixtime_10_ago, five_ten_min_ago_ssids)

print ("{} Probed SSIDs added to the 5 to 10 mins ago list".format(len(five_ten_min_ago_ssids)))
cyt_log.write("{} Probed SSIDs added to the 5 to 10 mins ago list \n".format(len(five_ten_min_ago_ssids)))

######Initialize probe requests ten to fifteen minutes ago

probe_request_sql_fetch(con, unixtime_10_ago, unixtime_15_ago, ten_fifteen_min_ago_ssids)

print ("{} Probed SSIDs added to the 10 to 15 mins ago list".format(len(ten_fifteen_min_ago_ssids)))
cyt_log.write ("{} Probed SSIDs added to the 10 to 15 mins ago list \n".format(len(ten_fifteen_min_ago_ssids)))

######Initialize probe requests fifteem to twenty minutes ago

probe_request_sql_fetch(con, unixtime_15_ago, unixtime_20_ago, fifteen_twenty_min_ago_ssids)

print ("{} Probed SSIDs added to the 15 to 20 mins ago list".format(len(fifteen_twenty_min_ago_ssids)))
cyt_log.write("{} Probed SSIDs added to the 15 to 20 mins ago list \n".format(len(fifteen_twenty_min_ago_ssids)))

#### Define main logic

def sql_fetch_current(con):
    two_mins_ago = datetime.now() + timedelta(minutes=-2)  
    unixtime_2_ago = time.mktime(two_mins_ago.timetuple())
    cursorObj = con.cursor()
    cursorObj.execute("SELECT devmac, type, device FROM devices WHERE last_time >= {}".format(unixtime_2_ago)) 
    rows = cursorObj.fetchall()
    for row in rows:
        raw_device_json = json.loads(str(row[2], errors='ignore'))
        stripped_val = str(row[0])  # Get MAC directly
        
        if stripped_val in ignore_list:
            continue
            
        # Track device movement through time windows
        if stripped_val in five_ten_min_ago_macs:
            print("ALERT: {} {} seen again after 5-10 mins".format(stripped_val, row[1]))
            cyt_log.write("ALERT: {} {} seen again after 5-10 mins\n".format(stripped_val, row[1]))
        if stripped_val in ten_fifteen_min_ago_macs:
            print("WARNING: {} {} seen again after 10-15 mins".format(stripped_val, row[1]))
            cyt_log.write("WARNING: {} {} seen again after 10-15 mins\n".format(stripped_val, row[1]))
        if stripped_val in fifteen_twenty_min_ago_macs:
            print("CRITICAL: {} {} potentially following - seen across 15-20 min window".format(stripped_val, row[1]))
            cyt_log.write("CRITICAL: {} {} potentially following - seen across 15-20 min window\n".format(stripped_val, row[1]))

## End sql_fetch_current



#### Begin Time Loop

time_count = 0

DEBUG = False  # Set via command line arg or config

def debug_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)
        cyt_log.write(f"[DEBUG] {' '.join(map(str, args))}\n")

def signal_handler(signum, frame):
    print("\nShutting down gracefully...")
    cyt_log.write("Shutting down gracefully...\n")
    cyt_log.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def monitor_probe_requests(con, device_json):
    """Monitor and process new probe requests"""
    try:
        if 'dot11.device' in device_json:
            dot11_data = device_json['dot11.device']
            if 'dot11.device.last_probed_ssid_record' in dot11_data:
                probe_data = dot11_data['dot11.device.last_probed_ssid_record']
                if 'dot11.probedssid.ssid' in probe_data:
                    ssid = probe_data['dot11.probedssid.ssid']
                    if ssid and ssid not in probe_ignore_list:
                        print(f"Found a probe!: {ssid}")
                        cyt_log.write(f"Found a probe!: {ssid}\n")
                        return ssid
    except Exception as e:
        debug_print(f"Error processing probe request: {e}")
    return None

def check_new_devices(con):
    """Check for new devices and probe requests"""
    two_mins_ago = datetime.now() + timedelta(minutes=-2)  
    unixtime_2_ago = time.mktime(two_mins_ago.timetuple())
    
    cursorObj = con.cursor()
    cursorObj.execute("""
        SELECT devmac, type, device, last_time 
        FROM devices 
        WHERE last_time >= ?
        ORDER BY last_time DESC
    """, (unixtime_2_ago,))
    
    rows = cursorObj.fetchall()
    new_devices = []
    
    for row in rows:
        mac = str(row[0])
        dev_type = row[1]
        device_json = json.loads(str(row[2], errors='ignore'))
        last_time = datetime.fromtimestamp(row[3])
        
        if mac in ignore_list:
            continue
            
        # Check for probe requests
        probed_ssid = monitor_probe_requests(con, device_json)
        
        # Track device persistence
        device_info = {
            'mac': mac,
            'type': dev_type,
            'last_seen': last_time,
            'probed_ssid': probed_ssid
        }
        new_devices.append(device_info)
        
        # Check time windows for persistence
        if mac in five_ten_min_ago_macs:
            alert = f"ALERT: Device {mac} ({dev_type}) seen again after 5-10 mins"
            if probed_ssid:
                alert += f" - Probing for: {probed_ssid}"
            print(alert)
            cyt_log.write(f"{alert}\n")
            
        if mac in ten_fifteen_min_ago_macs:
            warning = f"WARNING: Device {mac} ({dev_type}) seen again after 10-15 mins"
            if probed_ssid:
                warning += f" - Probing for: {probed_ssid}"
            print(warning)
            cyt_log.write(f"{warning}\n")
            
        if mac in fifteen_twenty_min_ago_macs:
            critical = f"CRITICAL: Device {mac} ({dev_type}) potentially following - seen across 15-20 min window"
            if probed_ssid:
                critical += f" - Probing for: {probed_ssid}"
            print(critical)
            cyt_log.write(f"{critical}\n")
    
    return new_devices

while True:
    time_count += 1
    try:
        # Check for new devices and probe requests
        new_devices = check_new_devices(con)
        current_macs = [d['mac'] for d in new_devices]
        
        # Update time windows every 5 minutes
        if time_count % 5 == 0:
            ##Update Lists
            fifteen_twenty_min_ago_macs = ten_fifteen_min_ago_macs
            ten_fifteen_min_ago_macs = five_ten_min_ago_macs
            
            print("Updated MAC tracking lists:")
            print(f"- 15-20 min ago: {len(fifteen_twenty_min_ago_macs)}")
            print(f"- 10-15 min ago: {len(ten_fifteen_min_ago_macs)}")
            print(f"- 5-10 min ago: {len(five_ten_min_ago_macs)}")
            print(f"- Current: {len(current_macs)}")
            
            # Still log everything to the file
            cyt_log.write ("{} MACs moved to the 15-20 Min list \n".format(len(fifteen_twenty_min_ago_macs)))
            cyt_log.write ("{} MACs moved to the 10-15 Min list \n".format(len(ten_fifteen_min_ago_macs)))
            
            fifteen_twenty_min_ago_ssids = ten_fifteen_min_ago_ssids
            ten_fifteen_min_ago_ssids = five_ten_min_ago_ssids
            
            print ("{} Probed SSIDs moved to the 15 to 20 mins ago list".format(len(fifteen_twenty_min_ago_ssids)))
            print ("{} Probed SSIDs moved to the 10 to 15 mins ago list".format(len(ten_fifteen_min_ago_ssids)))
            
            cyt_log.write ("{} Probed SSIDs moved to the 15 to 20 mins ago list \n".format(len(fifteen_twenty_min_ago_ssids)))
            cyt_log.write ("{} Probed SSIDs moved to the 10 to 15 mins ago list \n".format(len(ten_fifteen_min_ago_ssids)))
            
            ###Update time variables
            five_mins_ago = datetime.now() + timedelta(minutes=-5)
            unixtime_5_ago = time.mktime(five_mins_ago.timetuple())
            ten_mins_ago = datetime.now() + timedelta(minutes=-10)
            unixtime_10_ago = time.mktime(ten_mins_ago.timetuple())
            
            ###Clear recent lists
            five_ten_min_ago_macs = []
            five_ten_min_ago_ssids = []
            
            ### Move the past 5 check from 5 mins ago into the past 5-10 list
            #sql_fetch_5_to_10(con)
            five_ten_min_ago_macs = past_five_mins_macs
            print ("{} MACs moved to the 5 to 10 mins ago list".format(len(five_ten_min_ago_macs)))
            cyt_log.write ("{} MACs moved to the 5 to 10 mins ago list \n".format(len(five_ten_min_ago_macs)))
            five_ten_min_ago_ssids = past_five_mins_ssids
            print ("{} Probed SSIDs moved to the 5 to 10 mins ago list".format(len(five_ten_min_ago_ssids)))
            cyt_log.write ("{} Probed SSIDs moved to the 5 to 10 mins ago list \n".format(len(five_ten_min_ago_ssids)))
            
            ### Update past 5 min check to have them ready for 5 mins from now
            past_five_mins_macs = []
            past_five_mins_ssids = []
            
            sql_fetch_past_5(con)
            probe_request_sql_fetch(con, unixtime_5_ago, unixtime_10_ago, past_five_mins_ssids)
            #print ("{} MACs seen within the past 5 minutes".format(len(past_five_mins_macs)))
            #past_five_mins_ssids
            
            # Refresh the database connection periodically
            con.close()
            latest_file = max(glob.glob(db_path), key=os.path.getctime)
            con = sqlite3.connect(latest_file)
            print(f"Refreshed database connection: {latest_file}")
            cyt_log.write(f"Refreshed database connection: {latest_file}\n")
            
        # Add debug information
        if DEBUG:
            debug_print(f"Active devices in current window: {len(current_macs)}")
            for device in new_devices:
                if device.get('probed_ssid'):
                    debug_print(f"Device {device['mac']} probing for {device['probed_ssid']}")
                    
    except Exception as e:
        print(f"Error in main loop: {e}")
        cyt_log.write(f"Error in main loop: {e}\n")
        time.sleep(5)  # Wait before retrying
        continue
        
    time.sleep(60)  # Check every minute
