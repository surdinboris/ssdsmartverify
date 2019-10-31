ssds=[{'device': '/dev/sda', 'slot': '0', 'vendor': 'Hitachi', 'model': 'HUA72101'}]

for ssd in ssds:
    print("Slot: {}  Model: {}".format(ssd["slot"], ssd["model"], ))

dd={'Hitachi HUA72101': '0'}
