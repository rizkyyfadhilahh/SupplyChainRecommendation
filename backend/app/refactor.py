import re
import os

with open('app/data_loader.py', 'r', encoding='utf-8') as f:
    content = f.read()

vectorize_funcs = """
def vectorize_normalize_trace_product(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.upper().str.strip()
    conds = [
        s.str.contains("RBDPKO", na=False),
        s.str.contains("RBDPO", na=False),
        s.str.contains("PKO", na=False),
        s.str.contains("CPO", na=False),
        (s == "PK") | s.str.startswith("PK "),
        s.str.contains("RBDOLN", na=False) | s.str.contains("OLEIN", na=False),
        s.str.contains("RBDST", na=False),
        s.str.contains("RBDPS", na=False),
        s.str.contains("PFAD", na=False),
        s == "FFB"
    ]
    choices = ["RBDPKO", "RBDPO", "PKO", "CPO", "PK", "RBDOLN", "RBDST", "RBDPS", "PFAD", "FFB"]
    return pd.Series(np.select(conds, choices, default=s), index=s.index)

def vectorize_normalize_facility_type(series: pd.Series) -> pd.Series:
    return series.astype(str).str.upper().str.strip()

def vectorize_normalize_spec_value(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.upper().str.strip()
    return pd.Series(np.where(s.isin({"EUDR", "YES", "Y", "TRUE", "COMPLIANT", "EUDR COMPLIANT"}), "EUDR", s), index=s.index)
"""

content = content.replace('def load_application_data() -> Dict[str, Any]:\n    APP_DATA.clear()', vectorize_funcs + '\n\ndef load_application_data() -> Dict[str, Any]:\n    global APP_DATA\n    new_app_data = {}')

content = re.sub(r'\.apply\(\s*normalize_trace_product\s*\)', r'.pipe(vectorize_normalize_trace_product)', content)
content = re.sub(r'\.apply\(\s*normalize_facility_type\s*\)', r'.pipe(vectorize_normalize_facility_type)', content)
content = re.sub(r'\.apply\(\s*normalize_spec_value\s*\)', r'.pipe(vectorize_normalize_spec_value)', content)

content = re.sub(r'set_app_data\("([^"]+)",\s*([^)]+)\)', r'new_app_data["\1"] = \2', content)
content = content.replace('return APP_DATA', 'APP_DATA = new_app_data\n    return APP_DATA')

with open('app/data_loader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Refactor complete.")
