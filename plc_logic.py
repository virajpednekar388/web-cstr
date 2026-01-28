# plc_logic.py
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

def is_plc_connected(ip="192.168.1.100", port=502, timeout=2):
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


def read_plc_registers(ip='192.168.1.100', port=502, address=40001, count=4, device_id=1, timeout=3):
    """
    Read Modbus holding registers and return a list of register values or None on failure.
    """
    client = ModbusTcpClient(host=ip, port=port, timeout=timeout)
    try:
        if not client.connect():
            print(f"[plc_logic] Failed to connect to PLC {ip}:{port}")
            return None

        address_zero_based = address - 40001
        response = client.read_holding_registers(address=address_zero_based, count=count, device_id=device_id)

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

def Modbus_Write(register, value):
    DEVICE_IP = '192.168.1.1'  # Replace with your PLC's actual IP
    DEVICE_PORT = 502

    client = ModbusTcpClient(DEVICE_IP, port=DEVICE_PORT)

    if not client.connect():
        return "Failed to connect to Modbus server"
    
    try:
        address_to_write = register - 40001  # Convert Modbus address to zero-based index
        write_response = client.write_register(address=address_to_write, value=value, slave=1)

        if write_response.isError():
            return f"Error writing data: {write_response}"
        return f"Value {value} written to register {register} successfully!"
    
    except Exception as e:
        return f"Error: {str(e)}"
    
    finally:
        client.close()
# -----------------code ends ----------------
