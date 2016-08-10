import httplib
import sys
import time, datetime
import csv


# TODO: encapsulate as a stock alert class so that multiple
# alerts can be created and set running.


def get_quote(sym, quote_type):
    VALID_QUOTE_TYPES = ['b','a']
    YAHOO_FINANCE_API = 'download.finance.yahoo.com'
    REQ = {}
    REQ['type'] = 'GET'
    REQ['data'] = """/d/quotes.csv?s={0}&f={1}""".format(sym, quote_type)
    conn = httplib.HTTPConnection(YAHOO_FINANCE_API)
    conn.request(REQ['type'],REQ['data'])
    data = float(conn.getresponse().read().strip())
    conn.close()
    return data


class NexmoTexter(object):

    def __init__(self, credfile='.nexmo_creds'):
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
        response = conn.getresponse() # response.status, response.reason
        conn.close()
        sys.stderr.write("Alert sent, exiting.\n")
        sys.exit(0)


if __name__ == "__main__":

    sym = 'TSLA'
    quote_type = 'b'
    number = '15208696038'
    trigger_value = 227.0
    nexmo_texter = NexmoTexter()
    quote_check_time_sec = 10.

    while(True):
        quote_data = get_quote(sym, quote_type)
        date_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d+%H:%M:%S')
        message = """STOCK+ALERT:+{0}+{1}+{2}+{3}+{4}""".format(
            sym, quote_type, trigger_value, quote_data, date_str)
        sys.stderr.write(message + "\n")
        if quote_type == 'b' and quote_data > trigger_value:
            nexmo_texter.send_alert(number, message)
        elif quote_type == 'a' and quote_data < trigger_value:
            nexmo_texter.send_alert(number, message)
        time.sleep(quote_check_time_sec)
