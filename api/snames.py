from bottle import request, response
from bottle import post, get, put, delete
import json

import datetime as DT
import dateutil
from influxdb import DataFrameClient

# TODO: gather static variable to a single file to better manage configuration
TIMESTR_FORMAT = "%Y-%m-%d %H:%M:%S"
START_TIMETAG = "fromDate"
END_TIMETAG = "toDate"


def _validation(func):
    """Validation decorator"""
    def wrapper(*args, **kwargs):
        return eval('_validate_' + func.__name__)(*args, **kwargs)
    return wrapper


@_validation
def get_timezone(data):
    return data.get("timeZone")


@_validation
def get_timestamp(data, tag=START_TIMETAG):
    """
    :param data: user given dataset
    :param tag: fromDate or toDate
    :type data: dict
    :type tag: str
    :return: string format of timestamp
    """
    return data.get(tag)


@_validation
def get_stock_name(data, stockName):
    return stockName


@get('/test')
def listen_handler():
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': 'success'})


@post('/stock/<stockName>')
def req_handler(stockName):
    """
    Request handler
    """
    try:
        try:
            data = request.json
        except Exception:
            raise ValueError

        if data is None:
            raise ValueError

        try:
            stock_name = get_stock_name(data, stockName)
            time_zone = get_timezone(data)
            if not time_zone:
                time_zone = "America/Los_Angeles"
            tz = dateutil.tz.gettz(time_zone)
            # from and to must be UTC
            # truncate %H:%M:%S to 00:00:00 - 23:59:59 limit to day query only
            from_date = _pruning_timestamp(get_timestamp(data, START_TIMETAG))
            to_date = _pruning_timestamp((get_timestamp(data, END_TIMETAG)),
                                         to_date=True)
            # set to past week from today if no from and to date
            # TODO: Validate scenario given only fromDate or toDate
            if not from_date and not to_date:
                today = DT.datetime.now(tz)
                to_date = (DT.datetime(
                            today.year,
                            today.month,
                            today.day,
                            tzinfo=tz) + DT.timedelta(days=1) -
                           DT.timedelta(seconds=1)).strftime(TIMESTR_FORMAT)
                from_date = (DT.datetime(
                            today.year,
                            today.month,
                            today.day,
                            tzinfo=tz) -
                            DT.timedelta(days=7)).strftime(TIMESTR_FORMAT)
            from_date_utc = convert_to_utc(from_date, tz)
            to_date_utc = convert_to_utc(to_date, tz)
            res = query_dataset(stockName, from_date_utc, to_date_utc, tz)

        except (TypeError, KeyError):
            # indicate that user doesn't provide proper body
            raise ValueError

    except ValueError:
        # if bad request data, return 400 Bad Request
        response.status = 400
        return

    except KeyError:
        response.status = 409
        return

    response.headers['Content-Type'] = 'application/json'
    response.status = 200
    return json.dumps({
        "success": "true",
        "stockName": stockName,
        "fromDate": from_date,
        "toDate": to_date,
        "timeone": time_zone,
        "result": res
        })


def query_dataset(stockName, from_date_utc, to_date_utc, tz):
    """
    The part to use influxDB python library and Pandas Dataframe to deal with
    series dataset.
    :param stockName: Name of the stock
    :param from_date_utc: timestamp in utc
    :param to_date_utc: timestamp in utc
    :param tz: user preferred timezone
    :type stockName: str
    :type from_date_utc: str
    :type to_date_utc: str
    :type tz: tzinfo
    :return: A dictionary of price associate to each date for specified time
    range
    """
    cli = DataFrameClient(database="DT")
    dfs = cli.query("select * from market_trends").get('market_trends')
    bname = dfs["business_name"] == stockName
    avg_val, res = None, {}
    for ps, pe in _interval_generator(from_date_utc, to_date_utc):
        dfs_range = dfs[(bname)]["business_value"].loc[ps:pe]
        if dfs_range.size != 0:
            avg_val = dfs_range.mean()
        output_tz =\
            convert_utc_time_to_other_timezone(ps, tz).split(' ')[0]
        if isinstance(avg_val, float):
            avg_val = round(avg_val, 1)
        res[output_tz] = str(avg_val)
    return res


def query_max_price_per_month(stockName):
    """
    Return max price per month
    """
    cli = DataFrameClient(database="DT")
    dfs = cli.query("select * from market_trends").get('market_trends')
    bname = dfs["business_name"] == stockName
    # format data
    dfs["Date"] = pd.to_datetime(df["Date"])
    dfs["Month"] = dfs["Date"].dt.month
    res = df[bname].groupby("Month").max(axis="Stock Price")
    return res


def query_deal_between_1pm_to_4pm_on_Feb(stockName):
    """
    Return price between 1pm-4pm on Feb
    """
    cli = DataFrameClient(database="DT")
    dfs = cli.query("select * from market_trends").get('market_trends')
    bname = dfs["business_name"] == stockName
    fter_hour = df["Date"].dt.hour >= 13
    before_hour = df["Date"].dt.hour < 16
    deal_after_one = df[after_hour & before_hour]
    res = deal_after_one[bname & (df["Month"] == 2)]
    return res


def _interval_generator(from_date, to_date):
    """
    Calculate interval between from_date to to_date through each
    interval (as 00:00:00 - 23:59:59)
    :return: datetime string as [(start, end)]
    """
    start = convert_str_to_dt(from_date)
    end = convert_str_to_dt(to_date)
    interval = (end - start).days
    pstart, pend, res = None, None, []
    while interval >= 0:
        if not pstart:
            pstart = start
        else:
            pstart = pend + DT.timedelta(seconds=1)
        pend = pstart + DT.timedelta(hours=23, minutes=59, seconds=59)
        interval -= 1
        yield (pstart.strftime(TIMESTR_FORMAT), pend.strftime(TIMESTR_FORMAT))


def _validate_get_stock_name(*args):
    req_body_stock_name = args[0].get("stockName")
    path_stock_name = args[1]
    if req_body_stock_name and req_body_stock_name != path_stock_name:
        raise ValueError


def _validate_get_timezone(*args):
    tz_str = args[0].get('timezone')
    if not tz_str:
        return None
    if not dateutil.tz.gettz(tz_str):
        raise ValueError("Invalid timezone %s" % tz_str)
    return tz_str


def _validate_get_timestamp(*args):
    tag = args[1]
    dt_str = args[0].get(tag)
    if not dt_str:
        return None
    if len(dt_str.split(" ")) == 2:
        try:
            DT.datetime.strptime(dt_str, TIMESTR_FORMAT)
        except ValueError:
            raise ValueError("Invalid timestamp format, should be %s" %
                             TIMESTR_FORMAT)
    else:
        try:
            DT.datetime.strptime(dt_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid timestamp format, should be %Y-%m-%d")
    return dt_str


def _pruning_timestamp(dt_str, to_date=False):
    """
    Revise from and to timestamp to 00:00:00 and 23:59:59
    return %Y-%m-%d string
    """
    if not dt_str:
        return None

    dt = dt_str.split(" ")[0]
    do = DT.datetime.strptime(dt, "%Y-%m-%d")
    if to_date:
        do = do + DT.timedelta(days=1) - DT.timedelta(seconds=1)
    return do.strftime(TIMESTR_FORMAT)


def convert_to_utc(dt_str, timezone):
    """
    :param dt_str: Date to convert to UTC time.
    :param timezone: timzone tzinfo
    :type dt_str: dt_strtime timestamp string
    :type timezone: tzinfo
    :return: UTC time in string
    """
    if not isinstance(dt_str, str):
        raise ValueError
    if not isinstance(timezone, dateutil.tz.tzfile):
        raise ValueError
    date = convert_str_to_dt(dt_str).replace(tzinfo=timezone)
    return date.astimezone(DT.timezone.utc).strftime(TIMESTR_FORMAT)


def convert_utc_time_to_other_timezone(dt_str, timezone):
    """
    :param dt_str: Date to convert to preferred timezone time
    :param timezone: timzone tzinfo
    :type dt_str: str
    :type timezone: tzinfo
    :return: wanted timezone timestamp string
    """
    if not isinstance(dt_str, str):
        raise ValueError
    if not isinstance(timezone, dateutil.tz.tzfile):
        raise ValueError
    utc_time = convert_str_to_dt(dt_str).replace(tzinfo=DT.timezone.utc)
    return utc_time.astimezone(timezone).strftime(TIMESTR_FORMAT)


def convert_str_to_dt(dt_str):
    """
    :param dt_str: Date string in a format
    :type dt_str: string
    :return: datetime object
    """
    if not isinstance(dt_str, str):
        raise ValueError
    return DT.datetime.strptime(dt_str, TIMESTR_FORMAT)
