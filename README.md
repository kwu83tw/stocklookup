# The stocklookup project 

* Rely on iterator to save some memory.
* Make use of Pandas Dataframe to deal with series dataset stored in influxDB.
* Some TODO list to improve for better quality.
* Provide simple command line interface to insert sql content to influxDB.
* Use virtualenv.

>
>   (env) kwu@kwu-desktop:~/workspace/hw2$ python sql_to_influxdb.py --help
>   usage: sql_to_influxdb.py [-h] --path PATH
>   
>   A utility to parse given file and insert into influxDB.
>   
>   optional arguments:
>     -h, --help   show this help message and exit
>     --path PATH  Path to time series dataset.


# Assumption:
* limit user to query by date (truncate %H:%M:%S internally)
* There's future improvments for the sql parser to make it more generic or able
  to digest data when table column is changed. Now it's most likely a one-time use tool.


# Unzip the code:
* Just simple unzip it. You shall have these files in the similar folder
  structure where api/ contains the api routing and computation part, main.py
for the bottle framework, and sql_to_influxdb.py as the utility tool to insert
data to influxDB.

```
    stocklookup/
    ├── api
    │   ├── __init__.py
    │   └── snames.py
    ├── main.py
    ├── README.md
    └── sql_to_influxdb.py
```

# Step to run the code:
My test m/c is on Ubuntu 18.04, python 3.6.8
* Install InfluxDB (I'm following general instruction to install it on my m/c and no firewall set on my testbed)
> https://computingforgeeks.com/install-influxdb-on-ubuntu-18-04-and-debian-9/


* Create virtualenv first (you can create that inside my DT_hw/, however, it's not requried) Please noted that all the following commands need to apply on the same console. Cause our packages are installed inside virtualenv.
>
> virtualenv myenv


* Activate virtualenv and install needed packages (You can compare your pip
  freeze -l output to tell if any difference.)
>
> source ./myenv/bin/activate
> pip install bottle influxdb pandas


* Use one time shell script to parse DT_market_trends.sql. It will be the input
  data to the sql parser tool.
>
> grep -E '\([0-9]{1,4}.*\)[,|;]$' DT_market_trends.sql | tee parsed_data

> We expect this type of dataset in the output.
>
>        (1,'AMZN','1871.3','30265','2019-01-01 20:47:15'),
>        (2,'AMZN','1865.7','8281','2019-01-01 18:18:49'),
>        (3,'AMZN','1869.3','33400','2019-01-01 21:50:29'),
>        (4,'AMZN','1864.2','26809','2019-01-01 04:14:14'),
>        (5,'AMZN','1870.1','4006','2019-01-02 22:43:50'),
>        (6,'AMZN','1873.8','876','2019-01-02 19:15:18'),
>        (7,'AMZN','1867.7','19601','2019-01-02 17:24:37'),
>        (8,'AMZN','1871.3','34949','2019-01-02 06:31:48'),
>        (9,'AMZN','1873.6','1257','2019-01-03 01:22:46'),
>


* Trigger sql parser tool to insert data into influxDB.
>
> python sql_to_influxdb.py --path ./parsed_data


* Activating the API
>
> python DT_hw/main.py
>
> (You shall be able to see these lines on your console, it starts to listen http://127.0.0.1:8099)
>
>    (myenv) kwu@kwu-desktop:~/workspace$ python DT_hw/main.py
>    Bottle v0.12.18 server starting up (using WSGIRefServer())...
>    Listening on http://127.0.0.1:8099/
>    Hit Ctrl-C to quit. 


* curl a GET request to see if everything is okay on other consle.

```
    kwu@kwu-desktop:~$ curl -v http://127.0.0.1:8099/test
    *   Trying 127.0.0.1...
    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8099 (#0)
    > GET /test HTTP/1.1
    > Host: 127.0.0.1:8099
    > User-Agent: curl/7.58.0
    > Accept: */*
    >
    * HTTP 1.0, assume close after body
    < HTTP/1.0 200 OK
    < Date: Sat, 18 Jan 2020 07:28:18 GMT
    < Server: WSGIServer/0.2 CPython/3.6.8
    < Content-Type: application/json
    < Content-Length: 21
    <
    * Closing connection 0
    {"status": "success"}
```

* If curl command works fine, then you shall be able to query stockName.

```
curl -v --header "Content-Type:application/json" http://127.0.0.1:8099/stock/TSLA --data '{"stockName" : "TSLA", "timeZone":"Asia/Taipei","fromDate":"2019-01-05", "toDate":"2019-01-20"}'
```
