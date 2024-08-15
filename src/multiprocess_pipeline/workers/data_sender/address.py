import traceback
import struct
import time

import numpy as np
from enum import Enum, unique
from socket import *

from ._masterclass import BaseDataSender

FLAG = 'S///'


@unique
class ESupportConnectionType(Enum):
    TCP = 1
    UDP = 2


class AddressDataSender(BaseDataSender):
    def __init__(self,
                 *args,
                 **kwargs):
        super(AddressDataSender, self).__init__(*args, **kwargs)

        address_str_list = self.target.split(':')
        self.connect_type, ip, port = address_str_list[0], address_str_list[1], int(address_str_list[2])
        assert ESupportConnectionType[self.connect_type], \
            f'None support connection type {self.connect_type}. Please check it.'
        self.address = (ip, port)
        self.len = 1

        self.ConnectionSocket = None
        self.b_socket_alive = True

        self.connect()

    def connect(self):
        if self.connect_type == ESupportConnectionType.TCP.name:
            server_socket = socket(AF_INET, SOCK_STREAM)
            server_socket.bind(self.address)
            server_socket.listen()

            self.ConnectionSocket, address = server_socket.accept()
        elif self.connect_type == ESupportConnectionType.UDP.name:
            server_socket = socket(AF_INET, SOCK_DGRAM)
            self.ConnectionSocket = server_socket
        else:
            raise

        self.ConnectionSocket.settimeout(60)

    def send_data(self, data: np.ndarray) -> bool:
        super(AddressDataSender, self).send_data(data)
        time_stamp = self.get_current_timestamp()
        data_send = struct.pack(f'{len(FLAG)}s', FLAG.encode('utf-8'))
        data_send += struct.pack('Q', time_stamp)

        # data format: (class, id , (xyza))
        if not isinstance(data, np.ndarray):
            return False

        data_index = np.nonzero(data)
        num = len(data_index[-1]) // 4
        for i in range(num):
            class_i = int(data_index[0][i * 4])
            id_i = int(data_index[1][i * 4])
            x_i = data[class_i][id_i][0]
            y_i = data[class_i][id_i][1]
            z_i = data[class_i][id_i][2]
            a_i = data[class_i][id_i][3]

            data_send += struct.pack('IIffff', class_i, id_i, x_i, y_i, z_i, a_i)

        if self.connect_type == ESupportConnectionType.UDP.name:
            self.ConnectionSocket.sendto(data_send, self.address)
            return True
        elif self.connect_type == ESupportConnectionType.TCP.name:
            self.ConnectionSocket.send(data_send)
            return True
