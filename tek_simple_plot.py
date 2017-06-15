from teksocket import TekSocket
import numpy as np
import pylab as pl

if __name__ == '__main__':
    tek = TekSocket('192.168.2.164', 4000)
    data = tek.get_data()
    data = np.frombuffer(data, dtype=np.int16).newbyteorder()
    total_time = tek.t_scale * data.size
    tstop = tek.t_start + total_time
    scaled_time = np.linspace(tek.t_start, tstop, num=data.size, endpoint=False)
    scaled_data = (np.array(data, dtype='double') - tek.v_pos) * tek.v_scale + tek.v_off

    pl.plot(scaled_time, scaled_data, lw='1')
    pl.show()

