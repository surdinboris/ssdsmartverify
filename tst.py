
import re

re_lsscsi_local_drive_dev = re.compile(
    '^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(SAMSUNG|INTEL|Hitachi|Micron)\s+(\w+)\s+(\w+)\s+(/dev/\w+)\s*$')
data='''[0:0:0:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sda 
[0:0:1:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdb 
[0:0:2:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdc 
[0:0:24:0]   enclosu DP       BP14G+EXP        2.25  -        
[0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde 
[0:0:131:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sdg 
[25:0:0:0]   disk    Kingston DataTraveler 3.0 PMAP  /dev/sdf 
'''
datar="[0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde"
print(re_lsscsi_local_drive_dev.match(datar))