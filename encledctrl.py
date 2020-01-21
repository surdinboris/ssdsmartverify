# import subprocess
import re
import os
# import shlex
# ssds=[{"device": 'device', "slot": 'NA', "vendor": 'vendor'},{"device": 'device', "slot": 12, "vendor": 'vendor'}]

def get_all_slots():
    # generating unpopulated slots array
    slot = 1
    unpopulated = []
    while slot <= 60:
        unpopulated.append(slot)
        slot += 1
    return unpopulated

def check_populated_slots(ssds):
    #generating unpopulated slots array
    slot = 1
    unpopulated = []
    while slot <= 60:
        unpopulated.append(slot)
        slot+=1
    for ssd in ssds:
        if (ssd['slot'] == 'NA'):
            continue
        # ind=unpopulated.index(ssd['slot'])
        unpopulated.pop(unpopulated.index(int(ssd['slot'])))
    return unpopulated

def get_failure_slots(ssds):
    failed=[]
    for ssd in ssds:
        failed.append(int(ssd['slot']))
    return failed

def led_ctrl(encslots, onOfflikr):
    action = 0
    if onOfflikr == 'on':
        action=1
    elif onOfflikr == 'off':
        action = 0
    elif onOfflikr == 'flikrOn':
        action = 1
    elif onOfflikr == 'flikrOff':
        action = 0

    #alarm led type on = 1 off = 0
    enclosure = os.listdir("/sys/class/enclosure/")
    if len(enclosure) > 1:
        print("Two scsi enclosures were found in /sys/class/enclosure/ "
              "that configuration wasn't tested, using first one {}".format(enclosure[0]))
    elif len(enclosure) < 1:
        raise IOError('No enclosures were found in /sys/class/enclosure/')
    encl_addr = (os.listdir("/sys/class/enclosure/")[0])
    re_encl_slot = re.compile('^SLOT(\s{2}\d|\s\d{2})\s\w{2}\s{2}$')
    allslotlist=(os.listdir("/sys/class/enclosure/{}/".format(encl_addr)))
    allslotlist_decoded = [re_encl_slot.match(row) for row in allslotlist]
    filtered_encl_slots = list(filter(lambda x: x != None, allslotlist_decoded))
    slots={}
    for slt in filtered_encl_slots:
        slots[int(slt[1].strip())] = slt[0]
    # print(slots)
    for unpopslot in encslots:
        # print(str(onOff))
        ledpath = 'na'
        if onOfflikr == 'on' or onOfflikr == 'off':
            ledpath = "/sys/class/enclosure/{}/{}/fault".format(encl_addr, slots[unpopslot])
        elif onOfflikr == 'flikrOn' or onOfflikr == 'flikrOff':
            ledpath = "/sys/class/enclosure/{}/{}/locate".format(encl_addr, slots[unpopslot])
        file = open(ledpath, 'w')
        file.write(str(action))
        file.close()

# echo 0 > /sys/class/enclosure/13\:0\:242\:0/SLOT\ 59\ 4A\ \ /fault

# if __name__ == '__main__':
#     unpopulated = check_populated_slots(ssds)
#     ledCtrl(unpopulated, 1)