# program/codegen/mips/instr_sel.py

from typing import Dict
import re

class InstructionSelector:
    def __init__(self, writer, reg_alloc, frame, string_vars=None):
        self.w = writer
        self.ra = reg_alloc
        self.frame = frame
        self.pc = 0
        # conjunto de nombres de variables que guardan direcciones de strings
        self.string_vars = set(string_vars or [])

    # -------- helpers --------
    def _is_const(self, x: str) -> bool:
        if x is None:
            return False
        x = x.strip()
        # acepta enteros negativos y literales "..."
        return x.lstrip("-").isdigit() or (x.startswith('"') and x.endswith('"'))

    def _mem_addr(self, bracketed: str):
        """
        Traduce direcciones TAC tipo [fp+2] o [fp-1] a offsets en bytes.
        Se añade +4 bytes para alinear con el layout real de frame.py:
            fp+4  -> old $fp
            fp+8  -> $ra
            fp+12 -> arg0
        Por tanto, [fp+2] debe mapear a 12($fp), no 8($fp).
        """
        inside = bracketed[1:-1].strip()
        if "+" in inside:
            base, off = inside.split("+", 1)
            sgn, val = +1, int(off.strip())
        elif "-" in inside:
            base, off = inside.split("-", 1)
            sgn, val = -1, int(off.strip())
        else:
            base, val, sgn = inside, 0, +1

        base = base.strip()
        byte_off = sgn * val * 4

        # ⚙️ Ajuste especial solo para base == "fp" y desplazamientos positivos:
        # agrega 4 bytes para compensar que arg0 = fp + 12, no fp + 8
        if base == "fp" and sgn > 0:
            byte_off += 4

        return base, byte_off


    def _save_victim(self, victim):
        # victim = (reg, off)
        if victim:
            reg, off = victim
            self.w.emit(f"sw {reg}, {off}($fp)")

    def _read_into_reg(self, name: str, scratch: str = "$t9", across: bool = False) -> str:
        """Devuelve un registro con el valor de 'name'. Maneja spill y víctimas."""
        reg, off, victim = self.ra.get_reg(name, across_call=across)
        self._save_victim(victim)
        if reg is None:
            # trabaja desde memoria a scratch
            self.w.emit(f"lw {scratch}, {off}($fp)")
            return scratch
        if off is not None:
            # estaba en memoria: cargarlo
            self.w.emit(f"lw {reg}, {off}($fp)")
            self.ra.mark_loaded(name)
        return reg

    def _dest_reg_or_spill(self, name: str, scratch: str = "$t8", across: bool = False):
        """Reg destino si cabe; si no, (None, off, scratch) para luego sw scratch->off."""
        reg, off, victim = self.ra.get_reg(name, across_call=across)
        self._save_victim(victim)
        if reg is not None:
            return reg, None, None
        return None, off, scratch

    # -------- selección --------
    def select_for_quad(self, q: Dict[str, str], pc: int):
        """
        Selección de instrucciones para un quad normalizado.
        pc = índice de la instrucción dentro de la función (0-based).
        """
        self.pc = pc

        op, a1, a2, dst, lab = q["op"], q["a1"], q["a2"], q["dst"], q["label"]

        # --- Saneamiento defensivo de labels (por si _normalize dejó cosas raras) ---
        if op == "goto":
            # si a1 viene vacío pero dst trae el label, usamos dst
            if (a1 is None or a1 == "None") and dst is not None:
                a1 = dst

        if op in ("ifgoto", "if_goto"):
            # if t goto L: el label puede venir en a2, o a veces en dst
            if (a2 is None or a2 == "None"):
                if dst is not None and dst != "None":
                    a2 = dst
                elif lab is not None and lab != "None":
                    a2 = lab

        # LABEL
        if op == "label":
            self.w.label(lab); return

        # GOTO
        if op == "goto":
            self.w.emit_raw(f"j {a1}"); return

        # IF GOTO  (if t goto L)
        if op in ("ifgoto", "if_goto"):
            if self._is_const(a1):
                cond_true = (a1 not in ("0", "false", "null"))
                if cond_true: self.w.emit(f"j {a2}")
            else:
                rcond = self._read_into_reg(a1)
                self.w.emit(f"bne {rcond}, $zero, {a2}")
                self.ra.free_if_dead(a1, pc)
            return
        
        # ASSIGN: dst := a1
        if op == "assign":
            if self._is_const(a1):
                # Literal de STRING: "..."
                if a1.startswith('"') and a1.endswith('"'):
                    label = f"_str_{hash(a1) & 0xFFFF:X}"

                    # Definimos el string en la sección .data
                    self.w.data()
                    self.w.label(label)
                    self.w.emit(f".asciiz {a1}")

                    # Volvemos a .text y cargamos la DIRECCIÓN en el destino
                    self.w.text()
                    rd, off, sc = self._dest_reg_or_spill(dst)
                    if rd:
                        self.w.emit(f"la {rd}, {label}")
                    else:
                        self.w.emit(f"la {sc}, {label}")
                        self.w.emit(f"sw {sc}, {off}($fp)")

                # Literal NUMÉRICO
                else:
                    rd, off, sc = self._dest_reg_or_spill(dst)
                    if rd:
                        self.w.emit(f"li {rd}, {a1}")
                    else:
                        self.w.emit(f"li {sc}, {a1}")
                        self.w.emit(f"sw {sc}, {off}($fp)")
            else:
                # dst := var/temporal
                rs = self._read_into_reg(a1)
                rd, off, sc = self._dest_reg_or_spill(dst)
                if rd:
                    self.w.emit(f"move {rd}, {rs}")
                else:
                    self.w.emit(f"sw {rs}, {off}($fp)")

            return

        # LOAD
        if op == "load":
            # Caso 1: dirección explícita [fp+N] (Addr(fp, k) -> "[fp+k]")
            if isinstance(a1, str) and a1.startswith("["):
                base, byte_off = self._mem_addr(a1)
                rd, off, sc = self._dest_reg_or_spill(dst)
                out = rd if rd is not None else sc
                # cargar desde [base+off] al registro 'out'
                self.w.emit(f"lw {out}, {byte_off}(${base})")
                # si no había registro para dst, guardamos el scratch en el spill
                if off is not None:
                    self.w.emit(f"sw {out}, {off}($fp)")
            else:
                # Caso 2: load ptr -> dst
                # a1 es una variable/temporal que CONTIENE una DIRECCIÓN
                rptr = self._read_into_reg(a1)      # rptr = puntero
                rd, off, sc = self._dest_reg_or_spill(dst)
                out = rd if rd is not None else sc  # registro donde queremos el valor
                # *rptr
                self.w.emit(f"lw {out}, 0({rptr})")
                if off is not None:
                    self.w.emit(f"sw {out}, {off}($fp)")
            self.ra.free_if_dead(a1, pc)
            return

        # STORE
        if op == "store":
            # store src, [fp+N]  → acceso directo al frame
            if isinstance(a2, str) and a2.startswith("["):
                base, byte_off = self._mem_addr(a2)
                rs = self._read_into_reg(a1)
                self.w.emit(f"sw {rs}, {byte_off}(${base})")
                self.ra.free_if_dead(a1, pc)
                self.ra.free_if_dead(a2, pc)
                return
            else:
                # store src, ptr  → *ptr = src
                rs   = self._read_into_reg(a1)   # valor a escribir
                rptr = self._read_into_reg(a2)   # puntero donde escribir
                self.w.emit(f"sw {rs}, 0({rptr})")
                self.ra.free_if_dead(a1, pc)
                self.ra.free_if_dead(a2, pc)
                return

        # BINOPS: + - * / %
        if op in {"+", "-", "*", "/", "%"}:
            rs = self._read_into_reg(a1, "$t7")
            rt = self._read_into_reg(a2, "$t6")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t5")
            out = rd if rd is not None else sc
            if op == "+":   self.w.emit(f"addu {out}, {rs}, {rt}")
            elif op == "-": self.w.emit(f"subu {out}, {rs}, {rt}")
            elif op == "*": self.w.emit(f"mul {out}, {rs}, {rt}")
            elif op == "/":
                self.w.emit(f"div {rs}, {rt}"); self.w.emit(f"mflo {out}")
            elif op == "%":
                self.w.emit(f"div {rs}, {rt}"); self.w.emit(f"mfhi {out}")
            if off is not None:
                self.w.emit(f"sw {out}, {off}($fp)")
            self.ra.free_if_dead(a1, pc); self.ra.free_if_dead(a2, pc)
            return

        # RELACIONALES básicos
        if op in {"<", "<=", ">", ">=", "==", "!="}:
            rs = self._read_into_reg(a1, "$t7")
            rt = self._read_into_reg(a2, "$t6")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t5")
            out = rd if rd is not None else sc
            if op == "<":
                self.w.emit(f"slt {out}, {rs}, {rt}")
            elif op == "<=":
                # rs <= rt  <=>  !(rs > rt)
                self.w.emit(f"slt {out}, {rt}, {rs}")  # rt < rs
                self.w.emit(f"xori {out}, {out}, 1")   # not
            elif op == ">":
                self.w.emit(f"slt {out}, {rt}, {rs}")  # rt < rs
            elif op == ">=":
                # rs >= rt  <=>  !(rs < rt)
                self.w.emit(f"slt {out}, {rs}, {rt}")
                self.w.emit(f"xori {out}, {out}, 1")
            elif op == "==":
                self.w.emit(f"subu {out}, {rs}, {rt}")
                self.w.emit(f"sltiu {out}, {out}, 1")
            elif op == "!=":
                self.w.emit(f"subu {out}, {rs}, {rt}")
                self.w.emit(f"sltu {out}, $zero, {out}")
            if off is not None:
                self.w.emit(f"sw {out}, {off}($fp)")
            self.ra.free_if_dead(a1, pc); self.ra.free_if_dead(a2, pc)
            return

        # RETURN
        if op == "ret":
            if a1 and a1 not in ("null",):
                rs = self._read_into_reg(a1)
                self.w.emit(f"move $v0, {rs}")
                self.ra.free_if_dead(a1, pc)
            return

        # PARAM/CALL
        if op == "param":
            rs = self._read_into_reg(a1, "$t7")
            self.w.emit("addi $sp, $sp, -4")
            self.w.emit(f"sw {rs}, 0($sp)")
            self.ra.free_if_dead(a1, pc)
            return

        if op == "call":
            # caller-saved: pedir a RA qué $t* guardar
            saves = self.ra.on_call()
            for reg, off in saves:
                self.w.emit(f"sw {reg}, {off}($fp)")

            # nombre de función limpio (por si trae comillas)
            fname = a1.strip('"') if a1 else a1

            # llamar
            self.w.emit(f"jal {fname}")

            # limpiar args apilados
            n = int(a2) if a2 and a2.isdigit() else 0
            if n > 0:
                self.w.emit(f"addi $sp, $sp, {n*4}")

            # recoger retorno
            if dst:
                rd, off, sc = self._dest_reg_or_spill(dst)
                if rd: self.w.emit(f"move {rd}, $v0")
                else:  self.w.emit(f"sw $v0, {off}($fp)")
            return

        # DIRECCIONES / MEMORIA DINÁMICA
        if op == "addr_field":
            # dst = base + offset * 4
            offset = int(a2) * 4
            rb = self._read_into_reg(a1, "$t7")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t6")
            out = rd if rd is not None else sc
            self.w.emit(f"addi {out}, {rb}, {offset}")
            if off is not None: self.w.emit(f"sw {out}, {off}($fp)")
            self.ra.free_if_dead(a1, pc)
            return

        if op == "addr_index":
            # dst = base + (i << 2)
            rb = self._read_into_reg(a1, "$t7")  
            ri = self._read_into_reg(a2, "$t6")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t5")
            out = rd if rd is not None else sc

            # out = i << 2
            self.w.emit(f"sll {out}, {ri}, 2")
            # out = base + (i << 2)
            self.w.emit(f"addu {out}, {rb}, {out}")

            if off is not None:
                self.w.emit(f"sw {out}, {off}($fp)")

            self.ra.free_if_dead(a1, pc)
            self.ra.free_if_dead(a2, pc)
            return

        if op == "alloc":
            # a1 = bytes
            rn = self._read_into_reg(a1, "$t7")
            self.w.emit(f"move $a0, {rn}")
            self.w.emit("li $v0, 9"); self.w.emit("syscall")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t6")
            if rd: self.w.emit(f"move {rd}, $v0")
            else:  self.w.emit(f"sw $v0, {off}($fp)")
            self.ra.free_if_dead(a1, pc)
            return

        if op == "alloc_array":
            # a1 = n (int)
            rn = self._read_into_reg(a1, "$t7")
            self.w.emit(f"sll $a0, {rn}, 2")
            self.w.emit("li $v0, 9"); self.w.emit("syscall")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t6")
            if rd: self.w.emit(f"move {rd}, $v0")
            else:  self.w.emit(f"sw $v0, {off}($fp)")
            self.ra.free_if_dead(a1, pc)
            return
        
        # PRINT
        if op == "print":
            if self._is_const(a1):
                # Literal de cadena
                if a1.startswith('"') and a1.endswith('"'):
                    label = f"_str_{hash(a1) & 0xFFFF:X}"
                    # Definimos el string en .data
                    self.w.data()
                    self.w.label(label)
                    self.w.emit(f".asciiz {a1}")
                    # Volvemos a .text y lo imprimimos como string
                    self.w.text()
                    self.w.emit(f"la $a0, {label}")
                    self.w.emit("li $v0, 4")   # print string
                else:
                    # Número constante
                    self.w.emit(f"li $a0, {a1}")
                    self.w.emit("li $v0, 1")   # print int
            else:
                # Variable: puede ser int o puntero a string
                rs = self._read_into_reg(a1)
                self.w.emit(f"move $a0, {rs}")
                if a1 in self.string_vars:
                    # Fue asignada desde un literal "...", asumimos string
                    self.w.emit("li $v0, 4")   # print string
                else:
                    self.w.emit("li $v0, 1")   # print int

            self.w.emit("syscall")
            self.ra.free_if_dead(a1, pc)
            return
        
        raise NotImplementedError(op)