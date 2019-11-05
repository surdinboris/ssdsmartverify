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
           3: {"SSD-00017-A": "INTEL SSDSC2KB01"},
           4: {"SSD-00037-0": "INTEL SSDSC2KB019T801"},
           5: {"SSD-00042-0": "400-BDOD"},
           6: {"SSD-00110-A": "SATA 6G PM863A"},
           7: {"SSD-00111-A": "SAMSUNG MZ7LM1T9HMJP00005DJ"},
           8: {"SSD-00125-0": "SAMSUNG MZ7LH1T9HMLT-00005"},
           9: {"SSD-00139-0": "SAMSUNG MZ7LH7T6HMLA-00005"},
           10: {"SSD-00143-0": "SAMSUNG MZ7LH7T6HALA-00007"},
           11: {"HDD-TEST-01": "Hitachi HUA72101"}
           }
sysdrives=['/dev/sda', '/dev/sdb/', '/dev/sdc']

def start_verify(ssd_choice):
    errors=[]
    results=[]
    print("Starting verification for: " + "{} ({}) \n".format(list(ssd_pns[ssd_choice].keys())[0],
                                                                   list(ssd_pns[ssd_choice].values())[0]))
    logging.basicConfig(filename='ssd_verify_{}.log'.format(datetime.now().strftime("%d-%m-%Y-%H-%M")),
                        level=logging.DEBUG,
                        format='%(message)s')
    logging.info("Started verification {}".format(datetime.now().strftime("%d-%m-%Y-%H-%M"), list(ssd_pns[ssd_choice].keys())[0]))
    # required_ssd_attrs = [...]int{ 233 }
    # rows from iscsi
    re_lsscsi_local_drive_dev = re.compile(
        '^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(SAMSUNG|INTEL|PERC H710P|Hitachi|PERC H730 Mini|NDS-4600-JD)\s+(\w+)\s+(\w+)\s+(/dev/\w+)\s*$')
    
    # re_smart_attr foe smartctl
    re_smart_attr = re.compile(
        '^\s*([0-9]+)\s+([\w-]+)\s+([^\s]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^\s]+)\s+([0-9]+)(?:\s+)?(\(?:.+\))?$')
    #serial number
    re_serial_numb=re.compile('^Serial\s+Number:\s+(\w*)\s*$')

    #lsscsi
    lsscsi_scan = subprocess.run(["lsscsi"], stdout=subprocess.PIPE)
    lsscsi_decoded = [re_lsscsi_local_drive_dev.match(row) for row in lsscsi_scan.stdout.decode().split("\n")]

    filtered_ssd_devs = list(filter(lambda x: x != None, lsscsi_decoded))
    if debug:
        print(lsscsi_decoded)

    inconsist = {}
    def getdrivedata(ssd):
        #retrieving attributes
        device = ssd[5]
        slot = ssd[1]
        vendor = ssd[2]
        model = "{} {}".format(ssd[2], ssd[3])
        # filtering system drives
        if device in sysdrives:
            return
        #updating inconsistency data
        inconsist[model] = slot
        return {"device": device, "slot": slot, "vendor": vendor, "model": model}


    ssds = list(map(getdrivedata, filtered_ssd_devs))

    #filtering skipped system ssds
    ssds = list(filter(lambda x: x != None, ssds))

    #verifying ssds of the same pn (redundant with next verification, but makes things more clear)
    if len(inconsist) > 1:
        print(Fore.RED + "Error: found different models in one batch. Please check inconsistent data:")
        for key, value in inconsist.items():
            print(Fore.RED + "{} {}".format(key, value, ))
        print(Fore.RED + "SSD list:")
        for ssd in ssds:
            print(Fore.RED + "Slot: {}  Model: {}".format(ssd["slot"], ssd["model"], ))

    # checking ssds for valid PN
    for key, value in inconsist.items():
         if key != list(ssd_pns[ssd_choice].values())[0]:
            print(Fore.RED + "Error, wrong ssd model  for {} ( \"{}\" was found while should be \"{}\")".format(list(ssd_pns[ssd_choice].keys())[0],key, list(ssd_pns[ssd_choice].values())[0]))
            return

    print(Fore.GREEN + "Found {} devices \n".format(len(ssds)))
    # verify drives consistency


    # get smart atts
    for ssd in ssds:
        # subprocess part
        smart_atts = subprocess.run(["smartctl", "-x", ssd['device']], stdout=subprocess.PIPE)
        #processing output (filtering regex's None rows and getting capturing group data)
        smart_atts_matched = [re_smart_attr.match(row) for row in smart_atts.stdout.decode().split("\n")]
        serial_number_matched = [re_serial_numb.match(row) for row in smart_atts.stdout.decode().split("\n")]
        ssd['serial_number'] = list(filter(lambda x: x != None, serial_number_matched))[0][1]
        filtered_smart_atts = list(filter(lambda x: x != None, smart_atts_matched))
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
                                    "is_passed": is_passed}

                               )
    #final result record
    print('Scan Results:')
    print('-'*80)
    for result in results:
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
