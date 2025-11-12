# program/codegen/mips/instr_sel.py

from typing import Dict

class InstructionSelector:
    def __init__(self, writer, reg_alloc, frame):
        self.w = writer
        self.ra = reg_alloc
        self.frame = frame

    def _is_const(self, x: str) -> bool:
        if x is None: return False
        x = x.strip()
        return x.isdigit() or (x.startswith('"') and x.endswith('"'))

    # parsea "[fp+2]" o "[fp-1]" → (base, offset_en_bytes)
    def _mem_addr(self, bracketed: str):
        inside = bracketed[1:-1].strip()  # quita [ ]
        if "+" in inside:
            base, off = inside.split("+", 1)
            sgn, val = +1, int(off.strip())
        elif "-" in inside:
            base, off = inside.split("-", 1)
            sgn, val = -1, int(off.strip())
        else:
            base, val, sgn = inside, 0, +1
        return base.strip(), sgn * val * 4

    def select_for_quad(self, q: Dict[str, str]):
        op, a1, a2, dst, lab = q["op"], q["a1"], q["a2"], q["dst"], q["label"]

        # LABEL
        if op == "label":
            self.w.label(lab)
            return

        # GOTO
        if op == "goto":
            self.w.emit(f"j {a1}")
            return

        # IF GOTO  (if t goto L)
        if op in ("ifgoto", "if_goto"):
            # MVP: si a1 es const, resuélvelo estáticamente
            if self._is_const(a1):
                cond_true = (a1 not in ("0", "false", "null"))
                if cond_true: self.w.emit(f"j {a2}")
                else: self.w.emit(f"# if false → no branch")
            else:
                self.w.emit(f"bne {a1}, $zero, {a2}")
            return

        # ASSIGN:  dst := a1
        if op == "assign":
            if self._is_const(a1):
                self.w.emit(f"li {dst}, {a1}")
            else:
                self.w.emit(f"move {dst}, {a1}")
            return

        # LOAD: load [fp+2] -> dst  |  load t2 -> dst
        if op == "load":
            if isinstance(a1, str) and a1.startswith("["):
                base, byte_off = self._mem_addr(a1)
                self.w.emit(f"lw {dst}, {byte_off}(${base})")
            else:
                self.w.emit(f"lw {dst}, 0({a1})")
            return

        # STORE: store a1, [fp-1]  |  store a1, t2
        if op == "store":
            if isinstance(a2, str) and a2.startswith("["):
                base, byte_off = self._mem_addr(a2)
                self.w.emit(f"sw {a1}, {byte_off}(${base})")
            else:
                self.w.emit(f"sw {a1}, 0({a2})")
            return

        # BINOPS: + - * / %
        if op in {"+", "-", "*", "/", "%"}:
            rd, rs, rt = dst, a1, a2
            if op == "+":   self.w.emit(f"addu {rd}, {rs}, {rt}")
            elif op == "-": self.w.emit(f"subu {rd}, {rs}, {rt}")
            elif op == "*": self.w.emit(f"mul {rd}, {rs}, {rt}")
            elif op == "/":
                self.w.emit(f"div {rs}, {rt}")
                self.w.emit(f"mflo {rd}")
            elif op == "%":
                self.w.emit(f"div {rs}, {rt}")
                self.w.emit(f"mfhi {rd}")
            return

        # RELACIONALES básicos (deja TODOs para el resto)
        if op in {"<", "<=", ">", ">=", "==", "!="}:
            if op == "<":
                self.w.emit(f"slt {dst}, {a1}, {a2}")
            elif op == "==":
                self.w.emit(f"subu {dst}, {a1}, {a2}")
                self.w.emit(f"sltiu {dst}, {dst}, 1")  # 1 si cero
            else:
                self.w.emit(f"# TODO relop {op} {a1} {a2} -> {dst}")
            return
        
        # BINOPS: + - * / %
        if op in {"+", "-", "*", "/", "%"}:
            if None in (a1, a2, dst):
                self.w.emit(f"# WARN binop incompleto: {a1} {op} {a2} -> {dst}")
                return
            rd, rs, rt = dst, a1, a2
            if op == "+":   self.w.emit(f"addu {rd}, {rs}, {rt}")
            elif op == "-": self.w.emit(f"subu {rd}, {rs}, {rt}")
            elif op == "*": self.w.emit(f"mul {rd}, {rs}, {rt}")
            elif op == "/":
                self.w.emit(f"div {rs}, {rt}")
                self.w.emit(f"mflo {rd}")
            elif op == "%":
                self.w.emit(f"div {rs}, {rt}")
                self.w.emit(f"mfhi {rd}")
            return

        # RETURN
        if op == "ret":
            if a1 and a1 not in ("null",):
                self.w.emit(f"move $v0, {a1}")
            return
        
        if op == "param":
            # Empuja el parámetro en el stack
            self.w.emit(f"addi $sp, $sp, -4")
            self.w.emit(f"sw {a1}, 0($sp)")
            return
        
        if op == "call":
            func_name = a1
            n_args = int(a2) if a2 and a2.isdigit() else 0

            self.w.emit(f"jal {func_name}")

            # Limpia los argumentos (n_args * 4 bytes)
            if n_args > 0:
                self.w.emit(f"addi $sp, $sp, {n_args * 4}")

            # Si hay destino, guarda el valor retornado ($v0)
            if dst:
                self.w.emit(f"move {dst}, $v0")
            return

        if op == "print":
            if self._is_const(a1):
                # Si es una cadena literal
                if a1.startswith('"'):
                    label = f"_str_{hash(a1) & 0xFFFF:X}"
                    self.w.emit(f'.data\n{label}: .asciiz {a1}\n.text')
                    self.w.emit(f"la $a0, {label}")
                    self.w.emit(f"li $v0, 4")
                else:
                    # Si es un número constante
                    self.w.emit(f"li $a0, {a1}")
                    self.w.emit(f"li $v0, 1")
            else:
                # Si es una variable (se asume entero)
                self.w.emit(f"move $a0, {a1}")
                self.w.emit(f"li $v0, 1")

            self.w.emit("syscall")
            return

        if op == "addr_field":
            # dst = base + offset * 4
            offset = int(a2) * 4
            self.w.emit(f"addi {dst}, {a1}, {offset}")
            return

        if op == "addr_index":
            # dst = base + (i << 2)
            self.w.emit(f"sll $t9, {a2}, 2")
            self.w.emit(f"addu {dst}, {a1}, $t9")
            return

        
        if op == "alloc":
            # a1 = bytes a reservar
            self.w.emit(f"move $a0, {a1}")
            self.w.emit("li $v0, 9")
            self.w.emit("syscall")
            self.w.emit(f"move {dst}, $v0")
            return

        if op == "alloc_array":
            # a1 = número de elementos
            self.w.emit(f"sll $a0, {a1}, 2")   # *4 bytes
            self.w.emit("li $v0, 9")
            self.w.emit("syscall")
            self.w.emit(f"move {dst}, $v0")
            return






        # Pendientes: param, call, print, addr_field, addr_index, alloc, alloc_array
        raise NotImplementedError(op)
