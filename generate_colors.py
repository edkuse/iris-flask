import colorsys
import os

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(
        max(0, min(255, int(rgb[0]))),
        max(0, min(255, int(rgb[1]))),
        max(0, min(255, int(rgb[2])))
    )

def rgb_to_hsl(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return (h, s, l)

def hsl_to_rgb(hsl):
    h, s, l = hsl
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))

def generate_color_shades(base_color):
    rgb = hex_to_rgb(base_color)
    hsl = rgb_to_hsl(rgb)
    
    shades = {}
    
    # Generate lighter shades (100-400)
    for i in range(1, 5):
        shade_num = i * 100
        lightness_factor = 0.1 + (0.15 * (5 - i))
        new_lightness = min(1.0, hsl[2] + lightness_factor)
        new_hsl = (hsl[0], max(0, hsl[1] - 0.05 * i), new_lightness)
        new_rgb = hsl_to_rgb(new_hsl)
        shades[shade_num] = rgb_to_hex(new_rgb)
    
    # Base color (500)
    shades[500] = base_color
    
    # Generate darker shades (600-900)
    for i in range(1, 5):
        shade_num = 500 + (i * 100)
        darkness_factor = 0.06 * i
        new_lightness = max(0, hsl[2] - darkness_factor)
        new_saturation = min(1.0, hsl[1] + 0.05 * i)
        new_hsl = (hsl[0], new_saturation, new_lightness)
        new_rgb = hsl_to_rgb(new_hsl)
        shades[shade_num] = rgb_to_hex(new_rgb)
    
    return shades

# Your custom colors
colors = {
    'primary': '#00388f',
    'secondary': '#686e74',
    'info': '#0074b3',
    'success': '#2d7e24',
    'danger': '#c70032',
    'warning': '#ea712f',
    'dark': '#25303a',
    'light': '#f3f4f6',
}

# Ensure the directory exists
os.makedirs('static/css', exist_ok=True)

# Generate CSS variables
css_variables = ":root {\n"
utility_classes = ""

# Border width utilities (similar to Tailwind's defaults)
border_widths = {
    '': '1px',      # Default border width
    '-0': '0px',
    '-2': '2px',
    '-4': '4px',
    '-8': '8px',
}

for color_name, hex_value in colors.items():
    shades = generate_color_shades(hex_value)
    
    for shade_num, shade_hex in shades.items():
        variable_name = f"--color-{color_name}-{shade_num}"
        css_variables += f"  {variable_name}: {shade_hex};\n"
        
        # Generate utility classes for background colors
        utility_classes += f".bg-{color_name}-{shade_num} {{ background-color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:bg-{color_name}-{shade_num}:hover {{ background-color: var({variable_name}); }}\n"
        
        # Generate utility classes for text colors
        utility_classes += f".text-{color_name}-{shade_num} {{ color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:text-{color_name}-{shade_num}:hover {{ color: var({variable_name}); }}\n"
        
        # Generate utility classes for border colors
        # Standard border (all sides)
        utility_classes += f".border-{color_name}-{shade_num} {{ border-color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:border-{color_name}-{shade_num}:hover {{ border-color: var({variable_name}); }}\n"
        
        # Border top
        utility_classes += f".border-t-{color_name}-{shade_num} {{ border-top-color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:border-t-{color_name}-{shade_num}:hover {{ border-top-color: var({variable_name}); }}\n"
        
        # Border right
        utility_classes += f".border-r-{color_name}-{shade_num} {{ border-right-color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:border-r-{color_name}-{shade_num}:hover {{ border-right-color: var({variable_name}); }}\n"
        
        # Border bottom
        utility_classes += f".border-b-{color_name}-{shade_num} {{ border-bottom-color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:border-b-{color_name}-{shade_num}:hover {{ border-bottom-color: var({variable_name}); }}\n"
        
        # Border left
        utility_classes += f".border-l-{color_name}-{shade_num} {{ border-left-color: var({variable_name}); }}\n"
        utility_classes += f".hover\\:border-l-{color_name}-{shade_num}:hover {{ border-left-color: var({variable_name}); }}\n"

css_variables += "}\n\n"

# Add border width utilities (similar to Tailwind's)
border_width_classes = ""
for suffix, width in border_widths.items():
    # All sides
    border_width_classes += f".border{suffix} {{ border-width: {width}; }}\n"
    
    # Individual sides
    border_width_classes += f".border-t{suffix} {{ border-top-width: {width}; }}\n"
    border_width_classes += f".border-r{suffix} {{ border-right-width: {width}; }}\n"
    border_width_classes += f".border-b{suffix} {{ border-bottom-width: {width}; }}\n"
    border_width_classes += f".border-l{suffix} {{ border-left-width: {width}; }}\n"

# Add border style utilities
border_style_classes = """
.border-solid { border-style: solid; }
.border-dashed { border-style: dashed; }
.border-dotted { border-style: dotted; }
.border-double { border-style: double; }
.border-none { border-style: none; }
"""

# Write to a CSS file
with open('iris/static/css/color-palette.css', 'w') as f:
    f.write(css_variables)
    f.write(utility_classes)
    f.write("\n/* Border Width Utilities */\n")
    f.write(border_width_classes)
    f.write("\n/* Border Style Utilities */\n")
    f.write(border_style_classes)

print("Generated color palette CSS file at static/css/color-palette.css")