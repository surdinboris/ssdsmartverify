import subprocess
from datetime import *
import logging
from colorama import Fore, init as coloramainit
import re
import time
import os
coloramainit(autoreset=True)
debug = False

verif_attributes = {'INTEL':{'Media_Wearout_Indicator': 100},
                    'Hitachi': {"Reallocated_Event_Count": 100, "Current_Pending_Sector":110},
                    'Micron':{'Media_Wearout_Indicator': 100},
                    'SAMSUNG':{'Media_Wearout_Indicator': 100}}

ssd_pns = {1: {"SSD-00001-A": "MTFDDAK960MAV"},
           2: {"SSD-00002-A": "INTEL SSDSC2BB016T401"},
           3: {"SSD-00017-A": "INTEL SSDSC2KB019T7"},
           4: {"SSD-00037-0": "INTEL SSDSC2KB019T801"},
           5: {"SSD-00042-0": "400-BDOD"},
           6: {"SSD-00110-A": "SATA 6G PM863A"},
           7: {"SSD-00111-A": "SAMSUNG MZ7LM1T9HMJP00005DJ"},
           8: {"SSD-00125-0": "SAMSUNG MZ7LH1T9HMLT-00005"},
           9: {"SSD-00139-0": "SAMSUNG MZ7LH7T6HMLA-00005"},
           10: {"SSD-00143-0": "SAMSUNG MZ7LH7T6HALA-00007"},
           11: {"HDD-TEST-01": "Hitachi HUA72101"}
           }


def start_verify(ssd_choice):
    errors=[]
    results=[]
    print("Starting verification for: " + "{} ({}) \n".format(list(ssd_pns[ssd_choice].keys())[0],
                                                                   list(ssd_pns[ssd_choice].values())[0]))
    logging.basicConfig(filename='ssd_verify_{}.log'.format(datetime.now().strftime("%d-%m-%Y-%H-%M")),
                        level=logging.DEBUG,
                        format='%(message)s')
    logging.info("Started verification {}".format(datetime.now().strftime("%d-%m-%Y-%H-%M"), list(ssd_pns[ssd_choice].keys())[0]))
    # rows from iscsi
    re_lsscsi_local_drive_dev = re.compile(
        '^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(SAMSUNG|INTEL|Hitachi|Micron)\s+(\w+)\s+(\w+)\s+(/dev/\w+)\s*$')
    
    # re_smart_attr foe smartctl
    re_smart_attr = re.compile(
        '^\s*([0-9]+)\s+([\w-]+)\s+([^\s]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^\s]+)\s+([0-9]+)(?:\s+)?(\(?:.+\))?$')
    #serial number
    re_serial_numb=re.compile('^Serial\s+Number:\s+(\w*)\s*$')

    # model
    re_device_model=re.compile('^(?:Device\sModel|Product):\s*(.*)$')

    #lsscsi
    lsscsi_scan = subprocess.run(["lsscsi"], stdout=subprocess.PIPE)
    lsscsi_decoded = [re_lsscsi_local_drive_dev.match(row) for row in lsscsi_scan.stdout.decode().split("\n")]

    filtered_ssd_devs = list(filter(lambda x: x != None, lsscsi_decoded))
    if debug:
        print(lsscsi_decoded)

    def detect_phy_slot(sw_slot):

        scsi_addr = '/sys/class/scsi_disk/{}\:{}\:{}\:{}/device'

        addr_seq = sw_slot.split(':')

        files = os.listdir( scsi_addr.format(*addr_seq))

        re_enc_path = re.compile('^enclosure_device:SLOT\s+(\d{1,2})\s+.*$')

        slot_matched = [re_enc_path.match(row) for row in files]

        phy_slot = list(filter(lambda x: x != None, slot_matched))[0][1]

        return phy_slot


    def getdrivedata(ssd):
        #retrieving attributes
        device = ssd[5]
        #retrieving physical slot
        slot = detect_phy_slot(ssd[1])
        vendor = ssd[2] #possibly need to refactor for micron
        # model = "{} {}".format(ssd[2], ssd[3])
        return {"device": device, "slot": slot, "vendor": vendor}


    ssds = list(map(getdrivedata, filtered_ssd_devs))


    print(Fore.GREEN + "Found {} devices \n".format(len(ssds)))
    # verify drives consistency


    # get smart atts
    for ssd in ssds:
        # subprocess part
        smart_atts = subprocess.run(["smartctl", "-x", ssd['device']], stdout=subprocess.PIPE)
        #processing output (filtering regex's None rows and getting capturing group data)

        smart_atts_matched = [re_smart_attr.match(row) for row in smart_atts.stdout.decode().split("\n")]
        filtered_smart_atts = list(filter(lambda x: x != None, smart_atts_matched))

        serial_number_matched = [re_serial_numb.match(row) for row in smart_atts.stdout.decode().split("\n")]
        ssd['serial_number'] = list(filter(lambda x: x != None, serial_number_matched))[0][1]

        model_matched = [re_device_model.match(row) for row in smart_atts.stdout.decode().split("\n")]
        ssd['model'] = list(filter(lambda x: x != None, model_matched))[0][1]

        #check ssd model
        if ssd['model'] != list(ssd_pns[ssd_choice].values())[0]:
            ssd['failed'] = True
            ssd['PN_ok'] = False
            results.append({"serial_number": ssd['serial_number'],
                            "slot": ssd['slot'],
                            "is_passed": False,
                            "PN_ok": ssd['PN_ok'],
                            "wrong_PN_data": ssd['model']
                            }
                           )
            #not processing wearout since ssd has wrong PN
            continue

        else:
            ssd['PN_ok']=True
            # validation if smart attr was found for drive type
            attributes_for_check = verif_attributes[ssd['vendor']]
            for smart_att in filtered_smart_atts:
                attribute = smart_att[2]
                checking_value = int(smart_att[4])
                if attribute in attributes_for_check:
                    passing_value = attributes_for_check[attribute]
                    is_passed = checking_value >= passing_value
                    #updating ssd status in case of failure
                    if not is_passed:
                        ssd['failed']= True
                    results.append({"serial_number": ssd['serial_number'],
                                       "attribute": attribute,
                                        "passing_value": passing_value,
                                        "checking_value": checking_value,
                                        "slot": ssd['slot'],
                                        "is_passed": is_passed,
                                        "PN_ok": ssd['PN_ok'],}

                                   )
    #final result record
    print('Scan Results:')
    print('-'*80)
    for result in results:
        if not result['PN_ok']:
            record = "SN: {0}, Slot:{1} - wrong PN {2} when {3} was selected for validation "\
                .format(result['serial_number'],
                        result['slot'],
                        result['wrong_PN_data'],
                        list(ssd_pns[ssd_choice].values())[0])

        else:
            record = "SN: {0}, Smart att: {1}, Allowed value >{2}, Drive value: {3}, Slot:{4}, Passed: {5}".format(
                result['serial_number'],
                result['attribute'],
                result['passing_value'],
                result['checking_value'],
                result['slot'],
                result['is_passed']
            )

        #writing log
        logging.info(record)
        if result['is_passed']:
            print(Fore.GREEN + record)
        else:
            print(Fore.RED + record)
    print('-' * 80)
    # calculating failed/passed ssds
    failed=[]
    try:
        failed = list(filter(lambda x: x['failed'] == True, ssds))
    except KeyError:
        pass

    #debug
    if debug == True:
        print("*"*40,'Debug',"*"*40)
        for ssd in ssds:
            print(ssd)
        print("-"*40)
        for result in results:
            print(result)
        print('failed', failed)
        print("*" * 40, 'Debug',"*" * 40)

    #COLORING
    finish_color = Fore.GREEN
    if len(failed):
        finish_color = Fore.RED

    print(finish_color + "Process finished. Scanned {} drives, {} passed, {} failed.".format(len(ssds), len(ssds)-len(failed), len(failed)))


#starting
if __name__ == '__main__':
    while True:
        os.system('clear')
        print("\n")
        print("Available SSD type for verification:")
        print("-"*80)
        print("\n")
        for x, y in ssd_pns.items():
            print("{}: {} ({})".format(x,list(y.keys())[0],list(y.values())[0]))
        print("-"*80)
        print("\n")
        print("Choose SSD type(1-{}): \n".format(len(ssd_pns)))
        while True:
            try:
                ssd_choice = int(input())
                tryout = ssd_pns[ssd_choice]
                break
            except (ValueError, KeyError):
                print("Enter a digit number from 1 to {} and press Enter\n".format(len(ssd_pns)))
        if ssd_pns.keys():
            print("\n")
            start_verify(ssd_choice)
        else:
            print('Please enter a valid choice')
        input("Press Enter to continue or ctrl-c to exit...")
        print("*" * 100)


"""Slot detetection
lsscsi 

cd \sys\class\scsi_disk

0:2:0:0
13:0:4:0
13:0:8:0

cd  /sys/class/scsi_disk/13\:0\:6\:0/device


ls


block
bsg
driver
"enclosure_device:SLOT 12 0B  "
generic
power
scsi_device
scsi_disk
scsi_generic
subsystem
delete
device_blocked
device_busy
dh_state
eh_timeout
evt_capacity_change_reported
evt_inquiry_change_reported
evt_lun_change_reported
evt_media_change
evt_mode_parameter_change_reported
evt_soft_threshold_reached
inquiry
iocounterbits
iodone_cnt
ioerr_cnt
iorequest_cnt
modalias
model
queue_depth
queue_ramp_up_period
queue_type
rescan
rev
sas_address
sas_device_handle
scsi_level
state
timeout
type
uevent
unpriv_sgio
vendor
vpd_pg80
vpd_pg83
wwid












/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/block/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/bsg/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/driver/
"/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/enclosure_device:SLOT 12 0B  /"
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/generic/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/power/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/scsi_device/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/scsi_disk/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/scsi_generic/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/subsystem/
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/delete
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/device_blocked
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/device_busy
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/dh_state
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/eh_timeout
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/evt_capacity_change_reported
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/evt_inquiry_change_reported
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/evt_lun_change_reported
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/evt_media_change
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/evt_mode_parameter_change_reported
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/evt_soft_threshold_reached
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/inquiry
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/iocounterbits
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/iodone_cnt
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/ioerr_cnt
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/iorequest_cnt
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/modalias
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/model
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/queue_depth
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/queue_ramp_up_period
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/queue_type
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/rescan
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/rev
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/sas_address
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/sas_device_handle
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/scsi_level
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/state
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/timeout
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/type
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/uevent
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/unpriv_sgio
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/vendor
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/vpd_pg80
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/vpd_pg83
/sys/devices/pci0000:00/0000:00:03.2/0000:09:00.0/host13/port-13:1/expander-13:3/port-13:3:3/expander-13:5/port-13:5:1/end_device-13:5:1/target13:0:8/13:0:8:0/wwid


"""