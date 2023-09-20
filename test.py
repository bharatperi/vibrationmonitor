#Base board: Raspberry Pi Zero w
#accelerometer sensor: MMA8452Q
#Interface I2CS
from base64 import b64encode, b64decode
from hashlib import sha256
from urllib.parse import quote_plus, urlencode
from hmac import HMAC
import requests
import json
import os
import smbus
import time

# Azure IoT Hub
URI = 'vibrationtest.azure-devices.net'
KEY = '/99HeGpM6ZPFlkY7HMCyYS02NliZ2TpDuMMB5UilA7k='
IOT_DEVICE_ID = 'TestNode1'
POLICY = 'iothubowner'

def generate_sas_token():
    expiry=3600
    ttl = time.time() + expiry
    sign_key = "%s\n%d" % ((quote_plus(URI)), int(ttl))
    print(sign_key)
    signature = b64encode(HMAC(b64decode(KEY), sign_key, sha256).digest())

    rawtoken = {
        'sr' :  URI,
        'sig': signature,
        'se' : str(int(ttl))
    }

    rawtoken['skn'] = POLICY

    return 'SharedAccessSignature ' + urlencode(rawtoken)

def sensor():
    bus = smbus.SMBus(1)
    # MMA8452Q address, 0x1D(29)
    # Select Control register, 0x2A(42)
    #       0x00(00)    StandBy mode
    bus.write_byte_data(0x1D, 0x2A, 0x00)
    # Select Control register, 0x2A(42)
    #       0x01(01)    Active mode
    bus.write_byte_data(0x1D, 0x2A, 0x01)

    # Select Configuration register, 0x0E(14)
    #       0x00(00)    Set range to +/- 2g
    bus.write_byte_data(0x1D, 0x0E, 0x00)

    time.sleep(0.5)

    # Read data back from 0x00(0), 7 bytes
    # Status register, X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
    data = bus.read_i2c_block_data(0x1d, 0x00, 7)

    # Convert the data
    xAccl = (data[1] * 256 + data[2]) / 16
    if xAccl > 2047 :
            xAccl -= 4096
            yAccl = (data[3] * 256 + data[4]) / 16
            if yAccl > 2047 :
                    yAccl -= 4096

                    zAccl = (data[5] * 256 + data[6]) / 16
                    if zAccl > 2047 :
                        zAccl -= 4096
                        # Output data to screen
                        print ("Acceleration in X-Axis : %d" %xAccl)
                        print ("Acceleration in Y-Axis : %d" %yAccl)
                        print ("Acceleration in Z-Axis : %d" %zAccl)
    output = [xAccl, yAccl, zAccl]
    return output

def send_message(token, message):
	url = 'https://{0}/devices/{1}/messages/events?api-version=2016-11-14'.format(URI, IOT_DEVICE_ID)
    headers = {
        "Content-Type": "application/json",
        "Authorization": token
    }
    data = json.dumps(message)
    print data
    response = requests.post(url, data=data, headers=headers)

if __name__ == '__main__':
    # 1. Enable Temperature Sensor
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')

    # 2. Generate SAS Token
    token = generate_sas_token()

    # 3. Send Temperature to IoT Hub
    while True:
        result = sensor()
        message = { "result": str(result) }
        send_message(token, message)
        time.sleep(1)
