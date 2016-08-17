from threading import Thread, Event
import httplib
import sys
import time, datetime
import csv
from bs4 import BeautifulSoup

# TODOs:
# - wrap stock alert class in thread event handling more cleanly, I don't like
#   the current dependence in the start() method


class GoogleFinanceTicker(object):
    """
    Real time price data scraped from Google Finance
    """
    def __init__(self, sym, quote_type):
        self.__bs4_parser = 'lxml'
        self.__GOOGLE_FINANCE_API = 'www.google.com'
        self.__sym = sym

    def get_quote(self):
        print float(self.__extract_price_string_from_html())

    def __generate_get_request(self):
        return """/finance?q={0}""".format(self.__sym)

    def __make_request(self):
        conn = httplib.HTTPConnection(self.__GOOGLE_FINANCE_API)
        req = self.__generate_get_request()
        conn.request('GET',req)
        res = conn.getresponse().read()
        conn.close()
        return res

    def __extract_price_string_from_html(self):
        try:
            parsed_html = BeautifulSoup(self.__make_request(),self.__bs4_parser)
            price_data = parsed_html.body.find('div', attrs={'id':'price-panel'}).text.split()[0]
        except Exception as e:
            sys.stderr.write("Error: html parsing error\n")
            raise
        return price_data


class YahooDelayedTicker(object):
    def __init__(self, sym, quote_type):
        self.__VALID_QUOTE_TYPES = ['b','a']
        self.__YAHOO_FINANCE_API = 'download.finance.yahoo.com'
        self.__validate_quote_type(quote_type)
        self.__quote_type = quote_type
        self.__sym = sym
        self.__req_type = 'GET'
        self.__req = self.__generate_get_request()

    def get_quote(self):
        return float(self.__make_request().strip())

    def sym(self):
        return self.__sym

    def __validate_quote_type(self, quote_type):
        if quote_type not in self.__VALID_QUOTE_TYPES:
            raise ValueError('quote_type must be a string with value "b" or "a"')

    def __generate_get_request(self):
        return """/d/quotes.csv?s={0}&f={1}""".format(self.__sym, self.__quote_type)

    def __make_request(self):
        conn = httplib.HTTPConnection(self.__YAHOO_FINANCE_API)
        conn.request(self.__req_type, self.__req)
        res = conn.getresponse().read()
        conn.close()
        return res


class NexmoTexter(object):
    def __init__(self, credfile):
        self.__get_nexmo_creds(credfile)

    def __get_nexmo_creds(self, filename):
        with open(filename) as f:
            data = f.read().strip().split()
            self.FROM_NUMBER = data[0]
            self.__API_KEY = data[1]
            self.__API_SECRET = data[2]

    def send_alert(self, number, message):
        NEXMO_HOST = 'rest.nexmo.com'
        REQ = {}
        REQ['type'] = 'GET'
        REQ['data'] = """/sms/json?api_key={0}&api_secret={1}&from={2}&to={3}&text={4}""".format(
            self.__API_KEY, self.__API_SECRET, self.FROM_NUMBER, number, message)
        conn = httplib.HTTPSConnection(NEXMO_HOST)
        conn.request(REQ['type'],REQ['data'])
        response = conn.getresponse() # response.status, response.reason -- TODO: check response code
        conn.close()


class StockAlert(object):
    def __init__(self, opts):
        self.__trigger_value = opts['trigger_value']
        self.__texter = opts['texter']
        self.__sym = opts['sym']
        self.__quote_type = opts['quote_type']
        self.__ticker_interval_sec = opts['ticker_interval_sec']
        self.__ticker = opts['ticker'](self.__sym, self.__quote_type)
        self.__phone_number = opts['phone_number']

    def start(self, run_event=Event()):
        run_event.set()
        while run_event.is_set():
            quote_data = self.__ticker.get_quote()
            message = self.__formatted_quote_data(quote_data)
            sys.stderr.write(message + "\n")
            if self.__check_trigger(quote_data):
                self.__texter.send_alert(self.__phone_number, message)
                sys.stderr.write("Alert sent, exiting.\n")
                sys.exit(0)
            time.sleep(self.__ticker_interval_sec)

    def __formatted_quote_data(self, quote_data):
        date_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d+%H:%M:%S')
        return """STOCK+ALERT:+{0}+{1}+{2}+{3}+{4}""".format(
            self.__sym, self.__quote_type, self.__trigger_value, quote_data, date_str)

    def __check_trigger(self, quote_data):
        return ((self.__quote_type == 'b' and quote_data > self.__trigger_value) or
                (self.__quote_type == 'a' and quote_data < self.__trigger_value))


def run_until_keyboard_interrupt(threads, run_events):
    HR_IN_SEC = 3600.
    for thread in threads: thread.start()
    try:
        while True:
            time.sleep(HR_IN_SEC)
    except KeyboardInterrupt:
        sys.stderr.write("keyboard interrupt: killing threads...\n")
        for event in run_events: event.clear()
        for thread in threads: thread.join()
        sys.stderr.write("threads terminated\n")


if __name__ == "__main__":
    # init opts dict
    opts = dict( ticker = GoogleFinanceTicker, #YahooDelayedTicker,
                 quote_type = 'b',
                 ticker_interval_sec = 1.0,
                 texter = NexmoTexter('/Users/casey/.nexmo_creds'),
                 phone_number = '15555555555', default = None )

    stock_alerts = []

    # tsla alert instance
    opts['sym'] = 'tsla'
    opts['trigger_value'] = 227.0
    stock_alerts.append(StockAlert(opts))

    # aapl alert instance
    opts['sym'] = 'aapl'
    opts['trigger_value'] = 120.0
    stock_alerts.append(StockAlert(opts))

    # create threads
    run_events = map(lambda x: Event(), stock_alerts)
    threads = map(lambda x: Thread(target=x[0].start, args = (x[1],)), zip(stock_alerts, run_events))

    run_until_keyboard_interrupt(threads, run_events)
    sys.stderr.write('exiting\n')
