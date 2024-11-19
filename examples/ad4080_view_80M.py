
import numpy as np
from scipy.signal import windows
from scipy.fft import fft, ifft, fftfreq

from matplotlib import pyplot as plt
from mpl_interactions import ioff, panhandler, zoom_factory



from adi.ad4080 import ad4080  # to connect to the AD4080
import paramiko  # to use SSH
import os  # to transfer files using the scp via windows terminal

[2]
# Data source flag = 'FILE' | 'pyADC' | 'zedADC'
# 'FILE' -> loads the data from a file specified in the line 'with open('FILE_NAME.xxx', 'rb') as file:'
# 'pyADC' -> Acquire the data from the AD4080 using the pyadi-iio library
# 'zedADC' -> Acquire the data from the AD4080 via ZedBoard IIO driver and then transfer the file to this PC via SCP.
# P.S. -> Always perform a reboot in the ZedBoard when changing from 'pyADC' to 'zedADC' and vice-versa.
# P.S.2 -> Restarting the Python kernel every once in a while also helps to prevent memory allocation errors in the PC.
# data_sorce = 'pyADC'
data_sorce = 'FILE'
# Config
ADC_sf = 8000000 # Variable Input Sampling Frequency
# SSH connection parameters
host = '169.254.199.69'  # ZedBoard IP address
port = 22
username = 'root'
password = 'analog'

# pyADC configs
pyADC_buffer = 30 * 1024 * 1024  # Max 30M samples

# zedADC configs
zedADC_buff = 80 * 1024 * 1024  # Max 100M samples

# Load the samples from a file
if data_sorce == 'FILE':
    print('Data source: load from file')

    #with open('samples_pyADC.dat', 'rb') as file:
    with open('c:\\samples.dat', 'rb') as file:
        data = np.frombuffer(file.read(), dtype=np.int32)

# Acquire the data from the AD4080 using the pyadfi-iio library
elif data_sorce == 'pyADC':
    print('Data source: acquire from ADC')

    # Create an SSH client
    print('Opening the SSH connection...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the Linux PC
        ssh.connect(host, port, username, password)
        print('SSH connection successful!')

        print('Configuring the clock...')
        # Execute the command
        stdin, stdout, stderr = ssh.exec_command('ad4080_update_clks.sh 40')
        # Print the output of the command
        print(stdout.read().decode())
        print('Clock configured successfully!')

        print('Setting ZedBoard dma buffer size...')
        # Execute the command
        stdin, stdout, stderr = ssh.exec_command(
            'echo 335544320 >/sys/module/industrialio_buffer_dma/parameters/max_block_size')
        # Print the output of the command
        print(stdout.read().decode())

        print('Checking ZedBoard dma buffer size...')
        # Execute the command
        stdin, stdout, stderr = ssh.exec_command('cat /sys/module/industrialio_buffer_dma/parameters/max_block_size')
        # Print the output of the command
        print(stdout.read().decode())

        # Check if there was any error during command execution
        # error = stderr.read().decode()
        # if error:
        #    raise Exception(f"Command execution error: {error}")

    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your username and password.")
    except paramiko.SSHException as ssh_exception:
        print(f"SSH connection error: {str(ssh_exception)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        # Close the SSH connection
        ssh.close()

    # Optionally pass URI as command line argument,
    # else use default ip:analog.local
    # my_uri = sys.argv[1] if len(sys.argv) >= 2 else 'ip:analog.local'
    my_uri = 'ip:' + host
    print('URI:' + str(my_uri))

    my_adc = ad4080(uri=my_uri)
    my_adc.rx_buffer_size = pyADC_buffer  # MAX 30Msamples so far
    # my_adc._rx_data_type = np.int32

    print('Sampling frequency: ', my_adc.sampling_frequency)
    print('RX buffer size:', my_adc.rx_buffer_size)
    print('Test mode: ', my_adc.test_mode)
    print('Scale: ', my_adc.scale)

    # Do the acquisition
    my_adc.rx_enabled = True
    data = my_adc.rx()
    # my_adc.rx_destroy_buffer()
    my_adc.rx_enabled = False

    # save the data
    with open('phaser/samples_pyADC.dat', 'wb') as file:
        data.tofile(file)

    # N = 2
    # buffer = np.zeros((N,my_adc.rx_buffer_size), dtype=np.int32)
    # for i in range(0, N):
    #    buffer[i] = my_adc.rx()
    # data = buffer.reshape(-1)

# Acquire the data from the AD4080 using the ZedBoard IIO driver
elif data_sorce == 'zedADC':
    print('Data source: acquire from ADC via ZedBoard')

    iio_rx_buff_size = 4 * 1024 * 1024  # samples -> default 4194304
    iio_dma_buff_size = 4 * iio_rx_buff_size  # bytes -> default 16777216
    zed_RX_stream = zedADC_buff
    zedboard_filepath = '../mnt/samples.dat'
    windows_filepath = ''

    # Create an SSH client
    print('Opening the SSH connection...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the Linux PC
        ssh.connect(host, port, username, password)
        print('SSH connection successful!')

        print('Configuring the clock...')
        # Execute the command
        stdin, stdout, stderr = ssh.exec_command('ad4080_update_clks.sh 40')
        # Print the output of the command
        print(stdout.read().decode())
        print('Clock configured successfully!')

        print('Checking temp RAM drive...')
        # Execute the 'df' command to check if the temporary file system is mounted on '/mnt'
        stdin, stdout, stderr = ssh.exec_command('df -h')
        # Read the output of the command
        output = stdout.read().decode()
        print(output)

        # Check if '/mnt' is in the output
        if '/mnt' not in output:
            # Execute the command
            stdin, stdout, stderr = ssh.exec_command('mount -t tmpfs -o size=400m tmpfs /mnt')
            # Check if everything was ok
            error = stderr.read().decode()
            if error:
                print("Error occurred:", error)
            else:
                print('RAM drive created successfully!')
        else:
            print('RAM drive already exists!\n')

        # Execute the command
        stdin, stdout, stderr = ssh.exec_command('iio_readdev -u local: -b ' + str(iio_rx_buff_size) + ' -s ' + str(
            zed_RX_stream) + ' ad4080 > ../mnt/samples.dat')
        # Check if everything was ok
        error = stderr.read().decode()
        if 'Success (0)' in error:
            print("Samples Acquired successfully!")
        else:
            print("Error occurred:", error)

        # Transfer the file from the zedboard
        # Create SCP client
        scp = ssh.open_sftp()
        # Copy the file from zedboard to Windows
        scp.get('/mnt/samples.dat', 'samples_zedADC.dat')

        with open('samples.dat', 'rb') as file:
            data = np.frombuffer(file.read(), dtype=np.int32)

        # Check if there was any error during command execution
        # error = stderr.read().decode()
        # if error:
        #    raise Exception(f"Command execution error: {error}")

    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your username and password.")
    except paramiko.SSHException as ssh_exception:
        print(f"SSH connection error: {str(ssh_exception)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        # Close the SCP and SSH clients
        scp.close()
        ssh.close()

# Analizing the data
data_label = 'test'
adc_res = 20
max_full_scale = 2 ** (adc_res - 1)
min_full_scale = 2 ** (adc_res - 1) * (-1)

###### Print signal parameters ######
print('\n')
print('############ Config checks ############\n')
print('Number of samples:', data.size)
print('Maximum DN:', np.max(data), '->', format(np.max(data) / max_full_scale * 100, '.2f'), '%FS')
print('Maximum DN position:', np.argmax(data))
print('Max value vicinity:', data[np.argmax(data) - 10:np.argmax(data) + 11])
print('Minimum DN:', np.min(data), '->', format(np.min(data) / min_full_scale * 100, '.2f'), '%FS')
print('Minimum DN position:', np.argmin(data))
print('Min value vicinity:', data[np.argmin(data) - 10:np.argmin(data) + 11])
print('\n')



# Trimming the arrays
trim_begin = 0
trim_end = 1000000
fft_zoom = 1000  # auxiliary variable to help 'zooming' in the frequency axis

# trimming to speedup tests
# data = data[trim_begin:trim_end]

# Calculating the FFT

NT = data.size
w = windows.blackmanharris(NT)
data_w = data / (2 ** 19) * w
data_wf = fft(data_w, norm='forward')
xf = fftfreq(data.size, d=1 / ADC_sf)  # defining the frequency axis scale

print('Strongest freq component:', format(xf[np.argmax(np.abs(data_wf))], '.3f'), 'Hz')

with plt.ioff():
    fig, axs = plt.subplots(nrows=3, ncols=1, sharex=False, sharey=False)

axs[0].plot(data, label=data_label)
axs[1].hist(data, bins=2 ** 10, edgecolor='tab:blue', label=data_label, histtype='step')
axs[2].semilogy(xf[0:NT // fft_zoom], np.abs(data_wf)[0:NT // fft_zoom],
                label=data_label)  # [0:N//2] -> plotting just the 1st half of the fft which represents the positive values

axs[0].set_xlabel('samples')
axs[1].set_xlabel('DN')
axs[2].set_xlabel('frequency [Hz]')

axs[0].set_ylabel('DN')
axs[1].set_ylabel('# of counts')
axs[2].set_ylabel('Amplitude [dB_FS]')

axs[0].set_title('Trace')
axs[1].set_title('Histogram')
axs[2].set_title('FFT')

axs[0].legend(loc='upper right')
axs[1].legend(loc='upper right')
axs[2].legend(loc='upper right')

axs[0].grid(True)
axs[1].grid(True)
axs[2].grid(True)

##### Define the formatter function for y-axis ticks

from matplotlib.ticker import FuncFormatter


def format_y_ticks(value, _):
    scaled_value = 20 * np.log10(value)
    return f'{scaled_value:g}'


# Apply the formatter to y-axis ticks
axs[2].yaxis.set_major_formatter(FuncFormatter(format_y_ticks))
#####


from matplotlib.ticker import FuncFormatter


def format_x_ticks(value, _):
    prefixes = ['p', 'n', 'u', 'm', '', 'k', 'M', 'G', 'T']  # Add more prefixes if needed
    if value == 0:
        prefix_index = 4
    else:
        prefix_index = int(np.floor(np.log10(abs(value)) / 3)) + 4
    prefix = prefixes[prefix_index]
    scaled_value = value / 10 ** ((prefix_index - 4) * 3)
    return f'{scaled_value:g}{prefix}'


# Apply the formatter to x-axis ticks
axs[0].xaxis.set_major_formatter(FuncFormatter(format_x_ticks))
axs[1].xaxis.set_major_formatter(FuncFormatter(format_x_ticks))
axs[2].xaxis.set_major_formatter(FuncFormatter(format_x_ticks))
#####

fig.set_figheight(8)
fig.set_figwidth(8)
fig.tight_layout()

disconnect_zoom = zoom_factory(axs[0])
disconnect_zoom = zoom_factory(axs[1])
disconnect_zoom = zoom_factory(axs[2])
# Enable scrolling and panning with the help of MPL
# Interactions library function like panhandler.
pan_handler = panhandler(fig)
#display(fig.canvas)
plt.show()
