import subprocess
from datetime import *
import logging
import re
now = datetime.now()
debug= True
verif_attributes = {'Hitachi': {"Reallocated_Event_Count": 100,"Current_Pending_Sector":100}}

#logging.basicConfig(filename='ssd_verify_{}.log'.format(now.strftime("%d-%m-%Y-%H-%M")),level=logging.DEBUG)

#required_ssd_attrs = [...]int{ 233 }
#rows from iscsi
re_lsscsi_local_drive_dev = re.compile('^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(SAMSUNG|INTEL|PERC H710P|Hitachi).*\s+(/dev/\w+)\s*$')

#re_smart_attr foe smartctl
re_smart_attr = re.compile('^\s*([0-9]+)\s+([\w-]+)\s+([^\s]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^\s]+)\s+([0-9]+)(?:\s+)?(\(?:.+\))?$')


# matching lsscsi
# fake data
# lsscsi_results = [re_lsscsi_local_drive_dev.match(row) for row in lsscsitest]

lsscsi_scan = subprocess.run(["lsscsi"], stdout=subprocess.PIPE)
lsscsi_decoded=[re_lsscsi_local_drive_dev.match(row) for row in lsscsi_scan.stdout.decode().split("\n")]

filtered_ssd_devs= list(filter(lambda x: x != None, lsscsi_decoded))

def getdrivedata(ssd):
    return {"device":ssd[3],"slot":ssd[1],"vendor":ssd[2]}

ssds=list(map(getdrivedata,filtered_ssd_devs))

print("Found {} devices".format(len(ssds)))

#get smart atts

for ssd in ssds:
    #subprocess part
    smart_atts = subprocess.run(["smartctl", "-x", ssd['device']], stdout=subprocess.PIPE)
    smart_atts_matched = [re_smart_attr.match(row) for row in smart_atts.stdout.decode().split("\n")]
    filtered_smart_atts = list(filter(lambda x: x != None, smart_atts_matched))
    #validation if smart attr was found for drive type
    attributes_for_check= verif_attributes[ssd['vendor']]
    for smart_att in filtered_smart_atts:
        attr_name= smart_att[2]
        value= smart_att[4]
        if attr_name in attributes_for_check:
            attr_passed = int(value) >= attributes_for_check[attr_name]
            print(attr_name, attr_passed)


        #print(list(map(lambda x: filtered_smart_atts[x] == smart_att[1] ,filtered_smart_atts)))

# #regex test
# for row in smartctltest.split("\n"):
#     print(row)
#     print(re_smart_attr.match(row))



lsscsitest="""[0:0:0:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sda
[0:0:1:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdb
[0:0:2:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdc
[0:0:24:0]   enclosu DP       BP14G+EXP        2.25  -
[0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde
[0:0:131:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sdg
[25:0:0:0]   disk    Kingston DataTraveler 3.0 PMAP  /dev/sdf""".split("\n")

smartctltest="""smartctl 6.5 2016-05-07 r4318 [x86_64-linux-3.10.0-693.el7.x86_64] (local build)
Copyright (C) 2002-16, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Device Model:     SAMSUNG MZ7LM1T9HMJP-00005
Serial Number:    S2TVNX0K604956
LU WWN Device Id: 5 002538 c40afd92b
Firmware Version: GXT5404Q
User Capacity:    1,920,383,410,176 bytes [1.92 TB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      2.5 inches
Device is:        Not in smartctl database [for details use: -P showall]
ATA Version is:   ACS-2, ATA8-ACS T13/1699-D revision 4c
SATA Version is:  SATA 3.1, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Wed Oct 30 02:49:35 2019 EDT
SMART support is: Available - device has SMART capability.
SMART support is: Enabled
AAM feature is:   Unavailable
APM feature is:   Disabled
Rd look-ahead is: Enabled
Write cache is:   Enabled
ATA Security is:  Disabled, NOT FROZEN [SEC1]
Wt Cache Reorder: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x02)	Offline data collection activity
					was completed without error.
					Auto Offline Data Collection: Disabled.
Self-test execution status:      (   0)	The previous self-test routine completed
					without error or no self-test has ever 
					been run.
Total time to complete Offline 
data collection: 		( 6000) seconds.
Offline data collection
capabilities: 			 (0x53) SMART execute Offline immediate.
					Auto Offline data collection on/off support.
					Suspend Offline collection upon new
					command.
					No Offline surface scan supported.
					Self-test supported.
					No Conveyance Self-test supported.
					Selective Self-test supported.
SMART capabilities:            (0x0003)	Saves SMART data before entering
					power-saving mode.
					Supports SMART auto save timer.
Error logging capability:        (0x01)	Error logging supported.
					General Purpose Logging supported.
Short self-test routine 
recommended polling time: 	 (   2) minutes.
Extended self-test routine
recommended polling time: 	 ( 100) minutes.
SCT capabilities: 	       (0x003d)	SCT Status supported.
					SCT Error Recovery Control supported.
					SCT Feature Control supported.
					SCT Data Table supported.

SMART Attributes Data Structure revision number: 1
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAGS    VALUE WORST THRESH FAIL RAW_VALUE
  5 Reallocated_Sector_Ct   PO--CK   100   100   010    -    0
  9 Power_On_Hours          -O--CK   098   098   000    -    7755
 12 Power_Cycle_Count       -O--CK   099   099   000    -    69
177 Wear_Leveling_Count     PO--C-   099   099   005    -    17
179 Used_Rsvd_Blk_Cnt_Tot   PO--C-   100   100   010    -    0
180 Unused_Rsvd_Blk_Cnt_Tot PO--C-   100   100   010    -    6511
181 Program_Fail_Cnt_Total  -O--CK   100   100   010    -    0
182 Erase_Fail_Count_Total  -O--CK   100   100   010    -    0
183 Runtime_Bad_Block       PO--C-   100   100   010    -    0
184 End-to-End_Error        PO--CK   100   100   097    -    0
187 Reported_Uncorrect      -O--CK   100   100   000    -    0
190 Airflow_Temperature_Cel -O--CK   074   065   000    -    26
194 Temperature_Celsius     -O---K   074   065   000    -    26 (Min/Max 18/35)
195 Hardware_ECC_Recovered  -O-RC-   200   200   000    -    0
197 Current_Pending_Sector  -O--CK   100   100   000    -    0
199 UDMA_CRC_Error_Count    -OSRCK   100   100   000    -    0
202 Unknown_SSD_Attribute   PO--CK   100   100   010    -    0
235 Unknown_Attribute       -O--C-   099   099   000    -    66
241 Total_LBAs_Written      -O--CK   099   099   000    -    50690640644
242 Total_LBAs_Read         -O--CK   099   099   000    -    22668938293
243 Unknown_Attribute       -O--CK   100   100   000    -    0
244 Unknown_Attribute       -O--CK   100   100   000    -    0
245 Unknown_Attribute       -O--CK   100   100   000    -    65535
246 Unknown_Attribute       -O--CK   100   100   000    -    65535
247 Unknown_Attribute       -O--CK   100   100   000    -    65535
251 Unknown_Attribute       -O--CK   100   100   000    -    62792359936
                            ||||||_ K auto-keep
                            |||||__ C event count
                            ||||___ R error rate
                            |||____ S speed/performance
                            ||_____ O updated online
                            |______ P prefailure warning

General Purpose Log Directory Version 1
SMART           Log Directory Version 1 [multi-sector log support]
Address    Access  R/W   Size  Description
0x00       GPL,SL  R/O      1  Log Directory
0x01           SL  R/O      1  Summary SMART error log
0x02           SL  R/O      1  Comprehensive SMART error log
0x03       GPL     R/O      1  Ext. Comprehensive SMART error log
0x04       GPL,SL  R/O      8  Device Statistics log
0x06           SL  R/O      1  SMART self-test log
0x07       GPL     R/O      1  Extended self-test log
0x08       GPL     R/O      2  Power Conditions log
0x09           SL  R/W      1  Selective self-test log
0x10       GPL     R/O      1  SATA NCQ Queued Error log
0x11       GPL     R/O      1  SATA Phy Event Counters log
0x13       GPL     R/O      1  SATA NCQ Send and Receive log
0x30       GPL,SL  R/O      9  IDENTIFY DEVICE data log
0x80-0x9f  GPL,SL  R/W     16  Host vendor specific log
0xa0       GPL     VS      16  Device vendor specific log
0xce           SL  VS      16  Device vendor specific log
0xe0       GPL,SL  R/W      1  SCT Command/Status
0xe1       GPL,SL  R/W      1  SCT Data Transfer

SMART Extended Comprehensive Error Log Version: 1 (1 sectors)
No Errors Logged

SMART Extended Self-test Log Version: 1 (1 sectors)
No self-tests have been logged.  [To run self-tests, use: smartctl -t]

SMART Selective self-test log data structure revision number 1
 SPAN  MIN_LBA  MAX_LBA  CURRENT_TEST_STATUS
    1        0        0  Not_testing
    2        0        0  Not_testing
    3        0        0  Not_testing
    4        0        0  Not_testing
    5        0        0  Not_testing
  255        0    65535  Read_scanning was completed without error
Selective self-test flags (0x0):
  After scanning selected spans, do NOT read-scan remainder of disk.
If Selective self-test is pending on power-up, resume after 0 minute delay.

SCT Status Version:                  3
SCT Version (vendor specific):       256 (0x0100)
SCT Support Level:                   1
Device State:                        SCT command executing in background (5)
Current Temperature:                    26 Celsius
Power Cycle Min/Max Temperature:     20/26 Celsius
Lifetime    Min/Max Temperature:     18/35 Celsius
Under/Over Temperature Limit Count:   0/0

SCT Temperature History Version:     2
Temperature Sampling Period:         1 minute
Temperature Logging Interval:        10 minutes
Min/Max recommended Temperature:      0/70 Celsius
Min/Max Temperature Limit:            0/70 Celsius
Temperature History Size (Index):    128 (76)

Index    Estimated Time   Temperature Celsius
  77    2019-10-29 05:30    25  ******
  78    2019-10-29 05:40    28  *********
  79    2019-10-29 05:50    26  *******
  80    2019-10-29 06:00    27  ********
  81    2019-10-29 06:10    28  *********
  82    2019-10-29 06:20    26  *******
  83    2019-10-29 06:30    28  *********
  84    2019-10-29 06:40    27  ********
  85    2019-10-29 06:50    27  ********
  86    2019-10-29 07:00    27  ********
  87    2019-10-29 07:10    25  ******
  88    2019-10-29 07:20    29  **********
  89    2019-10-29 07:30    24  *****
  90    2019-10-29 07:40    29  **********
  91    2019-10-29 07:50    25  ******
  92    2019-10-29 08:00    28  *********
  93    2019-10-29 08:10    26  *******
  94    2019-10-29 08:20    25  ******
  95    2019-10-29 08:30    28  *********
  96    2019-10-29 08:40    25  ******
  97    2019-10-29 08:50    28  *********
  98    2019-10-29 09:00    25  ******
  99    2019-10-29 09:10    28  *********
 100    2019-10-29 09:20    24  *****
 101    2019-10-29 09:30    29  **********
 102    2019-10-29 09:40    24  *****
 103    2019-10-29 09:50    29  **********
 104    2019-10-29 10:00    24  *****
 105    2019-10-29 10:10    29  **********
 106    2019-10-29 10:20    25  ******
 107    2019-10-29 10:30    27  ********
 108    2019-10-29 10:40    26  *******
 109    2019-10-29 10:50    26  *******
 110    2019-10-29 11:00    28  *********
 111    2019-10-29 11:10    26  *******
 112    2019-10-29 11:20    28  *********
 113    2019-10-29 11:30    27  ********
 114    2019-10-29 11:40    26  *******
 115    2019-10-29 11:50    28  *********
 116    2019-10-29 12:00    27  ********
 117    2019-10-29 12:10    27  ********
 118    2019-10-29 12:20    26  *******
 119    2019-10-29 12:30    26  *******
 120    2019-10-29 12:40    28  *********
 121    2019-10-29 12:50    24  *****
 122    2019-10-29 13:00    30  ***********
 123    2019-10-29 13:10    25  ******
 124    2019-10-29 13:20    29  **********
 125    2019-10-29 13:30    24  *****
 126    2019-10-29 13:40    29  **********
 127    2019-10-29 13:50    25  ******
   0    2019-10-29 14:00    28  *********
   1    2019-10-29 14:10    26  *******
   2    2019-10-29 14:20    27  ********
   3    2019-10-29 14:30    27  ********
   4    2019-10-29 14:40    25  ******
   5    2019-10-29 14:50    29  **********
   6    2019-10-29 15:00    25  ******
   7    2019-10-29 15:10    29  **********
   8    2019-10-29 15:20    24  *****
   9    2019-10-29 15:30    29  **********
  10    2019-10-29 15:40    25  ******
  11    2019-10-29 15:50    28  *********
  12    2019-10-29 16:00    27  ********
  13    2019-10-29 16:10    25  ******
  14    2019-10-29 16:20    28  *********
  15    2019-10-29 16:30    25  ******
  16    2019-10-29 16:40    29  **********
  17    2019-10-29 16:50    25  ******
  18    2019-10-29 17:00    28  *********
  19    2019-10-29 17:10    25  ******
  20    2019-10-29 17:20    29  **********
  21    2019-10-29 17:30    24  *****
  22    2019-10-29 17:40    29  **********
  23    2019-10-29 17:50    25  ******
  24    2019-10-29 18:00    27  ********
  25    2019-10-29 18:10    27  ********
  26    2019-10-29 18:20    26  *******
  27    2019-10-29 18:30    28  *********
  28    2019-10-29 18:40    25  ******
  29    2019-10-29 18:50    29  **********
  30    2019-10-29 19:00    24  *****
  31    2019-10-29 19:10    30  ***********
  32    2019-10-29 19:20    25  ******
  33    2019-10-29 19:30    28  *********
  34    2019-10-29 19:40    25  ******
  35    2019-10-29 19:50    27  ********
  36    2019-10-29 20:00    28  *********
  37    2019-10-29 20:10    25  ******
  38    2019-10-29 20:20    29  **********
  39    2019-10-29 20:30    24  *****
  40    2019-10-29 20:40    29  **********
  41    2019-10-29 20:50    25  ******
  42    2019-10-29 21:00    28  *********
  43    2019-10-29 21:10    26  *******
  44    2019-10-29 21:20    27  ********
  45    2019-10-29 21:30    28  *********
  46    2019-10-29 21:40    25  ******
  47    2019-10-29 21:50    29  **********
  48    2019-10-29 22:00    25  ******
  49    2019-10-29 22:10    27  ********
  50    2019-10-29 22:20    27  ********
  51    2019-10-29 22:30    26  *******
  52    2019-10-29 22:40    28  *********
  53    2019-10-29 22:50    25  ******
  54    2019-10-29 23:00    29  **********
  55    2019-10-29 23:10    25  ******
  56    2019-10-29 23:20    26  *******
  57    2019-10-29 23:30    28  *********
  58    2019-10-29 23:40    25  ******
  59    2019-10-29 23:50    28  *********
  60    2019-10-30 00:00    26  *******
  61    2019-10-30 00:10    26  *******
  62    2019-10-30 00:20    26  *******
  63    2019-10-30 00:30    25  ******
  64    2019-10-30 00:40    28  *********
  65    2019-10-30 00:50    25  ******
  66    2019-10-30 01:00    29  **********
  67    2019-10-30 01:10    24  *****
  68    2019-10-30 01:20    29  **********
  69    2019-10-30 01:30    24  *****
  70    2019-10-30 01:40    28  *********
  71    2019-10-30 01:50    25  ******
  72    2019-10-30 02:00    28  *********
  73    2019-10-30 02:10    22  ***
  74    2019-10-30 02:20     ?  -
  75    2019-10-30 02:30    27  ********
  76    2019-10-30 02:40     ?  -

SCT Error Recovery Control:
           Read: Disabled
          Write: Disabled

Device Statistics (GP Log 0x04)
Page  Offset Size        Value Flags Description
0x01  =====  =               =  ===  == General Statistics (rev 1) ==
0x01  0x008  4              69  ---  Lifetime Power-On Resets
0x01  0x010  4            7755  ---  Power-on Hours
0x01  0x018  6     50690640644  ---  Logical Sectors Written
0x01  0x020  6       372727331  ---  Number of Write Commands
0x01  0x028  6     22668938293  ---  Logical Sectors Read
0x01  0x030  6       363156023  ---  Number of Read Commands
0x01  0x038  6         2951000  ---  Date and Time TimeStamp
0x04  =====  =               =  ===  == General Errors Statistics (rev 1) ==
0x04  0x008  4               0  ---  Number of Reported Uncorrectable Errors
0x04  0x010  4               0  ---  Resets Between Cmd Acceptance and Completion
0x05  =====  =               =  ===  == Temperature Statistics (rev 1) ==
0x05  0x008  1              26  ---  Current Temperature
0x05  0x020  1              35  ---  Highest Temperature
0x05  0x028  1              18  ---  Lowest Temperature
0x05  0x058  1              70  ---  Specified Maximum Operating Temperature
0x06  =====  =               =  ===  == Transport Statistics (rev 1) ==
0x06  0x008  4              24  ---  Number of Hardware Resets
0x06  0x010  4               0  ---  Number of ASR Events
0x06  0x018  4               0  ---  Number of Interface CRC Errors
0x07  =====  =               =  ===  == Solid State Device Statistics (rev 1) ==
0x07  0x008  1               0  N--  Percentage Used Endurance Indicator
                                |||_ C monitored condition met
                                ||__ D supports DSN
                                |___ N normalized value

SATA Phy Event Counters (GP Log 0x11)
ID      Size     Value  Description
0x0001  2            0  Command failed due to ICRC error
0x0002  2            0  R_ERR response for data FIS
0x0003  2            0  R_ERR response for device-to-host data FIS
0x0004  2            0  R_ERR response for host-to-device data FIS
0x0005  2            0  R_ERR response for non-data FIS
0x0006  2            0  R_ERR response for device-to-host non-data FIS
0x0007  2            0  R_ERR response for host-to-device non-data FIS
0x0008  2            0  Device-to-host non-data FIS retries
0x0009  2            1  Transition from drive PhyRdy to drive PhyNRdy
0x000a  2            1  Device-to-host register FISes sent due to a COMRESET
0x000b  2            0  CRC errors within host-to-device FIS
0x000d  2            0  Non-CRC errors within host-to-device FIS
0x000f  2            0  R_ERR response for host-to-device data FIS, CRC
0x0010  2            0  R_ERR response for host-to-device data FIS, non-CRC
0x0012  2            0  R_ERR response for host-to-device non-data FIS, CRC
0x0013  2            0  R_ERR response for host-to-device non-data FIS, non-CRC"""
