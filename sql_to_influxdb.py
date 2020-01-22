from influxdb import InfluxDBClient
import argparse
import os
import pdb
INFLUX_DB_NAME = "DT"
INFLUX_HOST = "127.0.0.1"
INFLUX_PORT = "8086"
INFLUX_PRECISION = "rfc3339"


def main(path):
    influxClient = InfluxDBClient(INFLUX_HOST, INFLUX_PORT)
    influxClient.drop_database(INFLUX_DB_NAME)
    influxClient.create_database(INFLUX_DB_NAME)
    influxClient.write_points(generate_influx_points(path),
                              database=INFLUX_DB_NAME)


def file_loader(path):
    with open(path) as f:
        line = f.readline()
        while line:
            prev_line = line
            line = f.readline()
            yield prev_line


def generate_influx_points(path):
    """
    Expect to parse csv-liked dataset.
    """
    influx_points = []
    for record in file_loader(path):
        tags, fields = {}, {}
        raw_data = record.strip()[1:-2].split(',')
        tags["business_name"] = raw_data[1].strip()[1:-1]
        fields["business_value"] = float(raw_data[2][1:-1])
        fields["business_volume"] = raw_data[3][1:-1]
        r_time = raw_data[-1][1:-1]
        influx_points.append({
            "measurement": "market_trends",
            "tags": tags,
            "time": r_time,
            "fields": fields
            })
    return influx_points


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="A utility to parse given file and insert into\
            influxDB.")
    parser.add_argument("--path", help="Path to time series dataset.",
                        type=str, required=True)
    args = parser.parse_args()
    main(args.path)
