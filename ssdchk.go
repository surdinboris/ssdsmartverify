package main

import (
	"fmt"
	"os"
	"os/exec"
	"bytes"
	"strings"
	"regexp"
	"strconv"
	"encoding/json"
	"sync"
	//"flag"
)

const (
	//media_wearout_indicator_smart_field = 233
	//crc_error_smart_field = 199
	//workload_minutes_smart_field = 228

	minimum_wearout_value = 95

	log_file = "/tmp/ssd_wearout.log"
)


var (
	//required_ssd_attrs = [...]int{ 233 }
	//re_lsscsi_local_drive_dev  = regexp.MustCompile(`^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(?:SAMSUNG|INTEL|PERC H710P).*\s+(/dev/\w+)\s*$`)
	re_lsscsi_local_drive_dev  = regexp.MustCompile(`^\[[0-9]+:[0-9]:([0-9]+):[0-9]\]\s+.*(?:SAMSUNG|INTEL|PERC H710P).*\s+(/dev/\w+)\s*$`)
	// smartctl -x
	re_smart_attr = regexp.MustCompile(`^\s*([0-9]+)\s+([\w-]+)\s+([^\s]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^\s]+)\s+([0-9]+)$`)
	// smartctl -aid sat+megaraid,N /dev/sda
	//re_smart_attr = regexp.MustCompile(`^\s*([0-9]+)\s+([\w-]+)\s+([^\s]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+([0-9]+)$`)
	re_smartctl_serial = regexp.MustCompile(`^Serial\sNumber:\s*(\w+)\s*$`)
	re_smartctl_model = regexp.MustCompile(`^(?:Device\sModel|Product):\s*(.*)$`)
	//re_dmidecode_cpu_model = regexp.MustCompile(`^\s*Version:\s.*\s(CPU\sE[^\s]+)\s.*\s*$`)
	re_dmidecode_cpu_model = regexp.MustCompile(`^\s*Version:\s.*\s(Gold 6142|CPU\sE[^\s]+)\s.*\s*$`)
)

//var re_lsscsi_local_drive_dev, re_smart_attr, re_smartctl_serial, re_smartctl_model, re_dmidecode_cpu_model *regexp.Regexp 

type smart_attribute struct {
	Id int `json:"id"`
	Name string `json:"name"`
	Flags string `json:"flags"`
	Value int `json:"value"`
	Worst int `json:"worst"`
	Threshold int `json:"threshold"`
	//Type string `json:"type"`
	//Updated string `json:"updated"`
	Fail string `json:"fail"`
	Raw_value uint64 `json:"raw_value"`
	Line string `json:"line"`
}

type local_drive struct {
	Device string `json:"device"`
	Slot int `json:"slot"`
	Attributes map[int]smart_attribute `json:"attributes"`
	Model string `json:"model"`
	Serial string `json:"serial"`
	Errors []string `json:"errors"`
	wearoutSmartAttribute int
	requiredSsdAttributes []int
}

func run_cmd(command string, args ...string) string {
	c := exec.Command(command, args...)
	var output bytes.Buffer
	c.Stdout = &output
	c.Stderr = &output
	c.Run()

	return output.String()
}

func get_server_model() string {
	lines := strings.Split(run_cmd("dmidecode"), "\n")
	var cpu_model string
	for _, line := range lines {
		if matches := re_dmidecode_cpu_model.FindStringSubmatch(line); len(matches) > 0 {
			cpu_model = matches[1]
			//fmt.Println(cpu_model)
			break
		}
	}

	var server_model string
	switch cpu_model {
	case "CPU E5-2697":
		server_model = "DELL_R730"
	case "CPU E5-2690":
		server_model = "DELL_R720"
	case "Gold 6142":
		server_model = "DELL_R740"	
	default:
		fmt.Println("Unrecognized CPU model.")
		//panic("Unrecognized CPU model.")
		//server_model = "DELL_R730"
	}

	return server_model
}

func requires_raid_reset() bool {
	return get_server_model() == "DELL_R720"
}

func is_in_detect_and_register() bool {
	hostname, err := os.Hostname()
	if err != nil {
		fmt.Println("panic is_in_detect_and_register")
		panic(err)
	}

	return hostname == "infiniconf" || hostname == "infiniconf2"
}

func reload_raid_config() string {
	/* the setup script copies `MegaCli' to /usr/bin
	var megacli string
	if is_in_detect_and_register() {
		megacli = "/mfg/hwconf/Mega_raid/MegaCli"
	} else {
		megacli = "MegaCli"
	}

	return run_cmd(megacli, "-CfgEachDskRaid0", "-a0")
	*/

	return run_cmd("MegaCli", "-CfgEachDskRaid0", "-a0")
}

func clear_foreign_ssd_configs() {
	run_cmd("MegaCli", "-CfgForeign", "-Clear", "-a0")
}

func (d *local_drive) isIntelSSD() bool {
	return d.Model == "INTEL SSDSC2BB016T4" || d.Model == "INTEL SSDSC2KB019T7"
}

func (d *local_drive) isSamsungSSD() bool {
	return d.Model == "SAMSUNG MZ7LM1T9HMJP-00005" || d.Model == "SAMSUNG MZ7LM3T8HMLP-00005" || d.Model == "SAMSUNG MZ7LH1T9HMLT-00005" 
}

func (d *local_drive) is_ssd() bool {
	return d.isIntelSSD() || d.isSamsungSSD()
}

func get_ssds() []local_drive {
	//fmt.Println("get_ssds")
	var ssds []local_drive
	output := run_cmd("lsscsi")
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if matches := re_lsscsi_local_drive_dev.FindStringSubmatch(line); len(matches) > 0 {
			//fmt.Println(matches[1])
			//fmt.Println(matches[2])
			var s local_drive
			s.Device = matches[2]
			s.Slot, _ = strconv.Atoi(matches[1])
			s.get_attributes()
			if s.is_ssd() {
				ssds = append(ssds, s)
			}
		}
	}
	//fmt.Println(ssds)
	return ssds
}

func (s *local_drive) get_attributes() {
	s.Attributes = make(map[int]smart_attribute)
	var output string
	// XXX: `smartctl -x /dev/sd[a-z]' doesn't work on iboxfru01-1.
	if get_server_model() != "DELL_R740" {
	output = run_cmd("smartctl", "-aid", fmt.Sprintf("sat+megaraid,%d", s.Slot), "/dev/sda")
	if strings.Contains(output, "Device Read Identity Failed") {
		output = run_cmd("smartctl", "-aid", fmt.Sprintf("megaraid,%d", s.Slot), "/dev/sda")
		}
	}else if get_server_model() == "DELL_R740"{
		output = run_cmd("smartctl", "-x",s.Device)
	}

	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if matches := re_smart_attr.FindStringSubmatch(line); len(matches) > 0 {
			var attr smart_attribute
			attr.Id, _ = strconv.Atoi(matches[1])
			attr.Name = matches[2]
			attr.Flags = matches[3]
			attr.Value, _ = strconv.Atoi(matches[4])
			attr.Worst, _ = strconv.Atoi(matches[5])
			attr.Threshold, _ = strconv.Atoi(matches[6])
			//attr.Type = matches[7]
			//attr.Updated = matches[8]
			attr.Fail = matches[7]
			attr.Raw_value, _ = strconv.ParseUint(matches[8], 10, 64)
			attr.Line = line
			s.Attributes[attr.Id] = attr
		} else if matches := re_smartctl_serial.FindStringSubmatch(line); len(matches) > 0 {
			s.Serial = matches[1]
		} else if matches := re_smartctl_model.FindStringSubmatch(line); len(matches) > 0 {
			s.Model = matches[1]
		}
	}

	if s.isIntelSSD() {
		s.wearoutSmartAttribute = 233
	} else if s.isSamsungSSD() {
		s.wearoutSmartAttribute = 177
	} else {
		s.wearoutSmartAttribute = -1
	}

	s.requiredSsdAttributes = []int{s.wearoutSmartAttribute}

	if s.Serial == "" || s.Model == "" {
		s.add_error("Failed to get the SSD's information")
	}
	for _, attr := range s.requiredSsdAttributes {
		if _, ok := s.Attributes[attr]; !ok {
			s.add_error(fmt.Sprintf("Failed to check Smart attribute %d", attr))
		}
	}
}

func (s *local_drive) add_error(err string) {
	s.Errors = append(s.Errors, err)
}

func print_json(j interface{}) {
	d, _ := json.MarshalIndent(j, "", "    ")
	fmt.Println(string(d))
}

func (s *local_drive) check_attributes() {
	for _, attr := range s.Attributes {
		switch attr.Id {
		case s.wearoutSmartAttribute:
			if attr.Value <= minimum_wearout_value {
				//fmt.Printf("SSD %d: Wrong value of '%s' - Expected '>%d', got '%d'.\n",
				//	   s.slot, attr.name, minimum_wearout_value, attr.value)
				s.add_error(fmt.Sprintf("Invalid wearout level (%d)", attr.Value))
			}
			break
		/*
		case crc_error_smart_field:
			//print_json(attr)
			//fmt.Println(attr.Raw_value)
			if attr.Raw_value > 0 {
				s.add_error("Invalid CRC value")
			}
			break
		case workload_minutes_smart_field:
			//print_json(attr)
			//fmt.Println(attr.Raw_value)
			if attr.Raw_value > 3783440327 {
				s.add_error("Invalid Workload_Minutes value")
			}
			break
		*/
		}
	}
}

func update_wear_log(ssd local_drive) {
	f, err := os.OpenFile(log_file, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
	if err != nil {
		panic(err)
	}

	defer f.Close()

	var status string
	if len(ssd.Errors) == 0 {
		status = "ACCEPT"
	} else {
		status = "REJECT"
	}
	line := fmt.Sprintf("%4d  %s   %s         %03d\n",
			    ssd.Slot, ssd.Serial, status,
			    ssd.Attributes[ssd.wearoutSmartAttribute].Value)
	if _, err = f.WriteString(line); err != nil {
		panic(err)
	}

	//fmt.Printf(status)
}

func main() {
   var wg sync.WaitGroup
   ssds := get_ssds()
   
   wg.Add(3)
   go func () {
	r, w, err := os.Pipe()
	if err != nil {
	    panic(err)
	}
	stdout := os.Stdout
	os.Stdout = w

	pager := exec.Command("less")
	pager.Stdin = r
	pager.Stdout = stdout
	pager.Stderr = os.Stderr

	defer func() {
		w.Close()
		if err := pager.Run(); err != nil {
			fmt.Fprintln(os.Stderr, err)
		}
		os.Stdout = stdout
	}()

	if requires_raid_reset() {
		reload_raid_config()
	}
	clear_foreign_ssd_configs()

	
	for _, ssd := range ssds {
		//fmt.Println("ssd exec")
		ssd.check_attributes()
		if len(ssd.Errors) == 0 {
			fmt.Printf("SSD ( S/N: %s) - Status: OK\n", ssd.Serial)
		} else {
			errs, _ := json.Marshal(ssd.Errors)
			fmt.Printf("SSD ( S/N: %s) - Status: FAILED.\n\tErrors: %s.\n\n",
				    ssd.Serial, errs)
		}
		
		update_wear_log(ssd)
		
	}
	wg.Done()
	}()
	go func () {fmt.Println("Total SSD's detected:", len(ssds))
	wg.Done()
	}()
	
	go func () {
	for true {
	for _, ssd := range ssds {
	//ssd.check_attributes()
	if len(ssd.Errors) != 0 {
	run_cmd("smartctl", "-x",ssd.Device)
		}
		}
	}
	wg.Done()
}()

wg.Wait()	
}
