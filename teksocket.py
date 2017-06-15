import logging
import socket
from time import sleep

logger = logging.getLogger("Tek." + __name__)


class TekSocket(object):
    def __init__(self, host, port):
        server_address = (host, port)
        self.num_points = 100000

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect(server_address)
        self.send_cmd('*cls')
        self.id = self.send_query('*idn?')
        logger.info("Connected to {}".format(self.id))
        self.sync()
        self.send_cmd('header 0')  # turn off headers
        self.data_initialized = False
        self.t_scale = 0
        self.t_start = 0
        self.v_scale = 0
        self.v_off = 0
        self.v_pos = 0
        self.raw_data = []
        self.get_scale_factors()

    def send_cmd(self, cmd):
        logger.debug(cmd)
        if not cmd.endswith('\n'):
            cmd += '\n'
        sleep(.05)  # TODO: Use 'BUSY?', '*OPC?', '*WAI' commands to better handle busy states
        bytes_sent = self.sock.send(cmd)
        if bytes_sent < len(cmd):
            print "Could not send all bytes"

    def send_query(self, query, max_bytes=1000):
        self.send_cmd(query)
        sleep(.1)
        resp = self.sock.recv(max_bytes)
        # TODO: verify all queries end with newline
        # Keep receiving data until we get a newline
        while resp[-1] != '\n':
            resp += self.sock.recv(max_bytes)
        return resp

    def get_scale_factors(self):
        # using a single query and splitting it is faster than doing multiple queries
        resp = self.send_query('wfmoutpre?').split(";")
        self.t_scale = float(resp[10])  # 'wfmoutpre:xincr?'
        self.t_start = float(resp[11])  # 'wfmoutpre:xzero?'
        self.v_scale = float(resp[14])  # 'wfmoutpre:ymult?' , volts / level
        self.v_off = float(resp[16])    # 'wfmoutpre:yzero?' , reference voltage
        self.v_pos = float(resp[15])    # 'wfmoutpre:yoff?'  , reference position (level)

    def init_data(self, channel='Ch1'):
        self.sync()
        self.send_cmd('header 0')
        self.send_cmd('data:encdg FASTEST')
        self.send_cmd('data:source {}'.format(channel))
        self.send_cmd('wfmoutpre:byt_n 2')
        self.send_cmd('data:start 1')
        self.send_cmd('data:stop {}'.format(self.num_points))
        # self.num_points = int(self.send_query('wfmoutpre:nr_pt?'))
        self.get_scale_factors()
        self.data_initialized = True

    def get_data(self, channel='Ch1'):
        if not self.data_initialized:
            self.init_data()
        self.send_cmd('data:source {}'.format(channel))
        # actually request the data
        data = self.send_query('curve?')
        # binary block header
        p = int(data[1])
        data_size = int(data[2:2+p])  # parse IEEE488.2 binary block header
        raw_data = data[p+2:]
        self.raw_data = raw_data[0:data_size]
        return self.raw_data

    def reset(self):
        self.send_cmd('*rst')
        sleep(2)  # sleep to give the scope time to reset

    def sync(self):
        self.send_query('*opc?')

    def shutdown(self):
        self.sock.close()
