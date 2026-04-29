import slideflow as sf
from slideflow import studio
import os

DATA_DIR = "/data/slideflow"
os.makedirs(DATA_DIR, exist_ok=True)

print("Initializing Slideflow Studio on", DATA_DIR)

# Note: Studio() will automatically find datasets and models formatted inside the project directory
st = studio.Studio()
print("Booting up graphical interface...")
st.run()
