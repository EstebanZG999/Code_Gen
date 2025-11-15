# program/codegen/mips/instr_sel.py

from typing import Dict
import re

class InstructionSelector:
    def __init__(self, writer, reg_alloc, frame, string_vars=None, known_funcs=None):
        self.w = writer
        self.ra = reg_alloc
        self.frame = frame
        self.pc = 0
        # conjunto de nombres de variables que guardan direcciones de strings
        self.string_vars = set(string_vars or [])
        self.known_funcs = set(known_funcs or [])
        self.concat_prefix: Dict[str, str] = {}
        self.pending_params = []


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
        # Protección extra: nunca tratar una constante como variable
        if self._is_const(name):
            # Esto NO debería pasar; si pasa, mejor que truene en compile-time que en runtime
            raise RuntimeError(f"_read_into_reg llamado con constante: {name}")

        reg, off, victim = self.ra.get_reg(name, across_call=across)
        self._save_victim(victim)
        if reg is None:
            self.w.emit(f"lw {scratch}, {off}($fp)")
            return scratch
        if off is not None:
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
                
                # DEBUG: chequear alineación SIN tocar rptr
                #self.w.emit(f"andi $at, {rptr}, 3")
                #self.w.emit(f"bne $at, $zero, __misaligned_store")
                #self.w.emit("nop")

                self.w.emit(f"sw {rs}, 0({rptr})")
                self.ra.free_if_dead(a1, pc)
                self.ra.free_if_dead(a2, pc)
                return

        # BINOPS: + - * / %
        if op in {"+", "-", "*", "/", "%"}:

            # --- CASO ESPECIAL: concatenación "string" + int usada para prints ---
            if op == "+":
                is_str1 = (
                    a1 is not None
                    and isinstance(a1, str)
                    and a1.startswith('"') and a1.endswith('"')
                )
                is_str2 = (
                    a2 is not None
                    and isinstance(a2, str)
                    and a2.startswith('"') and a2.endswith('"')
                )

                # Patrón: uno es string literal y el otro NO es constante (ej. "r1=" + r1)
                if (is_str1 and not self._is_const(a2)) or (is_str2 and not self._is_const(a1)):
                    # Determinar cuál es el prefijo string y cuál es el valor numérico
                    if is_str1:
                        prefix = a1
                        value_name = a2
                    else:
                        prefix = a2
                        value_name = a1

                    # Guardar que 'dst' tiene un prefijo de concatenación
                    if dst is not None:
                        self.concat_prefix[dst] = prefix

                    # Semántica "pragmática": dst solo almacena el valor numérico,
                    # y el prefijo se imprimirá en 'print dst'
                    rs = self._read_into_reg(value_name, "$t7")
                    rd, off, sc = self._dest_reg_or_spill(dst, "$t5")
                    out = rd if rd is not None else sc
                    self.w.emit(f"move {out}, {rs}")
                    if off is not None:
                        self.w.emit(f"sw {out}, {off}($fp)")

                    self.ra.free_if_dead(value_name, pc)
                    return

            # --- CASO NORMAL: aritmética entera pura ---
            rs = self._read_into_reg(a1, "$t7")
            rt = self._read_into_reg(a2, "$t6")
            rd, off, sc = self._dest_reg_or_spill(dst, "$t5")
            out = rd if rd is not None else sc
            if op == "+":   self.w.emit(f"addu {out}, {rs}, {rt}")
            elif op == "-": self.w.emit(f"subu {out}, {rs}, {rt}")
            elif op == "*": self.w.emit(f"mul {out}, {rs}, {rt}")
            elif op == "/":
                self.w.emit(f"div {rs}, {rt}")
                self.w.emit(f"mflo {out}")
            elif op == "%":
                self.w.emit(f"div {rs}, {rt}")
                self.w.emit(f"mfhi {out}")
            if off is not None:
                self.w.emit(f"sw {out}, {off}($fp)")
            self.ra.free_if_dead(a1, pc)
            self.ra.free_if_dead(a2, pc)
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
            # Solo acumulamos el nombre del parámetro.
            # Los pushes reales a la pila se hacen en 'call'.
            if a1 is not None:
                self.pending_params.append(a1)
            return

        if op == "call":
            # 0) Número de parámetros acumulados
            param_count = len(self.pending_params)

            # 1) Empujar parámetros en orden inverso
            #    IR: param p1, param p2, call f
            #    En stack (de arriba hacia abajo): p1, p2
            for pname in reversed(self.pending_params):
                # En tu IR los params deberían ser temporales/vars, no literales.
                # Así que podemos leerlos normal:
                rs = self._read_into_reg(pname, "$t7")
                self.w.emit("addi $sp, $sp, -4")
                self.w.emit(f"sw {rs}, 0($sp)")
                # Liberar aquí según liveness
                self.ra.free_if_dead(pname, pc)

            # Limpiamos la lista de params para la siguiente llamada
            self.pending_params.clear()

            # 2) caller-saved: pedir a RA qué $t* guardar
            saves = self.ra.on_call()
            for reg, off in saves:
                self.w.emit(f"sw {reg}, {off}($fp)")

            # 3) nombre base (por si viene con comillas)
            fname = a1.strip('"') if a1 else a1

            # Resolución contra la lista de funciones conocidas
            if self.known_funcs and fname not in self.known_funcs and "." in fname:
                parts = fname.split(".")
                for i in range(1, len(parts)):
                    candidate = ".".join(parts[i:])
                    if candidate in self.known_funcs:
                        fname = candidate
                        break

            # 4) llamar
            self.w.emit(f"jal {fname}")

            # 5) limpiar args apilados
            n = int(a2) if a2 and a2.isdigit() else param_count
            if n > 0:
                self.w.emit(f"addi $sp, $sp, {n*4}")

            # 6) recoger retorno
            if dst:
                rd, off, sc = self._dest_reg_or_spill(dst)
                if rd:
                    self.w.emit(f"move {rd}, $v0")
                else:
                    self.w.emit(f"sw $v0, {off}($fp)")
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
            # a1 puede ser:
            #  - "16"          (tamaño en bytes)
            #  - "\"Box\""     (nombre de tipo en la IR)
            #  - nombre de temporal/var
            size_expr = a1

            if size_expr is None:
                # fallback seguro: 4 bytes
                self.w.emit("li $a0, 4")

            # Caso 1: literal numérico (ej. "16")
            elif size_expr.lstrip("-").isdigit():
                self.w.emit(f"li $a0, {size_expr}")

            # Caso 2: literal de cadena (ej. "Box") -> tipo/clase
            elif size_expr.startswith('"') and size_expr.endswith('"'):
                type_name = size_expr.strip('"')
                # Para este proyecto: Box tiene 1 campo int -> 4 bytes
                # Si luego tienes más clases, aquí haces un map nombre->tamaño
                size_bytes = 4
                self.w.emit(f"li $a0, {size_bytes}")

            # Caso 3: viene de una variable/temporal
            else:
                rn = self._read_into_reg(size_expr, "$t7")
                self.w.emit(f"move $a0, {rn}")

            self.w.emit("li $v0, 9")
            self.w.emit("syscall")

            rd, off, sc = self._dest_reg_or_spill(dst, "$t6")
            if rd:
                self.w.emit(f"move {rd}, $v0")
            else:
                self.w.emit(f"sw $v0, {off}($fp)")

            return

        if op == "alloc_array":
            # a1 = n (longitud del arreglo)
            if self._is_const(a1) and not (a1.startswith('"') and a1.endswith('"')):
                # Longitud constante: li a un scratch y luego *4
                self.w.emit(f"li $t7, {a1}")
                self.w.emit("sll $a0, $t7, 2")   # bytes = n * 4
            else:
                # Longitud en una variable/temporal
                rn = self._read_into_reg(a1, "$t7")
                self.w.emit(f"sll $a0, {rn}, 2")

            self.w.emit("li $v0, 9")
            self.w.emit("syscall")

            rd, off, sc = self._dest_reg_or_spill(dst, "$t6")
            if rd:
                self.w.emit(f"move {rd}, $v0")
            else:
                self.w.emit(f"sw $v0, {off}($fp)")

            return
        
        # PRINT
        if op == "print":
            # --- CASO ESPECIAL: print de resultado de "string" + int ---
            if a1 in self.concat_prefix:
                prefix = self.concat_prefix[a1]

                # 1) imprimir el prefijo (string literal)
                label = f"_str_{hash(prefix) & 0xFFFF:X}"
                self.w.data()
                self.w.label(label)
                self.w.emit(f".asciiz {prefix}")
                self.w.text()
                self.w.emit(f"la $a0, {label}")
                self.w.emit("li $v0, 4")
                self.w.emit("syscall")

                # 2) imprimir el valor numérico guardado en 'a1'
                rs = self._read_into_reg(a1)
                self.w.emit(f"move $a0, {rs}")
                self.w.emit("li $v0, 1")
                self.w.emit("syscall")

                self.ra.free_if_dead(a1, pc)
                return

            # --- CASO NORMAL ---
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
                    self.w.emit("li $v0, 4")   # print string
                else:
                    self.w.emit("li $v0, 1")   # print int

            self.w.emit("syscall")
            self.ra.free_if_dead(a1, pc)
            return
        
        raise NotImplementedError(op)