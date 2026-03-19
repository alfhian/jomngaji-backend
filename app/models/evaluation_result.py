from pydantic import BaseModel
from typing import List, Optional, Dict

class Issue(BaseModel):
    category: str           # "tajwid" | "hijaiyah" | "tilawah" | "tahfidz"
    code: str               # e.g. "IKHFA", "IDGHAM", "MAKHRAJ_SIN"
    message: str            # penjelasan singkat
    location: Optional[str] # ayat:range atau huruf

class EvaluationResult(BaseModel):
    text: Optional[str]
    surah: Optional[str]
    ayah: Optional[int]
    scores: Dict[str, float]  # {"tajwid": 0.82, "tilawah": 0.75, ...}
    issues: List[Issue]
    suggestions: List[str]
