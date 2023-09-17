#!/usr/bin/env python
# test script by running:
# /home/pi/pialert/front/plugins/db_cleanup/script.py pluginskeephistory=250 hourstokeepnewdevice=48 daystokeepevents=90

import os
import pathlib
import argparse
import sys
import hashlib
import csv
import sqlite3
from io import StringIO
from datetime import datetime

sys.path.append("/home/pi/pialert/front/plugins")
sys.path.append('/home/pi/pialert/pialert') 

from plugin_helper import Plugin_Object, Plugin_Objects, decodeBase64
from logger import mylog, append_line_to_file
from helper import timeNowTZ
from const import logPath, pialertPath
from device import query_MAC_vendor


CUR_PATH = str(pathlib.Path(__file__).parent.resolve())
LOG_FILE = os.path.join(CUR_PATH, 'script.log')
RESULT_FILE = os.path.join(CUR_PATH, 'last_result.log')

def main():   

    mylog('verbose', ['[VNDRPDT] In script']) 

    # Get newest DB   
    update_vendor_database()

    # Resolve missing vendors
    plugin_objects = Plugin_Objects(RESULT_FILE)

    plugin_objects = update_vendors('/home/pi/pialert/db/pialert.db', plugin_objects)

    plugin_objects.write_result_file()
    
    mylog('verbose', ['[VNDRPDT] Update complete'])   
    
    return 0

#===============================================================================
# Update device vendors database
#===============================================================================
def update_vendor_database():

    # Update vendors DB (iab oui)
    mylog('verbose', ['    Updating vendors DB (iab & oui)'])    
    update_args = ['sh', pialertPath + '/back/update_vendors.sh']

    # Execute command     
    try:
        # try runnning a subprocess safely
        update_output = subprocess.check_output (update_args)
    except subprocess.CalledProcessError as e:
        # An error occured, handle it
        mylog('none', ['    FAILED: Updating vendors DB, set LOG_LEVEL=debug for more info'])  
        mylog('none', [e.output])        


# resolve missing vendors
def update_vendors (dbPath, plugin_objects): 
   
    # Connect to the PiAlert SQLite database
    conn    = sqlite3.connect(dbPath)
    cursor  = conn.cursor()

    # Initialize variables
    recordsToUpdate = []
    ignored = 0
    notFound = 0

    # All devices loop
    mylog('verbose', ['    Searching devices vendor'])    

    for device in cursor.execute ("""SELECT * FROM Devices
                                        WHERE   dev_Vendor      = '(unknown)' 
                                                OR dev_Vendor   =''
                                                OR dev_Vendor   IS NULL""") :
        # Search vendor in HW Vendors DB
        vendor = query_MAC_vendor (device['dev_MAC'])
        if vendor == -1 :
            notFound += 1
        elif vendor == -2 :
            ignored += 1
        else :
            plugin_objects.add_object(
                primaryId   = device['dev_MAC'],        # MAC (Device Name)
                secondaryId = device['dev_LastIP'],     # IP Address (always 0.0.0.0)
                watched1    = vendor,  
                watched2    = device['dev_Name'],
                watched3    = "",
                watched4    = "",
                extra       = "",            
                foreignKey  = device['dev_MAC']           
            )            
            
    # Print log    
    mylog('verbose', ["    Devices Ignored:  ", ignored])
    mylog('verbose', ["    Vendors Not Found:", notFound])
    mylog('verbose', ["    Vendors updated:  ", len(plugin_objects) ])

    conn.commit()    
    # Close the database connection
    conn.close()

    return plugin_objects

    

#===============================================================================
# BEGIN
#===============================================================================
if __name__ == '__main__':
    main()