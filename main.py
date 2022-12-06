"""
curl --location --request POST 'https://api.runpod.io/graphql?api_key=VH5W2VAXM2IQSCW1IF68WNPD9AZV8MTP7AGOQESU' \
--header 'Content-Type: application/json' \
--data-raw '{"query":"query getMyMachines { \n myself { \n id\n machineQuota \n machines { \n id \n name \nhostMinBidPerGpu \n registered \n listed \n verified \ngpuPowerLimitPercentageSelf \n margin \n gpuType { \ndisplayName \n securePrice \n __typename \n } \n cpuCount \ndiskReserved \n diskTotal \n diskMBps \n downloadMbps \ngpuReserved \n gpuTotal \n memoryReserved \n memoryTotal \npcieLink \n pcieLinkWidth \n uploadMbps \n vcpuReserved \nsecureCloud \n vcpuTotal \n pods { \n podType \n gpuCount \nvcpuCount \n containerDiskInGb \n memoryInGb \n volumeInGb \ndesiredStatus \n costPerHr \n costMultiplier \n __typename \n} \n supportPublicIp \n uptimePercentListedOneWeek \nuptimePercentListedFourWeek \n __typename \n } \n __typename\n } \n} ","variables":{}}'
"""


import requests
import logging
import json
import os
from time import sleep
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##LOGGING OPTIONS
LOG_LEVEL = os.getenv("LOG_LEVEL") or "INFO"
FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
log = logging
log.basicConfig(format=FORMAT,level=LOG_LEVEL)


API_KEY = os.getenv("RUNPOD_API_KEY") or "VH5W2VAXM2IQSCW1IF68WNPD9AZV8MTP7AGOQESU"
baseurl = os.getenv("QUERY_URL") or "https://api.runpod.io/graphql"
baseurl = baseurl+"?api_key="+API_KEY

influx_host = os.getenv("INFLUX_HOST") or "http://172.17.0.1:8086"

machine_database=os.getenv("INFLUX_MACHINE_BUCKET") or "metrics"
machine_measurement = os.getenv("INFLUX_MACHINE_MEASUREMENT") or 'runpodapimetrics'
earnings_database = os.getenv("INFLUX_EARNINGS_BUCKET") or 'machineEarnings'
earnings_measurement = os.getenv("INFLUX_EARNINGS_MEASUREMENT") or 'earnings'
influx_token = os.getenv("INFLUX_TOKEN") 
influx_orgID=os.getenv("INFLUX_ORG_ID") or '17ffc3127f13aa8f'


machine_url =  influx_host+"/api/v2/write?orgID={}&bucket={}&precision=ns".format(influx_orgID,machine_database)
earnings_url =  influx_host+"/api/v2/write?orgID={}&bucket={}&precision=ns".format(influx_orgID,earnings_database)
queryurl =  influx_host+"/api/v2/authorizations"

INFLUX_FORMAT=os.getenv("INFLUX_FORMAT") or "name-values" #name=n value1=v1,value2=v2,...,value_n=v_n
#INFLUX_FORMAT="name-metric-value" #name=n,metric=m value=v

SLEEP_TIME = int(os.getenv("SLEEP_TIME") or 60) 

required_fields = [
    'cpuCount',
    "diskReserved",
    "diskTotal",
    "diskMBps",
    "downloadMbps",
    "gpuReserved",
    "gpuTotal",
    "memoryReserved",
    "memoryTotal",
    "pcieLink",
    "pcieLinkWidth",
    "uploadMbps",
    "vcpuReserved",
    "secureCloud",
    "vcpuTotal"
]


def formatNameValue(name,gpu,obj,measurement):
    # returns name=n value1=v1,value2=v2,...,value_n=v_n
    output = "{},name={},gpuDisplayName={} ".format(measurement,name.replace(' ','\\ '),gpu.replace(' ','\\ '))
    values = []
    for key in obj:
        values.append("{}={}".format(key,obj[key]))

    output += ",".join(values)
    return output

def formatNameMetric(name,gpu,obj,measurement):
    # returns name=n,metric=m value=v
    values = []
    for key in obj:
        values.append("{},name={},gpuDisplayName={},metric={} value={}"
            .format(measurement,name.replace(' ','\\ '),gpu.replace(' ','\\ '),key,obj[key]))

    output = "\n".join(values)
    return output

def getParser():
    #returns the selected message formatter or error
    parser = {
        "name-values": formatNameValue,
        "name-metric-value": formatNameMetric,
    }.get(INFLUX_FORMAT,"NA")

    if parser == "NA":
        raise ValueError("No parser function defined for {}".format(INFLUX_FORMAT))

    return parser

def getPodData(pods):
    log.debug("Total pods: {}".format(len(pods)))
    retsum = 0
    for i in range(len(pods)):
        if 'desiredStatus' in pods[i].keys() and 'costPerHr' in pods[i].keys():
            if pods[i]['desiredStatus'] == 'RUNNING':
                log.debug("Pod Cost added: {}".format(pods[i]['costPerHr']))
                retsum += pods[i]['costPerHr']
    return round(retsum,4)


def selectMetrics(machine):
    # returns only the selected metrics from machine
    influx_object = {}
    #name setup
    log.debug("Machine Found: {}".format(json.dumps(machine)))
    name = 'noName-'+str(i)
    if 'name' in machine:
        name = machine['name']
    else:
        log.warning("no name defined for machine at index {} ".format(i))

    #key extraction
    for idx,key in enumerate(required_fields):
        if not key in machine.keys():
            log.warning("key {} not found for machine {}".format(key,name ))
        else:
            influx_object[key] = machine[key]

    if 'pods' in machine.keys():
         cost = getPodData(machine['pods'])
         influx_object['sum_costPerHr'] = cost
    else:
        log.info("machine {} has no pods")

    gpuName="none";
    if 'gpuType' in machine.keys():
        if 'displayName' in machine['gpuType'].keys():
            gpuName = machine['gpuType']['displayName'];

    return [name,gpuName,influx_object]


def queryAPI():
    # performs runpod api query
    headers = {'content-type':'application/json'}
    #old query
    #data = r'{"query":"query getMyMachines { \n myself { \n id\n machineQuota \n machines { \n id \n name \nhostMinBidPerGpu \n registered \n listed \n verified \ngpuPowerLimitPercentageSelf \n margin \n gpuType { \ndisplayName \n securePrice \n __typename \n } \n cpuCount \ndiskReserved \n diskTotal \n diskMBps \n downloadMbps \ngpuReserved \n gpuTotal \n memoryReserved \n memoryTotal \npcieLink \n pcieLinkWidth \n uploadMbps \n vcpuReserved \nsecureCloud \n vcpuTotal \n pods { \n podType \n gpuCount \nvcpuCount \n containerDiskInGb \n memoryInGb \n volumeInGb \ndesiredStatus \n costPerHr \n costMultiplier \n __typename \n} \n supportPublicIp \n uptimePercentListedOneWeek \nuptimePercentListedFourWeek \n __typename \n } \n __typename\n } \n} ","variables":{}}'
    #new query
    data = r'{"query":" query getMyMachines { \n myself { \n id\n machineQuota \n machines { \n id \n name \n machineBalance {\n hostDiskEarnings\n hostTotalEarnings\n hostGpuEarnings\n }\n hostMinBidPerGpu \n registered \n listed \n verified \n gpuPowerLimitPercentageSelf \n margin \n gpuType { \n displayName \n securePrice \n __typename \n } \n cpuCount \n diskReserved \n diskTotal \n diskMBps \n downloadMbps \n gpuReserved \n gpuTotal \n memoryReserved \n memoryTotal \n pcieLink \n pcieLinkWidth \n uploadMbps \n vcpuReserved \n secureCloud \n vcpuTotal \n pods { \n podType \n gpuCount \nvcpuCount \n containerDiskInGb \n memoryInGb \n volumeInGb \ndesiredStatus \n costPerHr \n costMultiplier \n __typename \n} \n supportPublicIp \n uptimePercentListedOneWeek \nuptimePercentListedFourWeek \n __typename \n } \n __typename\n } \n} ","variables":{}}'

    res = requests.post(baseurl,headers=headers, data = data,verify=False)
    if (res.status_code != 200):
        raise ValueError("Response Error: Status {} text: {}".format(res.status_code,res.text))

    # json parsing and field check
    response = res.json()
    log.debug(response)

    if 'data' not in response:
        raise ValueError("Expected data field not found")
    if 'myself' not in response['data']:
        raise ValueError("Expected data myself not found")
    if 'machines' not in response['data']['myself']:
        raise ValueError("Expected data.myself.machines not found")

    log.info("RunPod API Query OK")
    return response['data']['myself']['machines']


def pushData(push_url,payload,data_type):
    # posts data to influxdb
    data = '\n'.join(payload).replace("=True","=1").replace("=False","=0")
    log.debug("PAYLOAD: {}".format(data))

    #start request
    headers = {'content-type':'text/plain; charset=utf-8', 'Authorization': 'Token '+influx_token } 
    res = requests.post(push_url,headers=headers, data = data,verify=False)
    if (res.status_code != 200 and res.status_code != 204):
        raise ValueError("Response Error: Status {} text: {}".format(res.status_code,res.text))

    log.info("InfluxDB {}: Push OK".format(data_type))
    log.debug(res.text)


def testInflux():
    #test conectivity by creating database
    headers={'Authorization': 'Token '+influx_token } 
    res = requests.get(queryurl,headers=headers,verify=False)
    if (res.status_code != 200):
        raise ValueError("Response Error: Status {} text: {} {}".format(res.status_code,res.text))

    log.info("InfluxDB Online")
    log.debug(res.text)



if __name__ == "__main__":

    #loop every SLEEP_SECONDS
    while True:
        machine_data = []
        earnings_data = []
        try:    

            data_formatter = getParser()
            testInflux()

            machines = queryAPI()
            for i,machine in enumerate(machines):
                name,gpuName,machine_object = selectMetrics(machine)
                machine_data.append(data_formatter(name,gpuName,machine_object,machine_measurement))
                if 'machineBalance' in machine and machine['machineBalance'] is not None:
                    earnings_data.append(data_formatter(name,gpuName,machine['machineBalance'],earnings_measurement))
                log.debug("Parsed: {} DATA {}\n".format(name, machine_data))

            if len(machine_data) > 0:
                pushData(machine_url,machine_data,"Machines")
            if len(earnings_data) > 0:
                pushData(earnings_url,earnings_data,"Earnings")
            
            sleep(SLEEP_TIME)
        except Exception as e:
            log.error(e)
            exit(2)