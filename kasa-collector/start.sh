#!/bin/bash

##
## Kasa Collector - start-kasa-collector.sh
##

##
## Includes TP-Link Wifi SmartPlug Client
## https://github.com/softScheck/tplink-smartplug
##

##
## Functions
##

##
## ┌─┐┌─┐┌─┐┌─┐┌─┐┌─┐    ┌┐┌┌─┐┌┬┐┌─┐┌─┐
## ├┤ └─┐│  ├─┤├─┘├┤     │││├─┤│││├┤ └─┐
## └─┘└─┘└─┘┴ ┴┴  └─┘────┘└┘┴ ┴┴ ┴└─┘└─┘
##

function escape_device_alias {

##
## Spaces
##

device_alias_escaped="${alias// /\\ }"

##
## Commas
##

device_alias_escaped="${device_alias_escaped//,/\\,}"

##
## Equal Signs
##

device_alias_escaped="${device_alias_escaped//=/\\=}"

}

function escape_plug_alias {

##
## Spaces
##

plug_alias_escaped="${plug_alias// /\\ }"

##
## Commas
##

plug_alias_escaped="${plug_alias_escaped//,/\\,}"

##
## Equal Signs
##

plug_alias_escaped="${plug_alias_escaped//=/\\=}"

}

##
## Set Variables from Environmental Variables
##

collect_interval=$KASA_COLLECTOR_COLLECT_INTERVAL
debug=$KASA_COLLECTOR_DEBUG
debug_curl=$KASA_COLLECTOR_DEBUG_CURL
debug_sleeping=$KASA_COLLECTOR_DEBUG_SLEEPING
device_host=$KASA_COLLECTOR_DEVICE_HOST
host_hostname=$KASA_COLLECTOR_HOST_HOSTNAME
influxdb_password=$KASA_COLLECTOR_INFLUXDB_PASSWORD
influxdb_url=$KASA_COLLECTOR_INFLUXDB_URL
influxdb_username=$KASA_COLLECTOR_INFLUXDB_USERNAME

echo "
:::    :::     :::      ::::::::      :::                                                        
:+:   :+:    :+: :+:   :+:    :+:   :+: :+:                                                      
+:+  +:+    +:+   +:+  +:+         +:+   +:+                                                     
+#++:++    +#++:++#++: +#++:++#++ +#++:++#++:                                                    
+#+  +#+   +#+     +#+        +#+ +#+     +#+                                                    
#+#   #+#  #+#     #+# #+#    #+# #+#     #+#                                                    
###    ### ###     ###  ########  ###     ###                                                    
 ::::::::   ::::::::  :::        :::        :::::::::: :::::::: ::::::::::: ::::::::  :::::::::  
:+:    :+: :+:    :+: :+:        :+:        :+:       :+:    :+:    :+:    :+:    :+: :+:    :+: 
+:+        +:+    +:+ +:+        +:+        +:+       +:+           +:+    +:+    +:+ +:+    +:+ 
+#+        +#+    +:+ +#+        +#+        +#++:++#  +#+           +#+    +#+    +:+ +#++:++#:  
+#+        +#+    +#+ +#+        +#+        +#+       +#+           +#+    +#+    +#+ +#+    +#+ 
#+#    #+# #+#    #+# #+#        #+#        #+#       #+#    #+#    #+#    #+#    #+# #+#    #+# 
 ########   ########  ########## ########## ########## ########     ###     ########  ###    ### 
"

echo "$(date) - Starting Kasa Collector (start.sh) - https://github.com/lux4rd0/kasa-collector"

##
## Turn list of hosts into an array to loop
##

OLDIFS=$IFS
IFS=','; set -f
device_host_array=($device_host)

echo "Device(s): ${device_host_array[*]}"

##
## Set Specific Variables
##

if [ "$debug" == "true" ]

then

echo "
Debug Environmental Variables

collect_interval=${collect_interval}
debug=${debug}
debug_curl=${debug_curl}
debug_sleeping=${debug_sleeping}
device_host=${device_host}
host_hostname=${host_hostname}
influxdb_password=${influxdb_password}
influxdb_url=${influxdb_url}
influxdb_username=${influxdb_username}"

fi

##
## Check for required intervals
##

if [ -z "${collect_interval}" ]; then echo "$(date) - KASA_COLLECTOR_COLLECT_INTERVAL environmental variable not set. Defaulting to every second."; collect_interval="1"; export KASA_COLLECTOR_COLLECT_INTERVAL="1"; fi

if [ -z "${host_hostname}" ]; then echo "$(date) - KASA_COLLECTOR_HOST_HOSTNAME environmental variable not set. Defaulting to kasa-collector."; host_hostname="kasa-collector"; export KASA_COLLECTOR_HOST_HOSTNAME="kasa-collector"; fi

##
## Curl Command
##

if [ "$debug_curl" == "true" ]; then curl=(  ); else curl=( --silent --output /dev/null --show-error --fail ); fi

##
## Start Kasa Collector Loop
##

while ( true ); do

before=$(date +%s%N)

##
## Loop Through Device List
##

i=0

for device in "${device_host_array[@]}"; do

##
## Check that we get a good response back from the device. If not, retry.
##

while true; do

if [ "$debug" == "true" ]; then echo "kasa_request_info: fetching ${device}"; fi

kasa_request_info=$(./tplink_smartplug.py -t "${device}" -c info -q)

if [[ $kasa_request_info =~ }}} ]]; then

if [ "$debug" == "true" ]; then echo "kasa_request_info: good pull"; fi

break

fi

echo "kasa_request_info: malformed JSON, retrying"

if [ "$debug" == "true" ]; then  echo "${kasa_request_info}"; fi

done

##                           
##  _   _ ____ _____  ___   ___  
## | | | / ___|___ / / _ \ / _ \ 
## | |_| \___ \ |_ \| | | | | | |
## |  _  |___) ___) | |_| | |_| |
## |_| |_|____|____/ \___/ \___/ 
##                              

if [[ $kasa_request_info == *"HS300"* ]]; then

if [ "$debug" == "true" ]; then echo "device is HS300"; fi

eval "$(echo "${kasa_request_info}" | jq -r '.system.get_sysinfo | {"sw_ver", "hw_ver", "model", "deviceId", "oemId", "hwId", "rssi", "alias", "status", "mic_type", "mac", "updating", "led_off"} | to_entries | .[] | .key + "=" + "\"" + ( .value|tostring ) + "\""')"

if [ "$debug" == "true" ]; then

echo "
sw_ver=${sw_ver}
hw_ver=${hw_ver}
model=${model}
deviceId=${deviceId}
oemId=${oemId}
hwId=${hwId}
rssi=${rssi}
alias=${alias}
status=${status}
obd_src=${obd_src}
mic_type=${mic_type}
mac=${mac}
updating=${updating}
led_off=${led_off}"

fi

##
## Escape Device Alias (Function)
##

escape_device_alias

##
## Check that we get a good response back from the device. If not, retry.
##

while true; do

if [ "$debug" == "true" ]; then echo "kasa_request_energy: fetching ${device}"; fi

kasa_request_energy=$(./tplink_smartplug.py -t "${device}" -c energy -q)

if [[ $kasa_request_energy =~ }}} ]]; then
if [ "$debug" == "true" ]; then echo "kasa_request_energy: good pull"; fi
break
fi
echo "kasa_request_energy: malformed JSON, retrying"

if [ "$debug" == "true" ]; then  echo "${kasa_request_info}"; fi
done

eval "$(echo "${kasa_request_energy}" | jq -r '.emeter.get_realtime | to_entries | .[] | .key + "=" + "\"" + ( .value|tostring ) + "\""')"

if [ "$debug" == "true" ]; then

echo "
current_ma=${current_ma}
voltage_mv=${voltage_mv}
power_mw=${power_mw}
total_wh=${total_wh}
err_code=${err_code}"

fi

curl_message="kasa_energy,device_alias=${device_alias_escaped},device_hostname=${device} "

if [ -n "${current_ma}" ]; then curl_message="${curl_message}current_ma=${current_ma},"; else echo "current_ma is null"; fi
if [ -n "${voltage_mv}" ]; then curl_message="${curl_message}voltage_mv=${voltage_mv},"; else echo "voltage_mv is null"; fi
if [ -n "${power_mw}" ]; then curl_message="${curl_message}power_mw=${power_mw},"; else echo "power_mw is null"; fi
if [ -n "${total_wh}" ]; then curl_message="${curl_message}total_wh=${current_ma},"; else echo "total_wh is null"; fi
if [ -n "${err_code}" ]; then curl_message="${curl_message}err_code=${err_code},"; else echo "err_code is null"; fi
if [ -n "${rssi}" ]; then curl_message="${curl_message}rssi=${rssi},"; else echo "rssi is null"; fi
if [ -n "${sw_ver}" ]; then curl_message="${curl_message}sw_ver=\"${sw_ver}\","; else echo "sw_ver is null"; fi
if [ -n "${hw_ver}" ]; then curl_message="${curl_message}hw_ver=\"${hw_ver}\","; else echo "hw_ver is null"; fi
if [ -n "${model}" ]; then curl_message="${curl_message}model=\"${model}\","; else echo "model is null"; fi
if [ -n "${deviceId}" ]; then curl_message="${curl_message}deviceId=\"${deviceId}\","; else echo "deviceId is null"; fi
if [ -n "${oemId}" ]; then curl_message="${curl_message}oemId=\"${oemId}\","; else echo "oemId is null"; fi
if [ -n "${hwId}" ]; then curl_message="${curl_message}hwId=\"${hwId}\","; else echo "hwId is null"; fi
if [ -n "${status}" ]; then curl_message="${curl_message}status=\"${status}\","; else echo "status is null"; fi

if [ -n "${host_hostname}" ]; then curl_message="${curl_message}host_hostname=\"${host_hostname}\","; else echo "host_hostname is null"; fi
#if [ -n "${device}" ]; then curl_message="${curl_message}device_hostname=\"${device}\","; else echo "device is null"; fi
#if [ -n "${alias}" ]; then curl_message="${curl_message}device_alias=\"${alias}\","; else echo "device_alias is null"; fi

##
## Remove a trailing comma in curl_message if the last element happens to be null (so that there's still a properly formatted InfluxDB mmessage)
##

curl_message="$(echo "${curl_message}" | sed 's/,$//')"

if [ "$debug" == "true" ]; then

echo "${curl_message}"

fi

/usr/bin/timeout -k 1 10s curl "${curl[@]}" --connect-timeout 2 --max-time 2 --retry 5 --retry-delay 0 --retry-max-time 30 -i -XPOST "${influxdb_url}" -u "${influxdb_username}":"${influxdb_password}" --data-binary "${curl_message}" &

##
## Children
##

IFS=$OLDIFS; set -f

number_of_plugs=$(echo "${kasa_request_info}" | jq -r .system.get_sysinfo.child_num)
#number_of_plugs=6
#echo "${kasa_request_info}"
#echo "$(date) - number_of_plugs: ${number_of_plugs}"

number_of_plugs_minus_one=$((number_of_plugs-1))

for plug_number in $(seq 0 $number_of_plugs_minus_one); do

plug_id[$plug_number]=$(echo "${kasa_request_info}" | jq -r '.system.get_sysinfo.children['"${plug_number}"'].id')
plug_state[$plug_number]=$(echo "${kasa_request_info}" | jq -r '.system.get_sysinfo.children['"${plug_number}"'].state')
plug_alias[$plug_number]=$(echo "${kasa_request_info}" | jq -r '.system.get_sysinfo.children['"${plug_number}"'].alias')
plug_on_time[$plug_number]=$(echo "${kasa_request_info}" | jq -r '.system.get_sysinfo.children['"${plug_number}"'].on_time')

#plug_id[${plug_number}]=$(echo "${kasa_request_info}")

#plug_id[$plug_number]=$(echo "${kasa_request_info}" | jq -r .system.get_sysinfo.children[$plug_number].id)

#echo "plug_number=${plug_number}"

#echo "plug_number=${plug_number} - plug_id=${plug_id[$plug_number]}"
#echo "plug_number=${plug_number} - plug_state=${plug_state[$plug_number]}"
#echo "plug_number=${plug_number} - plug_alias=${plug_alias[$plug_number]}"
#echo "plug_number=${plug_number} - plug_on_time=${plug_on_time[$plug_number]}"

plug_alias=${plug_alias[$plug_number]}

##
## Escape Plug Alias (Function)
##

escape_plug_alias

kasa_request_energy[$plug_number]=$(./tplink_smartplug.py -t "${device}" -j '{"context":{"child_ids":["'"${plug_id[$plug_number]}"'"]},"emeter":{"get_realtime":{}}}' -q )

if [ "$debug" == "true" ]; then

echo "plug_number=${plug_number} - kasa_request_energy=${kasa_request_energy[$plug_number]}"

fi

eval "$(echo "${kasa_request_energy[$plug_number]}" | jq -r '.emeter.get_realtime | to_entries | .[] | .key + "=" + "\"" + ( .value|tostring ) + "\""')"

if [ "$debug" == "true" ]; then

echo "
current_ma=${current_ma}
voltage_mv=${voltage_mv}
power_mw=${power_mw}
total_wh=${total_wh}
err_code=${err_code}"

fi

curl_message="kasa_energy,device_alias=${device_alias_escaped},device_hostname=${device},plug_alias=${plug_alias_escaped} "

if [ -n "${current_ma}" ]; then curl_message="${curl_message}current_ma=${current_ma},"; else echo "current_ma is null"; fi
if [ -n "${voltage_mv}" ]; then curl_message="${curl_message}voltage_mv=${voltage_mv},"; else echo "voltage_mv is null"; fi
if [ -n "${power_mw}" ]; then curl_message="${curl_message}power_mw=${power_mw},"; else echo "power_mw is null"; fi
if [ -n "${total_wh}" ]; then curl_message="${curl_message}total_wh=${current_ma},"; else echo "total_wh is null"; fi
if [ -n "${err_code}" ]; then curl_message="${curl_message}err_code=${err_code},"; else echo "err_code is null"; fi

##
## Remove a trailing comma in curl_message if the last element happens to be null (so that there's still a properly formatted InfluxDB mmessage)
##

curl_message="$(echo "${curl_message}" | sed 's/,$//')"

if [ "$debug" == "true" ]; then echo "${curl_message}"; fi

/usr/bin/timeout -k 1 10s curl "${curl[@]}" --connect-timeout 2 --max-time 2 --retry 5 --retry-delay 0 --retry-max-time 30 -i -XPOST "${influxdb_url}" -u "${influxdb_username}":"${influxdb_password}" --data-binary "${curl_message}" &

done

fi

##                   
##  _  ______  _ _ ____  
## | |/ |  _ \/ / | ___| 
## | ' /| |_) | | |___ \ 
## | . \|  __/| | |___) |
## |_|\_|_|   |_|_|____/                  
##

if [[ $kasa_request_info == *"KP115"* ]]; then

if [ "$debug" == "true" ]; then echo "device is KP115"; fi

eval "$(echo "${kasa_request_info}" | jq -r '.system.get_sysinfo | {"sw_ver", "hw_ver", "model", "deviceId", "oemId", "hwId", "rssi", "alias", "status", "obd_src", "mic_type", "mac", "updating", "led_off", "relay_state", "on_time", "dev_name", "active_mode", "ntc_state", "err_code"} | to_entries | .[] | .key + "=" + "\"" + ( .value|tostring ) + "\""')"

if [ "$debug" == "true" ]; then

echo "sw_ver=${sw_ver}
hw_ver=${hw_ver}
model=${model}
deviceId=${deviceId}
oemId=${oemId}
hwId=${hwId}
rssi=${rssi}
alias=${alias}
status=${status}
obd_src=${obd_src}
mic_type=${mic_type}
mac=${mac}
updating=${updating}
led_off=${led_off}
relay_state=${relay_state}
on_time=${on_time}
dev_name=${dev_name}
active_mode=${active_mode}
ntc_state=${ntc_state}
err_code=${err_code}"

fi

##
## Escape Alias (Function)
##

escape_device_alias

##
## Check that we get a good response back from the device. If not, retry.
##

while true; do

if [ "$debug" == "true" ]; then echo "kasa_request_energy: fetching ${device}"; fi

kasa_request_energy=$(./tplink_smartplug.py -t "${device}" -c energy -q)

if [[ $kasa_request_energy =~ }}} ]]; then
if [ "$debug" == "true" ]; then echo "kasa_request_energy: good pull"; fi

break

fi

echo "kasa_request_energy: malformed JSON, retrying"

if [ "$debug" == "true" ]; then  echo "${kasa_request_info}"; fi

done

eval "$(echo "${kasa_request_energy}" | jq -r '.emeter.get_realtime | to_entries | .[] | .key + "=" + "\"" + ( .value|tostring ) + "\""')"

if [ "$debug" == "true" ]; then

echo "current_ma=${current_ma}
voltage_mv=${voltage_mv}
power_mw=${power_mw}
total_wh=${total_wh}
err_code=${err_code}"

fi

curl_message="kasa_energy,device_alias=${device_alias_escaped},device_hostname=${device} "

if [ -n "${current_ma}" ]; then curl_message="${curl_message}current_ma=${current_ma},"; else echo "current_ma is null"; fi
if [ -n "${voltage_mv}" ]; then curl_message="${curl_message}voltage_mv=${voltage_mv},"; else echo "voltage_mv is null"; fi
if [ -n "${power_mw}" ]; then curl_message="${curl_message}power_mw=${power_mw},"; else echo "power_mw is null"; fi
if [ -n "${total_wh}" ]; then curl_message="${curl_message}total_wh=${current_ma},"; else echo "total_wh is null"; fi
if [ -n "${err_code}" ]; then curl_message="${curl_message}err_code=${err_code},"; else echo "err_code is null"; fi

if [ -n "${sw_ver}" ]; then curl_message="${curl_message}sw_ver=\"${sw_ver}\","; else echo "sw_ver is null"; fi
if [ -n "${hw_ver}" ]; then curl_message="${curl_message}hw_ver=\"${hw_ver}\","; else echo "hw_ver is null"; fi
if [ -n "${model}" ]; then curl_message="${curl_message}model=\"${model}\","; else echo "model is null"; fi
if [ -n "${deviceId}" ]; then curl_message="${curl_message}deviceId=\"${deviceId}\","; else echo "deviceId is null"; fi
if [ -n "${oemId}" ]; then curl_message="${curl_message}oemId=\"${oemId}\","; else echo "oemId is null"; fi
if [ -n "${hwId}" ]; then curl_message="${curl_message}hwId=\"${hwId}\","; else echo "hwId is null"; fi
if [ -n "${rssi}" ]; then curl_message="${curl_message}rssi=${rssi},"; else echo "rssi is null"; fi
if [ -n "${status}" ]; then curl_message="${curl_message}status=\"${status}\","; else echo "status is null"; fi
if [ -n "${obd_src}" ]; then curl_message="${curl_message}obd_src=\"${obd_src}\","; else echo "obd_src is null"; fi
if [ -n "${mic_type}" ]; then curl_message="${curl_message}mic_type=\"${mic_type}\","; else echo "mic_type is null"; fi
if [ -n "${mac}" ]; then curl_message="${curl_message}mac=\"${mac}\","; else echo "mac is null"; fi
if [ -n "${updating}" ]; then curl_message="${curl_message}updating=${updating},"; else echo "updating is null"; fi
if [ -n "${led_off}" ]; then curl_message="${curl_message}led_off=${led_off},"; else echo "led_off is null"; fi
if [ -n "${relay_state}" ]; then curl_message="${curl_message}relay_state=${relay_state},"; else echo "relay_state is null"; fi
if [ -n "${on_time}" ]; then curl_message="${curl_message}on_time=${on_time},"; else echo "on_time is null"; fi
if [ -n "${dev_name}" ]; then curl_message="${curl_message}dev_name=\"${dev_name}\","; else echo "dev_name is null"; fi
if [ -n "${active_mode}" ]; then curl_message="${curl_message}active_mode=\"${active_mode}\","; else echo "active_mode is null"; fi
if [ -n "${ntc_state}" ]; then curl_message="${curl_message}ntc_state=${ntc_state},"; else echo "ntc_state is null"; fi
if [ -n "${err_code}" ]; then curl_message="${curl_message}err_code=${err_code},"; else echo "err_code is null"; fi

if [ -n "${host_hostname}" ]; then curl_message="${curl_message}host_hostname=\"${host_hostname}\","; else echo "host_hostname is null"; fi
#if [ -n "${device}" ]; then curl_message="${curl_message}device_hostname=\"${device}\","; else echo "device is null"; fi
#if [ -n "${alias}" ]; then curl_message="${curl_message}device_alias=\"${alias}\","; else echo "device_alias is null"; fi

##
## Remove a trailing comma in curl_message if the last element happens to be null (so that there's still a properly formatted InfluxDB mmessage)
##

curl_message="$(echo "${curl_message}" | sed 's/,$//')"

if [ "$debug" == "true" ]; then

echo "${curl_message}"

fi

/usr/bin/timeout -k 1 10s curl "${curl[@]}" --connect-timeout 2 --max-time 2 --retry 5 --retry-delay 0 --retry-max-time 30 -i -XPOST "${influxdb_url}" -u "${influxdb_username}":"${influxdb_password}" --data-binary "${curl_message}" &

fi

((i++))
[[ $((i%${#device_host_array[@]})) -eq 0 ]] && wait

done

after=$(date +%s%N)
delay=$(echo "scale=4;(${collect_interval}-($after-$before) / 1000000000)" | bc)
if [ "$debug_sleeping" == "true" ]; then echo "Sleeping: ${delay} seconds"; fi
sleep "$delay"
done
