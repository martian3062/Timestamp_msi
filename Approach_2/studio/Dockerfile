FROM python:3.10-slim

# Install system dependencies, VNC, Xvfb, noVNC, window manager, and GUI libraries
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    libvips-dev \
    libgl1 \
    libglib2.0-0 \
    openslide-tools \
    git \
    wget \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    openbox \
    xterm \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install slideflow (and dearpygui for studio)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir slideflow openslide-python dearpygui

# Create a noVNC index.html symlink (sometimes novnc provides vnc.html but websockify expects index.html)
RUN ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html || true

COPY . /app

# Grant execute to entrypoint
RUN chmod +x /app/entrypoint.sh

EXPOSE 6080

CMD ["/app/entrypoint.sh"]
