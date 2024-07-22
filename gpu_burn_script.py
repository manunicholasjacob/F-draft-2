import subprocess
from datetime import datetime
import time
import curses

# Function to Print to Output Window
def output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = ""):
    pady, padx = window.getyx()
    window.addstr(pady+1, 0, input)
    if pady+1 > window_height-4:  
        pad_pos += int(len(input)/window_width) + 1
    window.refresh(pad_pos, 0, window_offset_y+1, window_offset_x, min(curses.LINES-1, window_offset_y + window_height - 3), min(curses.COLS-1, window_offset_x + window_width - 5))
    return pad_pos

def execute_shell_command(command):
    try:
        # Execute the shell command
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            # Successful execution
            return result.stdout.decode("utf-8").strip()  # Decode bytes to string
        else:
            # Error occurredhttps://github.com/manunicholasjacob/Testing/blob/main/getbdf2
            return f"Error: {result.stderr.decode('utf-8').strip()}"  # Decode bytes to string
    except Exception as e:
        return f"Error: {str(e)}"


def check_replay(gpu_percentage, burn_time, gpu_number, gpu_index, call_time, window, window_offset_y, window_offset_x, window_height, window_width, pad_pos):
    try:
        pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Starting gpu_burn...")
        # print("Starting gpu_burn...")
        # "> /dev/null" will not clutter stdout with gpu_burn's outputs
        gpu_process = subprocess.Popen(['./gpu_burn', '-d', '-m', f"{gpu_percentage}%", f"{burn_time}"], cwd="/home/NVIDIA/gpu_burn-1.1/gpu-burn", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "running in background")
        # print("running in background")
    except Exception as e:
        return f"Error: {str(e)}"

    # Periodically execute another command while './gpu_burn' is running
    replay_count = ""
    while gpu_process.poll() is None:
        now = datetime.now()
        # print("Current Timestamp:", now)
        pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"Current Timestamp: {now}")
        if(len(gpu_index) > 0):
            for index in gpu_index:
                # print(f"GPU {index}:")
                pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"GPU {index}:")
                replay_count = execute_shell_command(f"nvidia-smi -i {index} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: 
                    # print(line.strip())
                    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"{line.strip()}")
                    time.sleep(1)
        else:
            for i in range(gpu_number):
                # print(f"GPU {i}:")
                pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"GPU {i}:")
                replay_count = execute_shell_command(f"nvidia-smi -i {i} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: 
                    # print(line.strip())
                    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"{line.strip()}")
        # print()
        time.sleep(call_time) 

    # 'gpu_burn' has finished; you can perform any cleanup or final actions here
    # print("gpu_burn has completed.")
    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "gpu_burn has completed.")
    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Writing to gpu_burn_output.txt")
    bdf_read = execute_shell_command("nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader")
    bdf_read = bdf_read.split('\n')
    bdf_read = [":".join(line.split(':')[1:]) for line in bdf_read]
    with open("./gpu_burn_output.txt","w") as file:
        if(len(gpu_index) > 0):
            bdfs = []
            for i, bdf in enumerate(bdf_read):
                if i in gpu_index: bdfs.append(bdf)
            for i, bdf in enumerate(bdfs):
                file.write(f"GPU {gpu_index[i]} - " + bdf + ":\n")
                replay_count = execute_shell_command(f"nvidia-smi -i {gpu_index[i]} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: file.write(line.strip() + "\n")
                file.write("\n")
        else:
            for gpu_index_tag, bdf in enumerate(bdf_read): 
                file.write(f"GPU {gpu_index_tag} - " + bdf + ":\n")
                replay_count = execute_shell_command(f"nvidia-smi -i {gpu_index_tag} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: file.write(line.strip() + "\n")
                file.write("\n")
    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Writing to gpu_burn_log.txt")
    stdout, stderr = gpu_process.communicate()
    with open("./gpu_burn_log.txt", "w") as file:
        file.write(stdout.decode("utf-8"))

    return pad_pos








def run_command(command):
    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    if result.returncode != 0:
        raise Exception(f"Command failed with error: {stderr.decode('utf-8')}")
    return stdout.decode('utf-8')

def get_bdf_list():
    """ Get a list of all BDFs using lspci. """
    output = run_command("lspci")
    bdf_list = [line.split()[0] for line in output.splitlines()]
    return bdf_list

def get_vendor_bdf_list(vendor_id):
    """ Get a list of BDFs for a specific vendor using lspci. """
    output = run_command(f"lspci -d {vendor_id}:")
    vendor_bdf_list = [line.split()[0] for line in output.splitlines()]
    return vendor_bdf_list

def get_header_type(bdf):
    
    header_type = run_command(f"setpci -s {bdf} HEADER_TYPE")
    return header_type.strip()

def get_secondary_bus_number(bdf):
    """ Get the secondary bus number for a given BDF using setpci. """
    secondary_bus_number = run_command(f"setpci -s {bdf} SECONDARY_BUS")
    return secondary_bus_number.strip()

def read_slot_capabilities(bdf):
    try:
        slot_capabilities_output = subprocess.check_output(["setpci", "-s", bdf, "CAP_EXP+0X14.l"])
        return slot_capabilities_output.decode().strip()
    except subprocess.CalledProcessError:
        return None
    
def hex_to_binary(hex_string):
    binary_string = format(int(hex_string, 16), '032b')
    return binary_string

def gpu_traverse_up():
    # use nvidia-smi to get all the BDF of the GPUs
    bdf_read = execute_shell_command("nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader")
    bdf_read = bdf_read.split('\n')
    bdf_read = [":".join(line.split(':')[1:]) for line in bdf_read]
    gpu_bdf_list = [bdf.lower() for bdf in bdf_read]
    # get a list of all bdfs
    all_bdf_list = get_bdf_list()

    #get a list of all bdfs with header type 1
    header_bdf_list = [bdf for bdf in all_bdf_list if get_header_type(bdf).startswith("01")]

    physical_slot_numbers = []
    root_ports = []

    for i, gpu_bdf in enumerate(gpu_bdf_list):
        # get the bus for the gpu to compare to secondary bus number
        current_bus = gpu_bdf.split(":")[0]
        current_bdf = gpu_bdf
        port_found = False
        root_port_found = False
        # print(f"starting {i} GPU")

        # keep traversing up the tree until a valid physical port number is found
        while(not port_found and not root_port_found):
            # print(f"current bus: {current_bus}")
            upstream_connection = None

            # find the bdf with a secondary bus of our current bus
            for bdf in header_bdf_list:
                if get_secondary_bus_number(bdf) == current_bus:
                    upstream_connection = bdf 

            # if no upstream connection is found, we are at the root port, report and add to list
            if upstream_connection is None:
                # print(f"did not find a port with secondary bus as {current_bus}")
                root_port_found = True
                root_ports.append(current_bdf)
                break
            else:
                # print("Upstream Connection: " + f"{upstream_connection}")
                slot_capabilities = read_slot_capabilities(upstream_connection)
                # Extract the physical slot number from slot capabilities bits [31:19]
                # Convert from hex to binary to decimal
                slot_number = int(hex_to_binary(slot_capabilities)[:13], 2)

                # print(f"slot_number: {slot_number}")

            # We only want relevant physical ports to our system, in this case 21 to 29
            if(slot_number in range(21,29) and port_found is False):
                physical_slot_numbers.append(slot_number)
                port_found = True
            current_bdf = upstream_connection
            current_bus = upstream_connection.split(":")[0]
        
        # if a valid physical port was not found, report
        if(not port_found):
            physical_slot_numbers.append(-1)
    # gpu_streams = {gpuBDF : [physical_slot_numbers[i], root_ports[i]] for i, gpuBDF in enumerate(gpu_bdf_list)}
    psb_number = [1, 1, 2, 2, 4, 4, 3, 3] if len(gpu_bdf_list) > 4 else [1, 2, 4, 3]
    connector = ["R1", "SL13, SL14", "SL3, SL4", "SL7, SL8", "SL11, SL12", "R4", "SL1, SL2", "SL5, SL6"] if len(gpu_bdf_list) > 4 else ["R1", "SL7, SL8", "SL11, SL12", "SL5, SL6"]
    gpu_streams = [[gpuBDF, physical_slot_numbers[i], root_ports[i], psb_number[i], connector[i]] for i, gpuBDF in enumerate(gpu_bdf_list)]
    return gpu_streams

def main():
    check_replay(burn_time=10, gpu_number=4)
    # print(gpu_traverse_up())

if __name__ == "__main__":
    main()
