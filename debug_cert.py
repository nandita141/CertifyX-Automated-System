import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from backend.certificate_engine import CertificateGenerator

cg = CertificateGenerator()
print(f"Config loaded: {cg.cert_config.get('convert_to_words')}")
print(f"Value for no_of_weeks (6): {cg._get_value('no_of_weeks', {'no_of_weeks': 6})}")
print(f"Value for no_of_weeks (8): {cg._get_value('no_of_weeks', {'no_of_weeks': 8})}")
