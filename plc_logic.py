# # plc_logic.py
# new backend code start here

# plc_logic.py
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# ------------ Default PLC Config ------------
DEFAULT_IP = "192.168.1.100"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1

# Your confirmed mapping (N13 file):
# N13:0  -> 40001 (Temp)
# N13:1  -> 40002 (Pressure)
# N13:10 -> 40011 (Valve1 demand %)
# N13:11 -> 40012 (Valve2 demand %)
VALVE1_REG = 40011
VALVE2_REG = 40012


def is_plc_connected(ip=DEFAULT_IP, port=DEFAULT_PORT, timeout=2):
    """
    Returns True if PLC TCP connection is successful, else False
    """
    client = ModbusTcpClient(host=ip, port=port, timeout=timeout)
    try:
        return client.connect()
    except Exception:
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


def read_plc_registers(ip=DEFAULT_IP, port=DEFAULT_PORT, address=40001, count=4, device_id=DEFAULT_SLAVE_ID, timeout=3):
    """
    Read Modbus holding registers and return a list of register values or None on failure.
    address uses 4xxxx style (e.g., 40001). We convert to 0-based.
    """
    client = ModbusTcpClient(host=ip, port=port, timeout=timeout)
    try:
        if not client.connect():
            print(f"[plc_logic] Failed to connect to PLC {ip}:{port}")
            return None

        address_zero_based = address - 40001

        # pymodbus 3.x uses 'slave=' (not device_id=)
        response = client.read_holding_registers(
            address=address_zero_based,
            count=count,
            slave=device_id
        )

        if not response or response.isError():
            print("[plc_logic] Error reading registers:", response)
            return None

        return getattr(response, "registers", None)

    except ModbusException as e:
        print("[plc_logic] Modbus exception:", e)
        return None
    except Exception as e:
        print("[plc_logic] Exception:", e)
        return None
    finally:
        try:
            client.close()
        except Exception:
            pass


def Modbus_Write(register, value, ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID, timeout=3):
    """
    Write ONE Modbus holding register (4xxxx style, e.g., 40011).
    Returns a success string or error string (kept similar to your original).
    """
    client = ModbusTcpClient(ip, port=port, timeout=timeout)

    if not client.connect():
        return "Failed to connect to Modbus server"

    try:
        address_to_write = register - 40001  # Convert 40001 -> 0 based
        write_response = client.write_register(
            address=address_to_write,
            value=int(value),
            slave=slave_id
        )

        if not write_response or write_response.isError():
            return f"Error writing data: {write_response}"

        return f"Value {value} written to register {register} successfully!"

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        client.close()


# ---------------- Valve helpers (SCADA -> PLC) ----------------

def set_valve1_percent(percent, ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID):
    """
    Valve1 demand (%). SCADA writes to N13:10 -> 40011.
    """
    p = max(0, min(100, int(percent)))
    return Modbus_Write(VALVE1_REG, p, ip=ip, port=port, slave_id=slave_id)


def set_valve2_percent(percent, ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID):
    """
    Valve2 demand (%). SCADA writes to N13:11 -> 40012.
    """
    p = max(0, min(100, int(percent)))
    return Modbus_Write(VALVE2_REG, p, ip=ip, port=port, slave_id=slave_id)


def valve1_open(ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID):
    return set_valve1_percent(100, ip=ip, port=port, slave_id=slave_id)


def valve1_close(ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID):
    return set_valve1_percent(0, ip=ip, port=port, slave_id=slave_id)


def valve2_open(ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID):
    return set_valve2_percent(100, ip=ip, port=port, slave_id=slave_id)


def valve2_close(ip=DEFAULT_IP, port=DEFAULT_PORT, slave_id=DEFAULT_SLAVE_ID):
    return set_valve2_percent(0, ip=ip, port=port, slave_id=slave_id)



# from pymodbus.client import ModbusTcpClient
# from pymodbus.exceptions import ModbusException

# def is_plc_connected(ip="192.168.1.100", port=502, timeout=2):
#     """
#     Returns True if PLC TCP connection is successful, else False
#     """
#     client = ModbusTcpClient(host=ip, port=port, timeout=timeout)
#     try:
#         return client.connect()
#     except Exception:
#         return False
#     finally:
#         try:
#             client.close()
#         except Exception:
#             pass


# def read_plc_registers(ip='192.168.1.100', port=502, address=40001, count=4, device_id=1, timeout=3):
#     """
#     Read Modbus holding registers and return a list of register values or None on failure.
#     """
#     client = ModbusTcpClient(host=ip, port=port, timeout=timeout)
#     try:
#         if not client.connect():
#             print(f"[plc_logic] Failed to connect to PLC {ip}:{port}")
#             return None

#         address_zero_based = address - 40001
#         response = client.read_holding_registers(address=address_zero_based, count=count, device_id=device_id)

#         if not response or response.isError():
#             print("[plc_logic] Error reading registers:", response)
#             return None

#         return getattr(response, "registers", None)
#     except ModbusException as e:
#         print("[plc_logic] Modbus exception:", e)
#         return None
#     except Exception as e:
#         print("[plc_logic] Exception:", e)
#         return None
#     finally:
#         try:
#             client.close()
#         except Exception:
#             pass

# def Modbus_Write(register, value):
#     DEVICE_IP = '192.168.1.1'  # Replace with your PLC's actual IP
#     DEVICE_PORT = 502

#     client = ModbusTcpClient(DEVICE_IP, port=DEVICE_PORT)

#     if not client.connect():
#         return "Failed to connect to Modbus server"
    
#     try:
#         address_to_write = register - 40001  # Convert Modbus address to zero-based index
#         write_response = client.write_register(address=address_to_write, value=value, slave=1)

#         if write_response.isError():
#             return f"Error writing data: {write_response}"
#         return f"Value {value} written to register {register} successfully!"
    
#     except Exception as e:
#         return f"Error: {str(e)}"
    
#     finally:
#         client.close()
# # -----------------code ends ----------------

