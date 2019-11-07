
import re
import os
#
# re_lsscsi_local_drive_dev = re.compile(
#     '^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(SAMSUNG|INTEL|Hitachi|Micron)\s+(\w+)\s+(\w+)\s+(/dev/\w+)\s*$')
# data='''[0:0:0:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sda
# [0:0:1:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdb
# [0:0:2:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdc
# [0:0:24:0]   enclosu DP       BP14G+EXP        2.25  -
# [0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde
# [0:0:131:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sdg
# [25:0:0:0]   disk    Kingston DataTraveler 3.0 PMAP  /dev/sdf
# '''
# datar="[0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde"
# print(re_lsscsi_local_drive_dev.match(datar))


scsi_addr= '/sys/class/scsi_disk/{}\:{}\:{}\:{}/device'

addr_seq =  "0:0:129:0".split(':')

drive_path = scsi_addr.format(*addr_seq)

tst_path = "/gitrep/ssdsmartverify/device_br/"

files = os.listdir(tst_path)
print(files)
#re_enc_path=re.compile('^enclosure_device:SLOT\s+(\d{1,2})\s+.*$')
re_enc_path=re.compile('^enclosure_device:SLOT\s+(\d{1,2})\s+.*$')

slot_matched = [re_enc_path.match(row) for row in files]

print(list(filter(lambda x: x != None, slot_matched)))

slot = list(filter(lambda x: x != None, slot_matched))[0][1]
print(slot)