"""Start VPN, wait, then take screenshot."""
import subprocess
import time
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
SW_RESTORE = 9

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                 ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

# Start VPN
vpn_path = r'C:\Program Files\Privax\HMA VPN\Vpn.exe'
print(f"Starting: {vpn_path}")
subprocess.Popen([vpn_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("Waiting 15s for window...")
time.sleep(15)

# Find by class GeniumWindow
found = [None]
def _cb(hwnd, _lp):
    if user32.IsWindowVisible(hwnd):
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        if cls_buf.value == 'GeniumWindow':
            found[0] = hwnd
            return False
    return True

user32.EnumWindows(WNDENUMPROC(_cb), 0)

if not found[0]:
    print("GeniumWindow not found! Trying title search...")
    def _cb2(hwnd, _lp):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value.strip() == 'HMA VPN' and user32.IsWindowVisible(hwnd):
                found[0] = hwnd
                return False
        return True
    user32.EnumWindows(WNDENUMPROC(_cb2), 0)

if not found[0]:
    print("HMA VPN window NOT found!")
    exit(1)

hwnd = found[0]
user32.ShowWindow(hwnd, SW_RESTORE)
time.sleep(1)
user32.SetForegroundWindow(hwnd)
time.sleep(1)

rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w = rect.right - rect.left
h = rect.bottom - rect.top
print(f"Window: pos=({rect.left},{rect.top}) size={w}x{h}")

# Take screenshot
ps_cmd = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap({w}, {h})
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen({rect.left}, {rect.top}, 0, 0, (New-Object System.Drawing.Size({w}, {h})))
$bmp.Save("E:\\mailexus-advanced\\hma_screenshot.png")
$g.Dispose()
$bmp.Dispose()
'''
subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True, timeout=10)
print("Screenshot saved to E:\\mailexus-advanced\\hma_screenshot.png")
