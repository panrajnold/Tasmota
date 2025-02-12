#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
   upload-ota-201.py - Upload Tasmota firmware file

   Copyright (C) 2021  Theo Arends

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.

Requirements:
   - Python 3.x and Pip:
      sudo apt-get install python3 python3-pip
      pip3 install paho-mqtt json

Instructions:
   Edit file and change parameters in User Configuration Section

   Then execute command upload-ota-201.py

"""

import paho.mqtt.client as mqtt
import time
import base64
import hashlib
import json

# **** Start of User Configuration Section

broker = "domus1"                      # MQTT broker ip address or name
broker_port = 1883                     # MQTT broker port

mytopic = "demo"                       # Tasmota MQTT topic
#myfile = "../../build_output/firmware/tasmota32.bin"   # Tasmota esp32 firmware file name
myfile = "../../build_output/firmware/tasmota.bin.gz"  # Tasmota esp8266 firmware file name
myfiletype = 1                         # Tasmota firmware file type

# **** End of User Configuration Section

# Derive fulltopic from broker LWT message
mypublish = "cmnd/"+mytopic+"/fileupload"
mysubscribe = "stat/"+mytopic+"/FILEUPLOAD"  # Case sensitive

Ack_flag = False

file_id = 114                          # Even id between 2 and 254
file_chunk_size = 700                  # Default Tasmota MQTT max message size

# The callback for when mysubscribe message is received
def on_message(client, userdata, msg):
   global Ack_flag
   global file_chunk_size

   rcv_code = ""
   rcv_id = 0

#   print("Received message =",str(msg.payload.decode("utf-8")))

   root = json.loads(msg.payload.decode("utf-8"))
   if "Command" in root: rcv_code = root["Command"]
   if rcv_code == "Error":
      print("Error: Command error")
      return

   if "Id" in root: rcv_id = root["Id"]
   if rcv_id == file_id:
      if "MaxSize" in root: file_chunk_size = root["MaxSize"]

   Ack_flag = False

def wait_for_ack():
   global Ack_flag
   timeout = 100
   while Ack_flag and timeout > 0:
      time.sleep(0.01)
      timeout = timeout -1

   if Ack_flag:
      print("Error: Ack timeout")

   return Ack_flag

client = mqtt.Client()
client.on_message = on_message
client.connect(broker, broker_port)
client.loop_start()                    # Start loop to process received messages
client.subscribe(mysubscribe)

time_start = time.time()
print("Uploading file "+myfile+" to "+mytopic+" ...")

fo = open(myfile,"rb")
fo.seek(0, 2)  # os.SEEK_END
file_size = fo.tell()
fo.seek(0, 0)  # os.SEEK_SET

client.publish(mypublish, "{\"File\":\""+myfile+"\",\"Id\":"+str("%3d"%file_id)+",\"Type\":"+str(myfiletype)+",\"Size\":"+str(file_size)+"}")
Ack_flag = True

out_hash_md5 = hashlib.md5()

Run_flag = True
while Run_flag:
   if wait_for_ack():                   # We use Ack here
      Run_flag = False

   else:
      chunk = fo.read(file_chunk_size)
      if chunk:
         out_hash_md5.update(chunk)       # Update hash

#         base64_encoded_data = base64.b64encode(chunk)
#         base64_data = base64_encoded_data.decode('utf-8')
         # Message length used by Tasmota (FileTransferHeaderSize)
#         client.publish(mypublish, "{\"Id\":"+str("%3d"%file_id)+",\"Data\":\""+base64_data+"\"}")
         client.publish(mypublish+"201", chunk)
         Ack_flag = True

      else:
         md5_hash = out_hash_md5.hexdigest()
         client.publish(mypublish, "{\"Id\":"+str("%3d"%file_id)+",\"Md5\":\""+md5_hash+"\"}")
         Run_flag = False

fo.close()

time_taken = time.time() - time_start
print("Done in "+str("%.2f"%time_taken)+" seconds")

client.disconnect()                    # Disconnect
client.loop_stop()                     # Stop loop
