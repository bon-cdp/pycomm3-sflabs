import serial
import time

try:
    # Open port
    ser = serial.Serial('COM3', 115200, timeout=0.1) 
    print("Port Opened. Waiting for ESP32...")
    time.sleep(2) # Give ESP32 time to reboot
    
    while True:
        # Check if there are ANY bytes waiting in the buffer
        if ser.in_waiting > 0:
            raw_data = ser.readline()
            print(f"Raw Byte Stream: {raw_data}") # See exactly what is coming in
            
            try:
                clean_data = raw_data.decode('utf-8').strip()
                if clean_data:
                    print(f"Parsed Weight: {clean_data}")
            except:
                print("Decoding error (check baud rate)")
        else:
            # If nothing is happening, print a dot every second
            pass 

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'ser' in locals():
        ser.close()