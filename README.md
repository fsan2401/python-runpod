# runpod-api-influx

Python agent which queries Runpod API periodically, selects preconfigured fields and pushes data to InfluxDb

### Changelog

- 2022-11-17 - added gpuDisplayName tag
- 2022-11-12 - escaped spaces on name tags to avoid error on names with spaces
- 2022-11-12 - renamed INFLUX_BUCKET to INFLUX_MACHINE_BUCKET and INFLUX_MEASUREMENT to INFLUX_MACHINE_MEASUREMENT
- 2022-11-12 - new machineEarnings Query added (new env INFLUX_EARNINGS_BUCKET,INFLUX_EARNINGS_MEASUREMENT )
- 2022-10-28 - sum_costPerHr field added (sum of all RUNNING pods costPerHr)
- 2022-10-27 - Influx Auth for latest version corrected
- 2022-10-26 - loop, dockerfile added
- 2022-10-25 - Initial version


### Build and startup

```
git clone
cd runpod-api-influx

docker build -t  runpod-api-influx .

#default env values listed
docker run -ti \
    -e LOG_LEVEL=INFO \
    -e SLEEP_TIME=60 \
    -e INFLUX_FORMAT=name-values \
    -e INFLUX_HOST=http://1xxxxx1:8086 \
    -e INFLUX_MACHINE_BUCKET=metrics \
    -e INFLUX_MACHINE_MEASUREMENT=runpodapimetrics \
    -e INFLUX_EARNINGS_BUCKET=machineEarnings \
    -e INFLUX_EARNINGS_MEASUREMENT=earnings \
    -e INFLUX_TOKEN="xxxxxxxxxxxxxxxxxxxxx==" \
    -e INFLUX_ORG_ID="f2cba366681f0213" \
    -e RUNPOD_API_KEY=xxxxxxxxxxxxx \
    --restart=unless-stopped \
    --name=runpod-api-influx \
    runpod-api-influx

```

#### OTHER ENV VARIABLES

```
    QUERY_URL=https://api.runpod.io/graphql

```


#### EXPECTED OUTPUT:

```

2022-11-13 01:09:08,282 [INFO] InfluxDB Online
2022-11-13 01:09:11,542 [INFO] RunPod API Query OK
2022-11-13 01:09:11,572 [INFO] InfluxDB Machines: Push OK
2022-11-13 01:09:11,685 [INFO] InfluxDB Earnings: Push OK
2022-11-13 01:10:11,758 [INFO] InfluxDB Online
2022-11-13 01:10:15,124 [INFO] RunPod API Query OK
2022-11-13 01:10:15,162 [INFO] InfluxDB Machines: Push OK
2022-11-13 01:10:15,179 [INFO] InfluxDB Earnings: Push OK


```

#### About INFLUX_FORMAT variable


- INFLUX_FORMAT="name-values"
```

#returns name=n,metric=m value=v

Influx Query:
    select mean(vcpuTotal) from measurement2 group by time(5m),"name",time(5m)

```
- INFLUX_FORMAT="name-metric-value" 
```

#returns name=n,metric=m value=v

Influx Query:
    select mean(value) from measurement2 where metric='vcpuTotal' group by "name",time(5m)

```

#### Rebuilding the container and running it
```
git pull
docker kill runpod-api-influx 
docker rm runpod-api-influx 
docker run -d -e LOG_LEVEL=INFO -e SLEEP_TIME=60 \
-e INFLUX_FORMAT=name-values \
-e INFLUX_HOST=http://1xxxxxxxxx:8086 \
-e INFLUX_TOKEN="VLHre-xxxxxxxxxxxxxxxxxxxx==" \
-e INFLUX_ORG_ID="xxxxxxxxxx" \
-e INFLUX_MACHINE_BUCKET=runpod \
-e INFLUX_EARNINGS_BUCKET=runpod \
--name=runpod-api-influx \
runpod-api-influx
```


# Sample InfluxDb queries

- Earnings Raw Data by minute displaying name and gpuName
```
from(bucket: "runpod")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "earnings")
  |> filter(fn: (r) => r["_field"] == "hostTotalEarnings")
  |> group(columns: ["gpuDisplayName","name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```
- Earnings Raw Data by hour by gpuName

```
from(bucket: "runpod")
  |> range(start: time(v:"2022-11-17T00:00:00.000Z"), stop: time(v:"2022-12-18T00:00:00.000Z"))
  |> filter(fn: (r) => r["_measurement"] == "earnings")
  |> filter(fn: (r) => r["_field"] == "hostTotalEarnings")
  |> aggregateWindow(every: 1m, fn: sum, createEmpty: false)
  |> difference(nonNegative: true, columns: ["_value"])
  |> group(columns: ["gpuDisplayName"])
  |>aggregateWindow(every: 1h, fn: sum, createEmpty: false)

```

- Aggregate Earnings by hour
```
from(bucket: "runpod")
  |> range(start: time(v:"2022-11-17T00:00:00.000Z"), stop: time(v:"2022-12-18T00:00:00.000Z"))
  |> filter(fn: (r) => r["_measurement"] == "earnings")
  |> filter(fn: (r) => r["_field"] == "hostTotalEarnings")
  |> aggregateWindow(every: 1m, fn: sum, createEmpty: false)
  |> difference(nonNegative: true, columns: ["_value"])
  |> group()
  |>aggregateWindow(every: 1h, fn: sum, createEmpty: false)
```
