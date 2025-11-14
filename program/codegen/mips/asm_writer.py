# program/codegen/mips/asm_writer.py

from typing import List, Optional

class AsmWriter:
    def __init__(self):
        self.lines: List[str] = []
        self.in_text = False
        self.in_data = False

    def text(self):
        if not self.in_text:
            self.lines.append(".text")
            self.in_text = True

    def data(self):
        if not self.in_data:
            self.lines.append(".data")
            self.in_data = True

    def label(self, name: str):
        self.lines.append(f"{name}:")   # sin indent, correcto

    def emit(self, instr: str):
        self.lines.append(f"  {instr}") # con indent

    # para líneas sin indent (lo usaremos en 'goto' por el test)
    def emit_raw(self, line: str):
        self.lines.append(line)

    def dump(self) -> str:
        return "\n".join(self.lines) + "\n"
