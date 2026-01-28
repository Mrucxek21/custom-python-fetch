#!/usr/bin/env python3
import os
import platform
import subprocess
import psutil
import re
try:
    from PIL import Image
except Exception:
    Image = None

# Kolory i formatowanie
C = "\033[36m"
M = "\033[35m"
G = "\033[32m"
B = "\033[34m"
RED = "\033[31m"
SHADOW = "\033[90m"
R = "\033[0m"
BOLD = "\033[1m"
RESET = R

def rgb_to_ansi_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"

def rgb_to_ansi_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def strip_ansi(s: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', s)

def generate_big_text(text: str, size: int = 80):
    """Render large ASCII text using pyfiglet or figlet if available; fallback to PIL rendering at `size` pts."""
    try:
        import pyfiglet
        fig = pyfiglet.Figlet(font='standard')
        rendered = fig.renderText(text)
        lines = rendered.rstrip('\n').splitlines()
        return [f"{BOLD}{RED}{line}{RESET}" for line in lines]
    except Exception:
        pass
    try:
        out = subprocess.check_output(['figlet', text], text=True)
        lines = out.rstrip('\n').splitlines()
        return [f"{BOLD}{RED}{line}{RESET}" for line in lines]
    except Exception:
        # fallback: render text into an image with PIL and convert to ANSI blocks
        try:
            from PIL import ImageDraw, ImageFont
            # Try common truetype fonts
            font = None
            for fp in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                       '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
                try:
                    font = ImageFont.truetype(fp, int(size))
                    break
                except Exception:
                    font = None
            if font is None:
                font = ImageFont.load_default()

            # create image large enough
            up = text
            # estimate size
            dummy = Image.new('RGB', (10, 10), (0, 0, 0))
            draw = ImageDraw.Draw(dummy)
            w, h = draw.textsize(up, font=font)
            img = Image.new('RGB', (w + 10, h + 10), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            # draw text in red
            draw.text((5, 5), up, font=font, fill=(255, 0, 0))
            # convert to ASCII-art lines using existing converter
            lines = convert_image_to_ascii(img)
            # ensure ANSI-wrapped lines are returned
            return lines
        except Exception:
            # final fallback: simple uppercase single-line
            up = text.upper()
            return [f"{BOLD}{RED}{up}{RESET}"]

def get_packages():
    try:
        return subprocess.check_output("pacman -Qq | wc -l", shell=True).decode().strip()
    except Exception:
        return "N/A"

def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    except Exception:
        return "N/A"

def get_cpu():
    try:
        val = platform.processor().strip()
        if val:
            return val
    except Exception:
        pass
    # /proc/cpuinfo
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'model name' in line:
                    return line.split(':', 1)[1].strip()
    except Exception:
        pass
    # lscpu
    try:
        out = subprocess.check_output(['lscpu'], text=True)
        for line in out.splitlines():
            if line.startswith('Model name:'):
                return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return 'Unknown'

def get_gpu_info():
    try:
        # Get GPU name from lspci
        gpu_full = subprocess.check_output("lspci | grep -i 'vga\\|3d\\|2d'", shell=True).decode().strip()
        if not gpu_full:
            return 'N/A'
        gpu_name = gpu_full.split(': ', 1)[-1].strip() if ': ' in gpu_full else gpu_full
        gpu_name = gpu_name.split('(rev')[0].strip()
        

        try:
            vram = subprocess.check_output("nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null", shell=True).decode().strip()
            if vram and vram.isdigit():
                vram_gb = int(vram) // 1024
                return f"{gpu_name} ({vram_gb}GB)"
        except Exception:
            pass
        # For AMD GPUs try rocm-smi
        try:
            vram = subprocess.check_output("rocm-smi --showmeminfo 2>/dev/null | grep -i 'vram total'", shell=True).decode().strip()
            if vram:
                return f"{gpu_name} {vram}"
        except Exception:
            pass
        return gpu_name
    except Exception:
        return 'N/A'

def get_info():
    try:
        user = os.getlogin()
    except Exception:
        user = os.getenv('USER') or 'unknown'
    gpu = get_gpu_info()
    mem = psutil.virtual_memory()
    return {
        'User': user,
        'Host': platform.node(),
        'OS': platform.system() + ' ' + (platform.release()),
        'Kernel': platform.release(),
        'Shell': os.getenv('SHELL', '').split('/')[-1] or 'sh',
        'Gpu': gpu,
        'Packages': get_packages(),
        'Uptime': get_uptime(),
        'Memory': f"{mem.used // (1024**2)}MiB / {mem.total // (1024**2)}MiB",
        'CPU': get_cpu(),
    }

def convert_image_to_ascii(img):
    # Use upper-half block '▀' with fg/bg colors to get two pixels per character
    if img is None:
        return []
    pixels = img.load()
    width, height = img.size
    logo_lines = []
    # ensure even height
    if height < 2:
        # fallback: render single line
        line = ''
        for x in range(width):
            r, g, b = pixels[x, 0]
            line += f"{rgb_to_ansi_fg(r,g,b)}█"
        line += RESET
        return [line]
    for y in range(0, height - 1, 2):
        line = ''
        for x in range(width):
            r1, g1, b1 = pixels[x, y]
            r2, g2, b2 = pixels[x, y+1]
            line += f"{rgb_to_ansi_fg(r1,g1,b1)}{rgb_to_ansi_bg(r2,g2,b2)}▀"
        line += RESET
        logo_lines.append(line)
    return logo_lines

def get_custom_image_logo(path_to_image, width=36):
    """Load image. Resize to `width` while keeping aspect ratio.
    Height will be kept even to work with half-block rendering.
    If `width` is None, keep original resolution.
    """
    if Image is None:
        return None
    try:
        img = Image.open(path_to_image)
        if width is None:
            img = img.convert('RGB')
            return img
        w = int(width)
        h = int(img.size[1] * (w / img.size[0]))
        if h < 2:
            h = 2
        if h % 2 == 1:
            h += 1
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        img = img.convert('RGB')
        return img
    except Exception:
        return None

def display_fetch(image_path=None, width=36):
    info = get_info()
    # Replace image/logo with a large text banner (no shadow)
    logo = []
    logo.extend(generate_big_text('Windows', size=120))
    logo.append('')
    logo.extend(generate_big_text('sucks', size=120))

    info_lines = [
        f"{BOLD}{info['User']}@{info['Host']}{RESET}",
        "-----------------",
        f"{G}OS:{RESET} {info['OS']}",
        f"{G}Kernel:{RESET} {info['Kernel']}",
        f"{G}Uptime:{RESET} {info['Uptime']}",
        f"{G}Packages:{RESET} {info['Packages']}",
        f"{G}Shell:{RESET} {info['Shell']}",
        f"{G}Memory:{RESET} {info['Memory']}",
        f"{G}GPU:{RESET} {info['Gpu']}",
        f"{G}CPU:{RESET} {info['CPU']}",
    ]

    # Side-by-side: logo on the left, info on the right
    logo_visible_width = 0
    if logo:
        logo_visible_width = max((len(strip_ansi(s)) for s in logo), default=0)

    max_lines = max(len(logo), len(info_lines))
    for i in range(max_lines):
        left = logo[i] if i < len(logo) else ''
        right = info_lines[i] if i < len(info_lines) else ''
        if left:
            visible = len(strip_ansi(left))
            pad = ' ' * max(0, logo_visible_width - visible)
            print(f"{left}{pad}  {right}")
        else:
            print(f"{' ' * logo_visible_width}  {right}")

if __name__ == '__main__':
    image_path = '/home/admin/Dokumenty/logo-vector.svg'
    if os.path.exists(image_path):
        display_fetch(image_path, width=36)
    else:
        display_fetch(None)

