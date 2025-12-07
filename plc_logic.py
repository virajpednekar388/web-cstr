# plc_logic.py
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

def read_plc_registers(ip='192.168.1.1', port=502, address=40001, count=4, device_id=1, timeout=3):
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
