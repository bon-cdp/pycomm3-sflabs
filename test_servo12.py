from pycomm3 import CIPDriver, Services
import struct
import time

DRIVE_IP = '192.168.1.10'

# --- ADDRESSES ---
CIP_ACCESS_EXCL  = (101, 1, 13) 
CIP_CONTROL_WORD = (127, 1, 1)  
CIP_STATUS_WORD  = (127, 1, 2)  
CIP_OP_MODE      = (127, 1, 3)  
CIP_JOG_ACT      = (127, 1, 9)  
CIP_JOG_VEL      = (141, 1, 5)  

def get_status(drive):
    """Reads and returns the Status Word (Integer)."""
    resp = drive.generic_message(
        service=Services.get_attribute_single,
        class_code=CIP_STATUS_WORD[0], instance=CIP_STATUS_WORD[1], attribute=CIP_STATUS_WORD[2],
        connected=True, unconnected_send=False
    )
    return int.from_bytes(resp.value, 'little') if resp else None

def wait_for_bit(drive, bit, target_value, timeout=3.0):
    """Waits for a specific bit in the Status Word to match the target."""
    start = time.time()
    while (time.time() - start) < timeout:
        status = get_status(drive)
        if status is None: continue
        
        # Check specific bit
        current_bit = (status >> bit) & 1
        if current_bit == target_value:
            return True
        time.sleep(0.1)
    return False

def write_param(drive, address, value, data_type='UINT', name="Param"):
    if data_type == 'INT': payload = struct.pack('<h', value)
    elif data_type == 'DINT': payload = struct.pack('<i', value)
    else: payload = struct.pack('<H', value)
        
    resp = drive.generic_message(
        service=Services.set_attribute_single,
        class_code=address[0], instance=address[1], attribute=address[2],
        request_data=payload, connected=True, unconnected_send=False, name=name
    )
    if not resp:
        print(f" [X] Error writing {name}: {resp.error}")
        return False
    print(f" [O] Success: Set {name} to {value}")
    return True

def main():
    with CIPDriver(DRIVE_IP) as drive:
        print(f"--- CONNECTED TO {DRIVE_IP} ---")
        
        # 1. SETUP & CLAIM
        print("\n1. Setup...")
        write_param(drive, CIP_ACCESS_EXCL, 1, 'UINT', "AccessExcl")
        write_param(drive, CIP_OP_MODE, -1, 'INT', "Mode Jog (-1)")
        write_param(drive, CIP_JOG_VEL, 1000, 'DINT', "Jog Vel (1000)") # Higher speed to see it

        # 2. ENABLE SEQUENCE (With Verification)
        print("\n2. Enabling Power Stage...")
        
        # A. Shutdown -> Ready to Switch On
        write_param(drive, CIP_CONTROL_WORD, 0x06, 'UINT', "Shutdown")
        if not wait_for_bit(drive, 0, 1): # Bit 0 = ReadyToSwitchOn
            print(" [!] Failed to reach 'Ready to Switch On'")
            return

        # B. Switch On -> Switched On
        write_param(drive, CIP_CONTROL_WORD, 0x07, 'UINT', "Switch On")
        if not wait_for_bit(drive, 1, 1): # Bit 1 = SwitchedOn
            print(" [!] Failed to reach 'Switched On'")
            return

        # C. Enable -> Operation Enabled
        write_param(drive, CIP_CONTROL_WORD, 0x0F, 'UINT', "Enable Operation")
        print("    Waiting for Magnetization...")
        if wait_for_bit(drive, 2, 1): # Bit 2 = OperationEnabled
            print(" [!] DRIVE IS ENABLED (Status ending in x37).")
            print("     You should hear the motor whine now.")
        else:
            print(" [X] Drive refused Enable. Check Status Word.")
            print(f"     Final Status: {hex(get_status(drive))}")
            return

        # 3. MOTION (Retried)
        print("\n3. Starting Motion...")
        # Retry loop for the connection failure
        for attempt in range(3):
            print(f"    Attempt {attempt+1}: Sending Jog Trigger...")
            # Write 5 (Bit 0 Pos + Bit 2 Fast)
            if write_param(drive, CIP_JOG_ACT, 5, 'UINT', "JOG TRIGGER"):
                print("    >>> MOVING <<<")
                break
            time.sleep(0.5)
        
        time.sleep(4) # Let it spin

        # 4. STOP
        print("\n4. Stopping...")
        write_param(drive, CIP_JOG_ACT, 0, 'UINT', "Jog Stop")
        time.sleep(0.5)
        write_param(drive, CIP_CONTROL_WORD, 0x00, 'UINT', "Disable")
        
        # Release lock
        write_param(drive, CIP_ACCESS_EXCL, 0, 'UINT', "Release Access")
        print("Done.")

if __name__ == '__main__':
    main()
