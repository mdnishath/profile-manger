"""Measure exact button position from screenshot."""
# Window: 700x570
# OFF button toggle - the dark pill shape with X circle and "OFF" text
# The X circle center: approximately x=485, y=388
# The "OFF" text center: approximately x=565, y=388
# The entire toggle pill: from about (455, 365) to (615, 415)
# Toggle center: x=535, y=390

w, h = 700, 570

# Button measurements (estimated from screenshot)
btn_x = 535  # center of toggle pill
btn_y = 390  # center of toggle pill

pct_x = btn_x / w
pct_y = btn_y / h
print(f"Toggle button center: ({btn_x}, {btn_y})")
print(f"As percentage: X={pct_x:.3f} ({pct_x*100:.1f}%), Y={pct_y:.3f} ({pct_y*100:.1f}%)")
print()

# Also the X circle specifically (might be the clickable part)
circle_x = 485
circle_y = 388
print(f"X circle center: ({circle_x}, {circle_y})")
print(f"As percentage: X={circle_x/w:.3f} ({circle_x/w*100:.1f}%), Y={circle_y/h:.3f} ({circle_y/h*100:.1f}%)")
