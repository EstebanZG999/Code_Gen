# program/codegen/mips/asm_writer.py

from typing import List

class AsmWriter:
    def __init__(self):
        self.lines: List[str] = []
        self.in_text = False
        self.in_data = False

    def text(self):
        # Forzamos SIEMPRE a emitir .text
        self.lines.append(".text")
        self.in_text = True
        self.in_data = False

    def data(self):
        # Forzamos SIEMPRE a emitir .data
        self.lines.append(".data")
        self.in_data = True
        self.in_text = False

    def label(self, name: str):
        self.lines.append(f"{name}:")   # sin indent

    def emit(self, instr: str):
        self.lines.append(f"  {instr}") # con indent

    def emit_raw(self, line: str):
        self.lines.append(line)

    def dump(self) -> str:
        return "\n".join(self.lines) + "\n"
