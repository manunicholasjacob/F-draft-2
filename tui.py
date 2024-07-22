import curses
import sbr
import device_control
from datetime import datetime
import gpu_burn_script
import time
import run_629_diag
import itertools
import threading

def main(stdscr):
    curses.echo()

    # Colors and border setup
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
    stdscr.bkgd(curses.color_pair(1))

    # Function to display a box with a title
    def display_box(window, y, x, height, width, title=""):
        window.attron(curses.color_pair(2))
        window.border(0)
        window.addstr(0, 2, f' {title} ')
        window.attroff(curses.color_pair(2))
        window.refresh()

    # Function for Scrollability on the pad
    def scroll_output(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos):
        scroll_pad = pad_pos
        cmd = ''
        while True:
            cmd = window.getch()
            if cmd == ord('q'): break
            if cmd == curses.KEY_DOWN:
                if scroll_pad < pad_pos: scroll_pad += 1
                window.refresh(scroll_pad, 0, window_offset_y, window_offset_x, min(curses.LINES-1, window_offset_y + window_height - 3), min(curses.COLS-1, window_offset_x + window_width - 5))
            elif cmd == curses.KEY_UP:
                if scroll_pad > 0: scroll_pad -= 1
                window.refresh(scroll_pad, 0, window_offset_y, window_offset_x, min(curses.LINES-1, window_offset_y + window_height - 3), min(curses.COLS-1, window_offset_x + window_width - 5))

    # Display available slot numbers
    slot_numbers = sbr.get_slot_numbers()
    gpu_info_list = gpu_burn_script.gpu_traverse_up()

    height = max(len(slot_numbers) + 4, len(gpu_info_list) + 5, 10)

    # slot_window_width = 30
    # slot_window = curses.newwin(height, slot_window_width, 1, 1)
    # display_box(slot_window, 1, 1, height, slot_window_width, "Available Slot Numbers")
    # slot_window.addstr(1, 2, 'Slot Number\tBDF'.expandtabs(5))
    # for i, slot in enumerate(slot_numbers):
    #     slot = slot.split(" : ")
    #     slot_window.addstr(i + 2, 2, '{:<14s} {:<10s}'.format(slot[0], slot[1]))
    # slot_window.refresh()

    # Display GPU information 
    gpu_window_height = height  
    gpu_window_width = 57
    gpu_window = curses.newwin(gpu_window_height, gpu_window_width, 1, 1)
    display_box(gpu_window, 1, 41, gpu_window_height, gpu_window_width, "GPU Info")
    gpu_window.addstr(2, 2, " GPU |   BDF   | Root Port | Slot | PSB | Connector ")
    gpu_window.addstr(3, 2, "----------------------------------------------------")
    for i, gpu_info in enumerate(gpu_info_list):
        # gpu_print = f"GPU {i}\t|\tBDF: {gpu_info[0]}\t|\tSlot: {gpu_info[1]}\t|\tRoot Port: {gpu_info[2]}\t|\tPSB {gpu_info[3]}"
        # gpu_print = f"  {i}  | {gpu_info[0]} |  {gpu_info[2]}  |  {gpu_info[1]}  |  {gpu_info[3]}  | {gpu_info[4]}"
        gpu_print = f"{i:^5}|{gpu_info[0]:^9}|{gpu_info[2]:^11}|{gpu_info[1]:^6}|{gpu_info[3]:^5}| {gpu_info[4]}"
        gpu_window.addstr(i+4, 2, gpu_print.expandtabs(3))
    gpu_window.refresh()

    # Create Output Window
    output_window_height = height + 21
    output_window_width = 53
    output_window = curses.newpad(10000, 53)
    output_window_left_corner = [gpu_window_width+2, 1]
    output_window_border = curses.newwin(output_window_height, output_window_width, output_window_left_corner[1], output_window_left_corner[0])
    display_box(output_window_border, 10, 41, height, gpu_window_width+3, "Output")
    pad_pos = 0

    # Collect user inputs
    input_window_height = 20
    input_window_width = 57
    input_window = curses.newwin(input_window_height-4, input_window_width-4, height + 4, 3)
    input_window_border = curses.newwin(input_window_height, input_window_width, height + 2, 1)
    display_box(input_window_border, height + 2, 1, input_window_height, input_window_width, "Command Line")

    input_window.addstr(0, 0, "Choose operation (s: SBR, g: GPU Burn, d: 629 Diag | comma separated): ")
    operations_input = input_window.getstr().decode().lower()
    operations = [operation.strip() for operation in operations_input.split(',')]

    all_valid = True
    for operation in operations:
        if operation not in ['s','g','d']: all_valid = False
    while not all_valid:
        input_window.clear()
        input_window.addstr(0, 0, "Invalid Input - (s: SBR, g: GPU Burn, d: 629 Diag | comma separated): ")
        operations_input = input_window.getstr().decode().lower()
        operations = [operation.strip() for operation in operations_input.split(',')]
        all_valid = True
        for operation in operations:
            if operation not in ['s','g','d']: all_valid = False

    input_window.addstr(3, 0, "Enter your password (sudo access): ")
    user_password = input_window.getstr().decode()

    for operation in operations:
        time.sleep(1.5)
        input_window.clear()
        if operation == 'g':
            input_window.addstr(0, 0, "GPU_Burn Settings")
            input_window.addstr(2, 0, "Run for 30 minutes at 95% (y/n): ")
            gpu_changesetting = input_window.getstr().decode()

            if gpu_changesetting == 'n':
                input_window.addstr(4, 0, "Run gpu_burn for how long (in seconds)?: ")
                gpu_run_time = input_window.getstr().decode()
                input_window.addstr(6, 0, "Run GPUs at what Percent?: ")
                gpu_percent = input_window.getstr().decode()
                notify = f"Run gpu_burn for {gpu_run_time} seconds at {gpu_percent}%"
            else:
                gpu_run_time = 1800
                gpu_percent = 95
                notify = "Run gpu_burn for 1800 seconds at 95%"

        elif operation == 's':
            input_window.addstr(0, 0, "SBR Settings")
            input_window.addstr(2, 0, "Number of Loops: ")
            inputnum_loops = int(input_window.getstr().decode())

            input_window.addstr(4, 0, "Do you want to kill on error? (y/n): ")
            kill = input_window.getstr().decode()

            input_window.addstr(6, 0, "Choose slot numbers to test (comma separated): ")
            slot_input = input_window.getstr().decode()
            slotlist = list(map(int, slot_input.split(',')))

    time.sleep(1)
    input_window.clear()
    line_pos = 0
    if 'g' in operations:
        gpu_pos = line_pos
        input_window.addstr(line_pos, 0, "[ ]\t".expandtabs(2) + notify)
        line_pos += 2
    if 'd' in operations:
        diag_pos = line_pos
        input_window.addstr(line_pos, 0, "[ ]\tRun 629 Diag".expandtabs(2))
        line_pos += 2
    if 's' in operations:
        sbr_pos = line_pos
        input_window.addstr(line_pos, 0, f"[ ]\tRun SBR for {inputnum_loops} loops on slot numbers {slotlist}".expandtabs(2))
        line_pos += 2
    input_window.refresh()
    time.sleep(1)
    input_window.addstr(15, 0, "Press any key to start the test...")
    input_window.refresh()
    input_window.getch()

    # Loading Circle
    done = False
    def animate(operation):
        for c in itertools.cycle(['|', '/', '-', '\\']):
            if done: break
            if operation == 'g':
                input_window.addstr(gpu_pos, 0, f"[{c}]\t".expandtabs(2) + notify)
            if operation == 'd':
                input_window.addstr(diag_pos, 0, f"[{c}]\tRun 629 Diag".expandtabs(2))
            if operation == 's':
                input_window.addstr(sbr_pos, 0, f"[{c}]\tRun SBR for {inputnum_loops} loops on slot numbers {slotlist}".expandtabs(2))
            input_window.refresh()
            time.sleep(0.1)

    # Execute Test in Order
    if 'g' in operations:
        input_window.move(15,0)
        input_window.clrtoeol()
        input_window.addstr(15, 0, "Running gpu_burn...")
        input_window.refresh()
        # gpu_burn_process = multiprocessing.Process(target=gpu_burn_script.check_replay, args=(gpu_percent, gpu_run_time, 4, [], 10, output_window, height + 3, 55, output_window_height, output_window_width, pad_pos))
        # gpu_burn_process.start()
        # while gpu_burn_process.is_alive():

        # gpu_burn_process.join()
        done = False
        t = threading.Thread(target=animate, args=('g'))
        t.start()
        pad_pos = gpu_burn_script.check_replay(gpu_percent, gpu_run_time, 4, [], 10, output_window, output_window_left_corner[1], output_window_left_corner[0], output_window_height, output_window_width, pad_pos)
        done = True
        input_window.addstr(gpu_pos, 0, "[x]\t".expandtabs(2) + notify)
        input_window.refresh()
        time.sleep(1.5)

    if 'd' in operations:
        input_window.move(15,0)
        input_window.clrtoeol()
        input_window.addstr(15, 0, "Running 629_diag...")
        pad_pos = gpu_burn_script.output_print(output_window, height + 3, 55, output_window_height, output_window_width, pad_pos, "\n\n\n\n\n\n\n\n\n\n")
        pad_pos = gpu_burn_script.output_print(output_window, height + 3, 55, output_window_height, output_window_width, pad_pos, "Running 629_diag...")
        input_window.refresh()
        done = False
        t = threading.Thread(target=animate, args=('d'))
        t.start()
        run_629_diag.main()
        pad_pos = gpu_burn_script.output_print(output_window, height + 3, 55, output_window_height, output_window_width, pad_pos, "629_Diag Finished Running")
        pad_pos = gpu_burn_script.output_print(output_window, height + 3, 55, output_window_height, output_window_width, pad_pos, "Output written to ./629_diag_output.txt")
        done = True
        input_window.addstr(diag_pos, 0, "[x]\tRun 629 Diag".expandtabs(2))
        input_window.refresh()
        time.sleep(1.5)
        
    if 's' in operations:
        device_window_height = 20
        device_window = curses.newwin(device_window_height, 107, height + 2, 1)
        display_box(device_window, height + 2, 2, device_window_height, 60, "Device Control Status")
        device_window.addstr(2, 2, "Setting error reporting to 0...")
        device_window.refresh()


        bdfs = device_control.get_all_bdfs()
        device_control.store_original_values(bdfs)
        device_control.process_bdfs(bdfs)

        device_window.addstr(5, 2, "Error reporting set to 0.")

        device_window.addstr(7, 2, "Running SBR tests...")
        tested_bdf_info = sbr.run_test(device_window, user_password, inputnum_loops, kill, slotlist)

        device_window.addstr(9, 2, "SBR tests running.")
        device_window.refresh()
        done = True

        device_window.addstr(11, 2, "Resetting device control registers...")
        device_window.refresh()

        device_control.reset_to_original_values()

        device_window.addstr(13, 2, "Device control registers reset to original values.")
        device_window.refresh()

    input_window.addstr(15, 0, "Generating Summary Window...")
    input_window.refresh()
    time.sleep(0.5)
    summary_window_height = 20
    summary_window_width = 107
    summary_window = curses.newwin(summary_window_height-4, summary_window_width-4, height + 4, 3)
    summary_window_border = curses.newwin(summary_window_height, summary_window_width, height + 2, 1)
    display_box(summary_window_border, height + 2, 1, summary_window_height, summary_window_width, "Test Summary - Press q to Quit")
    summary_window.clear()
    summary_window.refresh()
    summary_line_pos = 0

    if 'g' in operations:
        summary_window.addstr(summary_line_pos, 0, "GPU_BURN SUMMARY")
        summary_line_pos += 1
        with open("./gpu_burn_output.txt", "r") as gpu_burn_output:
            lines = gpu_burn_output.readlines()
        lines_to_summary = []
        for i, line in enumerate(lines):
            if 'GPU' in line:
                replays = int(lines[i+1].split(":")[-1].strip())
                rollovers = int(lines[i+2].split(":")[-1].strip())
                if replays > 0 or rollovers > 0:
                    lines_to_summary.append(line + f"{replays} replays and {rollovers}")
        if len(lines_to_summary) == 0:
            summary_window.addstr(summary_line_pos, 0, "PASS: No Replays Detected")
            summary_line_pos += 1
        else:
            for line in lines_to_summary:
                summary_window.addstr(summary_line_pos, 0, line)
                summary_line_pos += 1
        summary_line_pos += 1
        summary_window.refresh()

    if 'd' in operations:
        summary_window.addstr(summary_line_pos, 0, "629_DIAG SUMMARY")
        summary_line_pos += 1
        try:
            with open("./629_diag_output.txt", "r") as diag_output:
                lines = diag_output.readlines()
            test_complete = False
            for line in lines:
                if test_complete:
                    summary_window.addstr(summary_line_pos, 0, line)
                    summary_line_pos += 1
                if "Fieldiag Testing Completed" in line: test_complete = True
            if not test_complete:
                summary_window.addstr(summary_line_pos, 0, "Fieldiag Testing Failed - Check 629_diag_output.txt for more info")
                summary_line_pos += 1
        except Exception as e:
            summary_window.addstr(summary_line_pos, 0, "629-Diag Failed to Run")
            summary_line_pos += 1
        summary_line_pos += 1
        summary_window.refresh()

    if 's' in operations:
        summary_window.addstr(summary_line_pos, 0, "SBR SUMMARY")
        summary_line_pos += 1

        for slot, info in tested_bdf_info.items():
            summary_window.addstr(summary_line_pos, 0, f"Tested BDF: {slot}, Downstream BDF: {info['specific_bus_link']}")
            summary_line_pos += 1
            errors = info.get("errors", [])
            for error in errors:
                summary_window.addstr(summary_line_pos, 0, f"Reset Count: {error['reset_count']}")
                summary_window.addstr(summary_line_pos + 1, 0, f"Link Status: {error['link_status']}")
                summary_window.addstr(summary_line_pos + 2, 0, f"Link Capabilities: {error['link_capabilities']}")
                summary_window.addstr(summary_line_pos + 3, 0, f"Error Time: {error['error_time']}")
                summary_line_pos += 4
            summary_line_pos += 1

        try:
            with open("./output.txt", "r") as file:
                lines = file.readlines()

            start_time = next(line for line in lines if line.startswith("Start Time:")).split(": ", 1)[1].strip()
            end_time = next(line for line in lines if line.startswith("End Time:")).split(": ", 1)[1].strip()
            slot_test_counts = next(line for line in lines if line.startswith("Slot Test Counts:")).split(": ", 1)[1].strip()

            def print_with_rollover(input, summary_line_pos):
                print_width = summary_window_width - 4
                rollover_number = int(len(input) / print_width)
                for i in range(rollover_number):
                    summary_window.addstr(summary_line_pos, 0, input[print_width * i:print_width * (i + 1)])
                    summary_line_pos += 1
                summary_window.addstr(summary_line_pos, 0, input[print_width * rollover_number:])
                summary_line_pos += 1
                return summary_line_pos

            summary_line_pos = print_with_rollover(f"Start Time: {start_time}", summary_line_pos)
            summary_line_pos = print_with_rollover(f"End Time: {end_time}", summary_line_pos)
            summary_line_pos = print_with_rollover(f"Slot Test Counts: {slot_test_counts}", summary_line_pos)

        except Exception as e:
            summary_window.addstr(summary_line_pos, 0, f"Error reading summary: {str(e)}")
        summary_window.refresh()

    curses.cbreak()  # Switch off buffered input mode
    curses.noecho()  # Disable automatic echoing of keys

    while True:
        quit = summary_window.getch()
        if quit == ord('q'): break

curses.wrapper(main)
