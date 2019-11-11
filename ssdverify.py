import subprocess
import configparser
from datetime import *
import logging
from colorama import Fore, init as coloramainit
import re
import os
import json
coloramainit(autoreset=True)

def start_configuration():
    config = {}
    loaded_config = configparser.ConfigParser()
    loaded_config.read('ssdverify.ini')
    for item in ['DEBUG', 'ATTRIBUTES', 'PART NUMBERS']:
        if item not in loaded_config.sections():
            return create_default_ini()
    config['ssd_pns'] = dict(loaded_config['PART NUMBERS'])
    config['verif_attributes'] = dict(loaded_config['ATTRIBUTES'])
    # Decoding json-like ini subitems
    for item in config:
        for subitem in config[item]:
            string_value = config[item][subitem]
            json_ready_value = string_value.replace("\'", "\"")
            config[item][subitem] = json.loads(json_ready_value)
    #appending debug as non-subitem parameter
    config['debug'] = dict(loaded_config["DEBUG"])['debug']
    return config

def create_default_ini():
    print("\'ssdverify.ini\' not found, creating predefined configuration...")
    new_config = configparser.ConfigParser()
    debug = 0
    verif_attributes = {'INTEL': {'Media_Wearout_Indicator': 95},
                        'MICRON': {'Media_Wearout_Indicator': 95},
                        'SAMSUNG': {'Media_Wearout_Indicator': 95}}

    ssd_pns = {'1': {"SSD-00001-A": "MTFDDAK960MAV"},
               '2': {"SSD-00002-A": "INTEL SSDSC2BB016T401"},
               '3': {"SSD-00017-A": "INTEL SSDSC2KB019T7"},
               '4': {"SSD-00037-0": "INTEL SSDSC2KB019T801"},
               '5': {"SSD-00042-0": "400-BDOD"},
               '6': {"SSD-00110-A": "SATA 6G PM863A"},
               '7': {"SSD-00111-A": "SAMSUNG MZ7LM1T9HMJP00005DJ"},
               '8': {"SSD-00125-0": "SAMSUNG MZ7LH1T9HMLT-00005"},
               '9': {"SSD-00139-0": "SAMSUNG MZ7LH7T6HMLA-00005"},
               '10': {"SSD-00143-0": "SAMSUNG MZ7LH7T6HALA-00007"},
               }
    new_config['DEBUG'] = {'debug': '0'}
    new_config['ATTRIBUTES'] = verif_attributes
    new_config['PART NUMBERS'] = ssd_pns
    with open('ssdverify.ini', 'w') as configfile:
        new_config.write(configfile)
    return {debug: debug, 'ssd_pns': ssd_pns, 'verif_attributes': verif_attributes}


# IntelSSD wearoutSmartAttribute (233)
# SamsungSSD wearoutSmartAttribute(177)


# verif_attributes = {'INTEL':{'Media_Wearout_Indicator': 95},
#                     'Micron':{'Media_Wearout_Indicator': 95},
#                     'SAMSUNG':{'Media_Wearout_Indicator': 95}}
#
# ssd_pns = {1: {"SSD-00001-A": "MTFDDAK960MAV"},
#            2: {"SSD-00002-A": "INTEL SSDSC2BB016T401"},
#            3: {"SSD-00017-A": "INTEL SSDSC2KB019T7"},
#            4: {"SSD-00037-0": "INTEL SSDSC2KB019T801"},
#            5: {"SSD-00042-0": "400-BDOD"},
#            6: {"SSD-00110-A": "SATA 6G PM863A"},
#            7: {"SSD-00111-A": "SAMSUNG MZ7LM1T9HMJP00005DJ"},
#            8: {"SSD-00125-0": "SAMSUNG MZ7LH1T9HMLT-00005"},
#            9: {"SSD-00139-0": "SAMSUNG MZ7LH7T6HMLA-00005"},
#            10: {"SSD-00143-0": "SAMSUNG MZ7LH7T6HALA-00007"},
#            }


def start_verify(ssd_choice,config):
    config = start_configuration()
    ssd_pns=config['ssd_pns']
    verif_attributes = config['verif_attributes']
    debug=int(config['debug'])
    results=[]
    print("Starting verification for: " + "{} ({}) \n".format(list(ssd_pns[ssd_choice].keys())[0],
                                                                   list(ssd_pns[ssd_choice].values())[0]))
    logging.basicConfig(filename='ssd_verify_{}.log'.format(datetime.now().strftime("%d-%m-%Y-%H-%M")),
                        level=logging.DEBUG,
                        format='%(message)s')
    logging.info("Started verification {}".format(datetime.now().strftime("%d-%m-%Y-%H-%M"), list(ssd_pns[ssd_choice].keys())[0]))
    # rows from iscsi
    re_lsscsi_local_drive_dev = re.compile(
        '^\[([0-9]+:[0-9]:[0-9]+:[0-9])\]\s+.*(SAMSUNG|INTEL|Hitachi|Micron)\s+(\w+)\s+(\w+)\s+(/dev/\w+)\s*$')
    
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
        scsi_addr = '/sys/class/scsi_disk/{}:{}:{}:{}/device'
        addr_seq = sw_slot.split(':')
        files = os.listdir(scsi_addr.format(*addr_seq))
        re_enc_path = re.compile('^enclosure_device:SLOT\s+(\d{1,2})\s+.*$')
        slot_matched = [re_enc_path.match(row) for row in files]
        try:
            phy_slot = list(filter(lambda x: x != None, slot_matched))[0][1]
        except IndexError:
            phy_slot = "NA"
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

            attributes_for_check = verif_attributes[ssd['vendor'].lower()]
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
                                        "PN": ssd['model'],
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
            record = "SN: {0}, PN:{1} ({2}), Smart att: {3}, Allowed value >{4}, Drive value: {5}, Slot:{6}, Passed: {7}".format(
                result['serial_number'],
                result['PN'],
                list(ssd_pns[ssd_choice].keys())[0],
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
    if debug == 1:
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
        config = start_configuration()
        ssd_pns = config['ssd_pns']
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
                ssd_choice = input()
                tryout = ssd_pns[ssd_choice]
                break
            except (ValueError, KeyError):
                print("Enter a digit number from 1 to {} and press Enter\n".format(len(ssd_pns)))
        if ssd_pns.keys():
            print("\n")
            start_verify(ssd_choice,config)
        else:
            print('Please enter a valid choice')
        input("Press Enter to continue or ctrl-c to exit...")
        print("*" * 100)
