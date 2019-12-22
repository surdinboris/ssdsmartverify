import subprocess
import re
import os

ssds={"device": 'device', "slot": 'NA', "vendor": 'vendor'},{"device": 'device', "slot": 12, "vendor": 'vendor'}

def check_populated_slots(ssds):
    slot = 1
    unpopulated=[]
    while slot <= 60:
        ssdok=False
        for ssd in ssds:
            if(slot== 'NA'):
                break
            if (int(ssd['slot']) == slot):
                ssdok=True
                slot += 1
                break
        if (not ssdok):
            unpopulated.append(slot)
            slot += 1
    print(unpopulated)

def check_populated_slots2(ssds):
    #generating slots array
    slot = 1
    unpopulated = []
    while slot <= 60:
        unpopulated.append(slot)
    print(unpopulated)
    for ssd in ssds:
        unpopulated.index(ssd['slot'])
        
def failEn(slot, onOff):
    onOff = 1
    enclosure=os.listdir("/sys/class/enclosure/")
    if len(enclosure) > 1:
        print("Two scsi enclosures were found in /sys/class/enclosure/ "
              "that configuration wasn't tested, using first one {}".format(enclosure[0]))
    elif len(enclosure) < 1:
        raise IOError('No enclosures were found in /sys/class/enclosure/')
    encl_addr = (os.listdir("/sys/class/enclosure/")[0])
    slot = 11
    slot_ext = '0A'
    re_encl_slot = re.compile('^SLOT(\s{2}\d|\s\d{2})\s\w{2}\s{2}$')
    slotlist=(os.listdir("/sys/class/enclosure/{}/".format(encl_addr)))
    slotlist_decoded = [re_encl_slot.match(row) for row in slotlist]
    filtered_encl_slots = list(filter(lambda x: x != None, slotlist_decoded))
    sllots={}
    for slt in filtered_encl_slots:
        sllots[slt[1]] = slt[0]
    print(slotlist)


    #
    # print(subprocess.run(["ls /sys/class/enclosure/"], stdout=subprocess.PIPE))
    # echo_resp = subprocess.run(["echo {} > /sys/class/enclosure/{}/SLOT\ {}\ {}\ \ /fault"
    #                           .format(int(onOff), encl_addr, slot, slot_ext)], stdout=subprocess.PIPE)
    # valid = subprocess.run(["cat /sys/class/enclosure/{}/SLOT\ {}\ {}\ \ /fault"
    #                       .format(int(onOff), encl_addr, slot, slot_ext)], stdout=subprocess.PIPE)
    # print(valid == onOff)
    #

# echo 0 > /sys/class/enclosure/13\:0\:242\:0/SLOT\ 59\ 4A\ \ /fault


if __name__ == '__main__':
    #failEn(11, 1)
    check_populated_slots(ssds)