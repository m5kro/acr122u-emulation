# m5kro - 2024
# Big thanks to the RFIDIOt project for the PN532 firmware print function
from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.scard import SCARD_SHARE_DIRECT

# Define the APDU commands
ACS_DISABLE_AUTO_POLL = ['ff', '00', '51', '3f', '00']
ACS_LED_ORANGE = ['ff', '00', '40', '0f', '04', '00', '00', '00', '00']
ACS_GET_READER_FIRMWARE = ['ff', '00', '48', '00', '00']
ACS_DIRECT_TRANSMIT = ['ff', '00', '00', '00']
GET_PN532_FIRMWARE = ['d4', '02']
TG_INIT_AS_TARGET = ['d4', '8c']
TG_GET_DATA = ['d4', '86']
TG_SET_DATA = ['d4', '8e']
ISO_OK = ['90', '00']

# Define the PN532 functions
PN532_OK = [0xD5, 0x03]
PN532_FUNCTIONS = {
    0x01: 'ISO/IEC 14443 Type A',
    0x02: 'ISO/IEC 14443 Type B',
    0x04: 'ISO/IEC 18092',
}

def to_bytes(hex_list):
    # Convert a list of hex strings to a list of bytes
    return [int(byte, 16) if isinstance(byte, str) else byte for byte in hex_list]

def send_apdu(connection, apdu_hex):
    # Send an APDU command and print the response
    apdu = to_bytes(apdu_hex)
    print(f"Sending APDU: {apdu}")
    try:
        response, sw1, sw2 = connection.transmit(apdu)
        print(f"Response: {response}")
        print(f"Status words: {sw1:02X} {sw2:02X}")
        
        if not response:
            print(f"No data returned, but status words: {sw1:02X} {sw2:02X}")
            return None, sw1, sw2

        return response, sw1, sw2

    except Exception as e:
        print(f"Exception during APDU transmission: {e}")
        return None, None, None

def pn532_print_firmware(data):
    # Print the PN532 firmware information Thanks to RFIDIOT for this code :)
    if data[:2] != PN532_OK:
        print('  Bad data from PN532:', data)
    else:
        print('       IC:', data[2])
        print('      Rev: %d.%d' % (data[3] >> 4, data[3] & 0x0F))
        print('  Support:', end=' ')
        support = data[4]
        spacing = ''
        for n in PN532_FUNCTIONS.keys():
            if support & n:
                print(spacing + PN532_FUNCTIONS[n])
                spacing = '           '

def main():
    # Get the list of available readers
    reader_list = readers()
    if not reader_list:
        print("No readers found")
        return

    # Use the first available reader
    reader = reader_list[0]
    print(f"Using reader: {reader}")

    # Create a connection to the reader
    connection = reader.createConnection()
    try:
        # Connect in direct mode with raw protocol
        connection.connect(protocol=CardConnection.RAW_protocol, mode=SCARD_SHARE_DIRECT)
        print("Connected to reader")

        # Begin self test commmands

        # Send the disable auto poll command
        _, sw1, sw2 = send_apdu(connection, ACS_DISABLE_AUTO_POLL)
        if sw1 == 0x90:
            print("Auto poll disabled successfully")
        else:
            print("Failed to disable auto poll")
            return

        # Send the LED orange command
        _, sw1, sw2 = send_apdu(connection, ACS_LED_ORANGE)
        if sw1 == 0x90:
            print("LED set to orange successfully")
        else:
            print("Failed to set LED to orange")
            return

        # Send the get reader firmware command
        response, sw1, sw2 = send_apdu(connection, ACS_GET_READER_FIRMWARE)
        response.append(sw1)
        response.append(sw2)
        try:
            firmware_version = ''.join(chr(b) for b in response)
            print(f"Reader firmware version: {firmware_version}")
        except Exception as e:
            print(f"Failed to get reader firmware: {e}")
            return

        # Send the direct transmit command with GET_PN532_FIRMWARE
        full_command = ACS_DIRECT_TRANSMIT + [len(GET_PN532_FIRMWARE)] + GET_PN532_FIRMWARE
        response, sw1, sw2 = send_apdu(connection, full_command)
        if sw1 == 0x90:
            pn532_print_firmware(response)
        else:
            print("Failed to get PN532 firmware")
            return

        # End self test commands

        # Begin emulation commands

        # Arguments for TG_INIT_AS_TARGET
        mode = '05' # 00 = Passive Only 01 = DEP Only 02 = PICC Only 05 = passive and picc
        sens_res = '0400' # 0400 or 0800 try both
        nfcid1t = '000000'
        sel_res = '20' # 40 = DEP 60 = DEP and PICC 20 = PICC
        nfcid2t = '0000000000000000'
        pad = '0000000000000000'
        system_code = '0000'
        nfcid3t = '00000000000000000000'
        general_bytes = ''
        historical_bytes = ''

        init_as_target_command = TG_INIT_AS_TARGET + to_bytes([mode]) + to_bytes(sens_res) + to_bytes(nfcid1t) + to_bytes(sel_res) + to_bytes(nfcid2t) + to_bytes(pad) + to_bytes(system_code) + to_bytes(nfcid3t) + [len(to_bytes(general_bytes))] + to_bytes(general_bytes) + [len(to_bytes(historical_bytes))] + to_bytes(historical_bytes)
        init_as_target_command = ACS_DIRECT_TRANSMIT + [len(init_as_target_command)] + init_as_target_command

        # Send the direct transmit command with TG_INIT_AS_TARGET
        response, sw1, sw2 = send_apdu(connection, init_as_target_command)
        if sw1 == None:
            print("TG_INIT_AS_TARGET command sent successfully")
        else:
            print("Failed to send TG_INIT_AS_TARGET command")
            return

        # Send the direct transmit command with TG_GET_DATA
        full_command = ACS_DIRECT_TRANSMIT + [len(TG_GET_DATA)] + TG_GET_DATA
        response, sw1, sw2 = send_apdu(connection, full_command)
        if sw1 == 0x90:
            print(f"TG_GET_DATA returned: {response}")
        else:
            print("Failed to get data with TG_GET_DATA")
            return

        # Send the direct transmit command with TG_SET_DATA and ISO_OK
        tg_set_data_command = TG_SET_DATA + ISO_OK
        full_command = ACS_DIRECT_TRANSMIT + [len(tg_set_data_command)] + tg_set_data_command
        response, sw1, sw2 = send_apdu(connection, full_command)
        if sw1 == 0x90:
            print("TG_SET_DATA command sent successfully")
        else:
            print("Failed to send TG_SET_DATA command")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
