"""Inspect HMA VPN window UI tree to find the connect button."""
import uiautomation as auto

print("Searching for HMA VPN window...")
w = auto.WindowControl(searchDepth=1, SubName='HMA', searchWaitTime=5)
if not w.Exists(0):
    print("ERROR: HMA VPN window not found!")
    exit(1)

print(f"Found window: {w.Name!r}")
print(f"Window rect: {w.BoundingRectangle}")
print()

def dump_tree(ctrl, indent=0):
    """Recursively dump UI element tree."""
    prefix = "  " * indent
    name = ctrl.Name or ""
    aid = ctrl.AutomationId or ""
    ctype = ctrl.ControlTypeName or ""
    cls = ctrl.ClassName or ""
    rect = ctrl.BoundingRectangle

    info = f"{prefix}{ctype}: Name={name!r}"
    if aid:
        info += f" AutoId={aid!r}"
    if cls:
        info += f" Class={cls!r}"
    if rect:
        info += f" Rect=({rect.left},{rect.top},{rect.right},{rect.bottom})"
    print(info)

    # Limit depth to avoid infinite recursion
    if indent < 8:
        try:
            children = ctrl.GetChildren()
            for child in children:
                dump_tree(child, indent + 1)
        except Exception as e:
            print(f"{prefix}  [Error getting children: {e}]")

dump_tree(w)
