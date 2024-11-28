# Copyright (C) 2022 Analog Devices, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#     - Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     - Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#     - Neither the name of Analog Devices, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#     - The use of this software may or may not infringe the patent rights
#       of one or more patent holders.  This license does not release you
#       from the requirement that you obtain separate licenses from these
#       patent holders to use this software.
#     - Use of the software either in source or binary form, must be run
#       on or directly connected to an Analog Devices Inc. component.
#
# THIS SOFTWARE IS PROVIDED BY ANALOG DEVICES "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED.
#
# IN NO EVENT SHALL ANALOG DEVICES BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, INTELLECTUAL PROPERTY
# RIGHTS, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import time

import adi

# import numpy as np
# from scipy import signal
# from ad4080_data_analysis import process_adc_raw_data, validate_results
from ad4080_data_analysis import process_adc_raw_data

# import spectrum

# import matplotlib.pyplot as plt

from adi import ad4880_a
from adi import ad4880_b
import serial

Channel = "ChB"

# Optionally pass URI as command line argument,
# else use default ip:analog.local

my_uri = sys.argv[1] if len(sys.argv) >= 2 else "ip:ad4080dev.local"
# my_uri = sys.argv[1] if len(sys.argv) >= 2 else "ip:analog.local"

print("uri: " + str(my_uri))

my_acq_size = 524288
if Channel == "ChA":
    my_adc_ChA = ad4880_a(uri=my_uri)
else:
    my_adc_ChB = ad4880_b(uri=my_uri)

print("my_uri", my_uri)
if Channel == "ChA":
    my_adc_ChA.rx_buffer_size = my_acq_size
else:
    my_adc_ChB.rx_buffer_size = my_acq_size


# Set up the AD4080 configuration
ser = serial.Serial(
    port='COM5',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)

ser.isOpen()
ser.flushInput()
time.sleep(1)
#ser.write(b'bash ad4080_enable_v6.sh 9 sinc5_plus_compensation 128\r')
#ser.write(b'bash ad4880_enable_v1.sh 40 sinc5_plus_compensation 4\r')
ser.write(b'bash ad4880_enable_v1.sh 40 disabled 2\r')
time.sleep(2)

ser.close()

if Channel == "ChA":
    print("Sampling frequency: ", my_adc_ChA.sampling_frequency)
    print("Scale: ", my_adc_ChA.scale)
    my_adc_ChA._ctx.set_timeout(10000 * 10000)  # not sure here, doesn't seem to be ms
    data_ChA = my_adc_ChA.rx()
else:
    print("Sampling frequency: ", my_adc_ChB.sampling_frequency)
    print("Scale: ", my_adc_ChB.scale)
    my_adc_ChB._ctx.set_timeout(10000*10000)  # not sure here, doesn't seem to be ms
    data_ChB = my_adc_ChB.rx()

# Collect data
if Channel == "ChA":
    # ADC parameters
    adc_freq = my_adc_ChA.sampling_frequency
    adc_buff_n = my_acq_size
    adc_bits = 20
    adc_quants = 2 ** adc_bits
    adc_vref = 3
    adc_quant_v = adc_vref / adc_quants
    test_type = 'sig_input'   # 'sig_input' 'dyn_range'
    # test_type = 'dyn_range'
    # Analyze spectrum and show plots
    # spectrum.analyze(test_type, data, adc_bits, adc_vref, adc_freq, window='blackman')

    (snr_adj, thd_calc,  f1_freq, fund_dbfs) = \
            process_adc_raw_data(my_adc_ChA, 1, data_ChA,
            my_acq_size, adc_freq, 1)
    my_adc_ChA.rx_destroy_buffer()
else:
    # ADC parameters
    adc_freq = my_adc_ChB.sampling_frequency
    adc_buff_n = my_acq_size
    adc_bits = 20
    adc_quants = 2 ** adc_bits
    adc_vref = 3
    adc_quant_v = adc_vref / adc_quants
    test_type = 'sig_input'   # 'sig_input' 'dyn_range'
    # test_type = 'dyn_range'

    (snr_adj, thd_calc,  f1_freq, fund_dbfs) = \
            process_adc_raw_data(my_adc_ChB, 1, data_ChB,
            my_acq_size, adc_freq, 1)
    my_adc_ChB.rx_destroy_buffer()
del my_uri