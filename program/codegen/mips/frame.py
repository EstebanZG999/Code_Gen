# program/codegen/mips/frame.py

from dataclasses import dataclass, field
from typing import Dict

# Convención de offsets relativos a $fp:
# fp+8  -> $ra
# fp+4  -> old $fp
# fp+12.. -> args (si se accede vía fp)
# fp-4, -8, ... -> locales y spill slots

@dataclass
class Frame:
    func_name: str
    num_locals: int = 0
    spill_slots: int = 0
    local_offsets: Dict[str, int] = field(default_factory=dict)

    def alloc_local(self, name: str) -> int:
        self.num_locals += 1
        off = -4 * self.num_locals
        self.local_offsets[name] = off
        return off

    def alloc_spill(self) -> int:
        self.spill_slots += 1
        return -4 * (self.num_locals + self.spill_slots)

    def frame_size(self) -> int:
        # 16 mínimo: espacio para guardar $fp/$ra y alineación simple
        base = 16
        extra = 4 * (self.num_locals + self.spill_slots)
        # redondeo sencillo a múltiplos de 8
        total = base + extra
        if total % 8 != 0:
            total += 8 - (total % 8)
        return total

    def offset_of_local(self, name: str) -> int:
        return self.local_offsets[name]
