import subprocess
from datetime import datetime
import time
import curses
import numpy as np
import functions

# Function to Print to Output Window
def output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = ""):
    pady, padx = window.getyx()
    window.addstr(pady+1, 0, input)
    if pady+1 > window_height-4:  
        pad_pos += int(len(input)/window_width) + 1
    window.refresh(pad_pos, 0, window_offset_y+1, window_offset_x, min(curses.LINES-1, window_offset_y + window_height - 3), min(curses.COLS-1, window_offset_x + window_width - 5))
    return pad_pos

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
                replay_count = functions.execute_shell_command(f"nvidia-smi -i {index} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: 
                    # print(line.strip())
                    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"{line.strip()}")
                    time.sleep(1)
        else:
            for i in range(gpu_number):
                # print(f"GPU {i}:")
                pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"GPU {i}:")
                replay_count = functions.execute_shell_command(f"nvidia-smi -i {i} -q|grep -i replay")
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
    bdf_read = functions.execute_shell_command("nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader")
    bdf_read = bdf_read.split('\n')
    bdf_read = [":".join(line.split(':')[1:]) for line in bdf_read]
    with open("./gpu_burn_output.txt","w") as file:
        if(len(gpu_index) > 0):
            bdfs = []
            for i, bdf in enumerate(bdf_read):
                if i in gpu_index: bdfs.append(bdf)
            for i, bdf in enumerate(bdfs):
                file.write(f"GPU {gpu_index[i]} - " + bdf + ":\n")
                replay_count = functions.execute_shell_command(f"nvidia-smi -i {gpu_index[i]} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: file.write(line.strip() + "\n")
                file.write("\n")
        else:
            for gpu_index_tag, bdf in enumerate(bdf_read): 
                file.write(f"GPU {gpu_index_tag} - " + bdf + ":\n")
                replay_count = functions.execute_shell_command(f"nvidia-smi -i {gpu_index_tag} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: file.write(line.strip() + "\n")
                file.write("\n")
    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Writing to gpu_burn_log.txt")
    stdout, stderr = gpu_process.communicate()
    with open("./gpu_burn_log.txt", "w") as file:
        file.write(stdout.decode("utf-8"))

    return pad_pos



def gpu_traverse_up():
    # get a list of all bdfs
    all_bdf_list = functions.get_bdf_list()

    try:
        # use nvidia-smi to get all the BDF of the GPUs
        bdf_read = functions.execute_shell_command("nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader")
        bdf_read = bdf_read.split('\n')
        bdf_read = [":".join(line.split(':')[1:]) for line in bdf_read]
        gpu_bdf_list = [bdf.lower() for bdf in bdf_read]
    except Exception as e:
        pass

    if len(gpu_bdf_list) == 0 or  gpu_bdf_list[0] == ' ':
        gpu_bdf_list = []
        for bdf in all_bdf_list:
            class_code_hex = functions.read_class_code(bdf)
            header_type = functions.get_header_type(bdf)
            if class_code_hex[:2] == "03" and header_type == "00": gpu_bdf_list.append(bdf)

    #get a list of all bdfs with header type 1
    header_bdf_list = [bdf for bdf in all_bdf_list if functions.get_header_type(bdf).startswith("01")]

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
                if functions.get_secondary_bus_number(bdf) == current_bus:
                    upstream_connection = bdf 

            # if no upstream connection is found, we are at the root port, report and add to list
            if upstream_connection is None:
                # print(f"did not find a port with secondary bus as {current_bus}")
                root_port_found = True
                root_ports.append(current_bdf)
                break
            else:
                # print("Upstream Connection: " + f"{upstream_connection}")
                slot_capabilities = functions.read_slot_capabilities(upstream_connection)
                # Extract the physical slot number from slot capabilities bits [31:19]
                # Convert from hex to binary to decimal
                slot_number = int(functions.hex_to_binary(slot_capabilities)[:13], 2)

                # print(f"slot_number: {slot_number}")

            # We only want relevant physical ports to our system, in this case 21 to 29
            if(slot_number in range(21,29) and port_found is False):
                physical_slot_numbers.append(slot_number)
                port_found = True
            current_bdf = upstream_connection
            current_bus = upstream_connection.split(":")[0]
        
        # if a valid physical port was not found, report
        if(not port_found):
            physical_slot_numbers.append(slot_number)
    
    # gpu_streams = {gpuBDF : [physical_slot_numbers[i], root_ports[i]] for i, gpuBDF in enumerate(gpu_bdf_list)}
    fryer_slots = [28, 24, 23, 27, 25, 21, 26, 22]
    psb_number = [1, 1, 2, 2, 4, 4, 3, 3]
    connector = ["R1", "SL13, SL14", "SL3, SL4", "SL7, SL8", "SL11, SL12", "R4", "SL1, SL2", "SL5, SL6"]

    gpu_streams = []
    for i, gpuBDF in enumerate(gpu_bdf_list):   
        if physical_slot_numbers[i] != 0:
            if physical_slot_numbers[i] in fryer_slots:
                info_index = fryer_slots.index(physical_slot_numbers[i])
                gpu_streams.append([gpuBDF, physical_slot_numbers[i], root_ports[i], psb_number[info_index], connector[info_index]])
            else:
                gpu_streams.append([gpuBDF, physical_slot_numbers[i], root_ports[i], "N/A", "N/A"])

    # gpu_streams = [[gpuBDF, physical_slot_numbers[i], root_ports[i], psb_number[i], connector[i]] for i, gpuBDF in enumerate(gpu_bdf_list)]
    return gpu_streams

def main():
    check_replay(burn_time=10, gpu_number=4)
    # print(gpu_traverse_up())

if __name__ == "__main__":
    main()
