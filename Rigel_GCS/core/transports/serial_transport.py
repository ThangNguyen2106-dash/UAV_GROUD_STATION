from __future__ import annotations
import threading
from typing import Callable, Optional
import serial
class SerialTransport:
    def __init__(self, port:str, baudrate:int=115200, timeout:float=.2, on_data:Optional[Callable]=None):
        self.port=port; self.baudrate=int(baudrate); self.timeout=timeout; self.on_data=on_data
        self._serial=None; self._thread=None; self._running=False; self._lock=threading.Lock()
        self._rx_packets=self._rx_bytes=self._tx_packets=self._tx_bytes=0
    def start(self):
        if self._running:return
        self._serial=serial.Serial(self.port,self.baudrate,timeout=self.timeout); self._running=True
        self._thread=threading.Thread(target=self._rx_loop,name=f'RIGEL-SerialRX-{self.port}',daemon=True); self._thread.start()
        print(f'[SERIAL] Transport started | {self.port}@{self.baudrate}')
    def _rx_loop(self):
        while self._running:
            try:data=self._serial.read(4096) if self._serial else b''
            except (serial.SerialException,OSError) as e:
                if self._running: print(f'[SERIAL RX ERROR] {type(e).__name__}: {e}')
                break
            except Exception as e: print(f'[SERIAL RX ERROR] {type(e).__name__}: {e}'); continue
            if not data:continue
            with self._lock:self._rx_packets+=1; self._rx_bytes+=len(data)
            if self.on_data:
                try:self.on_data(data,self.port)
                except Exception as e:print(f'[SERIAL CALLBACK ERROR] {type(e).__name__}: {e}')
        self._running=False
    def send(self,data:bytes)->bool:
        if not isinstance(data,bytes):raise TypeError('SerialTransport.send() requires bytes')
        if self._serial is None or not self._serial.is_open:return False
        try:
            n=self._serial.write(data)
            with self._lock:self._tx_packets+=1; self._tx_bytes+=n
            return n==len(data)
        except (serial.SerialException,OSError) as e:print(f'[SERIAL TX ERROR] {type(e).__name__}: {e}'); return False
    def stop(self):
        self._running=False; ser=self._serial; self._serial=None
        if ser:
            try:ser.close()
            except Exception:pass
        if self._thread and self._thread.is_alive() and self._thread is not threading.current_thread():self._thread.join(timeout=1)
        self._thread=None; print(f'[SERIAL] Transport stopped | {self.port}')
    @property
    def running(self):return self._running
    def statistics(self):
        with self._lock:return {'port':self.port,'baudrate':self.baudrate,'running':self._running,'rx_packets':self._rx_packets,'rx_bytes':self._rx_bytes,'tx_packets':self._tx_packets,'tx_bytes':self._tx_bytes}
