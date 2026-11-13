from pathlib import Path
import shutil
shutil.rmtree(Path(__file__).parent / "home-isolated", ignore_errors=True)
