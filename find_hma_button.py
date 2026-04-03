"""Find ALL HMA windows and take screenshot of the main one."""
import ctypes
import ctypes.wintypes
import subprocess

user32 = ctypes.windll.user32

WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM,
)

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long), ("top", ctypes.c_long),
        ("right", ctypes.c_long), ("bottom", ctypes.c_long),
    ]

SW_RESTORE = 9

# Find ALL windows with HMA in title
all_hma = []
def _cb(hwnd, _lp):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if 'HMA' in buf.value.upper():
            visible = user32.IsWindowVisible(hwnd)
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            all_hma.append({
                'hwnd': hwnd,
                'title': buf.value,
                'visible': visible,
                'x': rect.left, 'y': rect.top,
                'w': w, 'h': h,
            })
    return True

user32.EnumWindows(WNDENUMPROC(_cb), 0)

print(f"Found {len(all_hma)} HMA window(s):")
for i, win in enumerate(all_hma):
    print(f"  [{i}] hwnd={win['hwnd']} title={win['title']!r} "
          f"visible={win['visible']} pos=({win['x']},{win['y']}) "
          f"size={win['w']}x{win['h']}")

# Find the main window (largest, visible, on-screen)
main_win = None
for win in all_hma:
    if win['w'] > 200 and win['h'] > 200 and win['x'] > -1000:
        main_win = win
        break

if not main_win:
    # Try restoring the first visible one
    for win in all_hma:
        if win['visible']:
            print(f"\nRestoring window: {win['title']!r}...")
            user32.ShowWindow(win['hwnd'], SW_RESTORE)
            import time
            time.sleep(1)
            user32.SetForegroundWindow(win['hwnd'])
            time.sleep(1)
            # Re-read rect
            rect = RECT()
            user32.GetWindowRect(win['hwnd'], ctypes.byref(rect))
            win['x'] = rect.left
            win['y'] = rect.top
            win['w'] = rect.right - rect.left
            win['h'] = rect.bottom - rect.top
            print(f"  After restore: pos=({win['x']},{win['y']}) size={win['w']}x{win['h']}")
            if win['w'] > 200 and win['h'] > 200:
                main_win = win
                break

if not main_win:
    print("\nNo suitable main HMA window found!")
    exit(1)

print(f"\nMain window: {main_win['title']!r} pos=({main_win['x']},{main_win['y']}) size={main_win['w']}x{main_win['h']}")

# Take screenshot
rect_l, rect_t = main_win['x'], main_win['y']
w, h = main_win['w'], main_win['h']

print(f"\nClick position candidates (center X={rect_l + w//2}):")
for pct_y in [0.45, 0.50, 0.55, 0.58, 0.60, 0.63, 0.65, 0.68, 0.70, 0.75, 0.80]:
    cx = rect_l + int(w * 0.50)
    cy = rect_t + int(h * pct_y)
    print(f"  Y={pct_y:.2f} -> ({cx}, {cy})  [pixel from top: {int(h * pct_y)}]")

ps_cmd = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap({w}, {h})
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen({rect_l}, {rect_t}, 0, 0, (New-Object System.Drawing.Size({w}, {h})))
$bmp.Save("E:\\mailexus-advanced\\hma_screenshot.png")
$g.Dispose()
$bmp.Dispose()
Write-Host "Screenshot saved to E:\\mailexus-advanced\\hma_screenshot.png"
'''
result = subprocess.run(['powershell', '-Command', ps_cmd],
                      capture_output=True, text=True, timeout=10)
print(result.stdout.strip())
if result.stderr.strip():
    print(f"PS Error: {result.stderr.strip()[:200]}")
