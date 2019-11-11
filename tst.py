import configparser
import json
def start_configuration():
    config = {}
    loaded_config = configparser.ConfigParser()
    loaded_config.read('ssdverify.ini')
    for item in ['DEBUG', 'ATTRIBUTES', 'PART NUMBERS']:
        if item not in loaded_config.sections():
            print('ssdverify.ini not found, creating predefined configuration')
            return create_default_ini()
    config['debug'] = dict(loaded_config["DEBUG"])
    config['ssd_pns'] = dict(loaded_config['PART NUMBERS'])
    config['verif_attributes'] = dict(loaded_config['ATTRIBUTES'])
    # Decoding json-like ini subitems
    for item in config:
        for subitem in config[item]:
            string_value = config[item][subitem]
            json_ready_value = string_value.replace("\'", "\"")
            config[item][subitem] = json.loads(json_ready_value)
    return config

def create_default_ini():
    print("creating daf")
    new_config = configparser.ConfigParser()
    debug = 0
    verif_attributes = {'INTEL': {'Media_Wearout_Indicator': 95},
                        'Micron': {'Media_Wearout_Indicator': 95},
                        'SAMSUNG': {'Media_Wearout_Indicator': 95}}

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
               }
    new_config['DEBUG'] = {'debug': False}

    new_config['ATTRIBUTES'] = verif_attributes

    new_config['PART NUMBERS'] = ssd_pns

    with open('ssdverify.ini', 'w') as configfile:
        new_config.write(configfile)
    return {debug: debug, 'ssd_pns': ssd_pns, 'verif_attributes': verif_attributes}

config = start_configuration()


# print(type(item))

# import configparser
#
#
# config = configparser.ConfigParser()
#
# loaded_config = config.read('ssdverify.ini')
# print(loaded_config)

#
# debug=False
# verif_attributes = {'INTEL':{'Media_Wearout_Indicator': 95},
#                     'Micron':{'Media_Wearout_Indicator': 95},
#                     'SAMSUNG':{'Media_Wearout_Indicator': 95}}
#
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
# config['DEBUG'] = {'debug':False}
#
#
# config['ATTRIBUTES'] = verif_attributes
#
# config['PART NUMBERS'] = ssd_pns
#
#
# with open('ssdverify.ini', 'w') as configfile:
#     config.write(configfile)

#
# import re
# import os
# #
# # re_lsscsi_local_drive_dev = re.compile(
# #     '^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(SAMSUNG|INTEL|Hitachi|Micron)\s+(\w+)\s+(\w+)\s+(/dev/\w+)\s*$')
# # data='''[0:0:0:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sda
# # [0:0:1:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdb
# # [0:0:2:0]    disk    SEAGATE  ST1200MM0099     ST31  /dev/sdc
# # [0:0:24:0]   enclosu DP       BP14G+EXP        2.25  -
# # [0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde
# # [0:0:131:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sdg
# # [25:0:0:0]   disk    Kingston DataTraveler 3.0 PMAP  /dev/sdf
# # '''
# # datar="[0:0:129:0]  disk    ATA      SAMSUNG MZ7LM1T9 404Q  /dev/sde"
# # print(re_lsscsi_local_drive_dev.match(datar))
#
#
# scsi_addr= '/sys/class/scsi_disk/{}\:{}\:{}\:{}/device'
#
# addr_seq =  "0:0:129:0".split(':')
#
# drive_path = scsi_addr.format(*addr_seq)
#
# tst_path = "/gitrep/ssdsmartverify/device_br/"
#
# files = os.listdir(tst_path)
# print(files)
# #re_enc_path=re.compile('^enclosure_device:SLOT\s+(\d{1,2})\s+.*$')
# re_enc_path=re.compile('^enclosure_device:SLOT\s+(\d{1,2})\s+.*$')
#
# slot_matched = [re_enc_path.match(row) for row in files]
#
# print(list(filter(lambda x: x != None, slot_matched)))
#
# slot = list(filter(lambda x: x != None, slot_matched))[0][1]
# print(slot)
