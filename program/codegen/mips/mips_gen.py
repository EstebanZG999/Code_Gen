# program/codegen/mips/mips_gen.py

from dataclasses import dataclass, field
from typing import List, Optional
import re

from .asm_writer import AsmWriter
from .frame import Frame
from .reg_alloc import RegAllocator
from .instr_sel import InstructionSelector

# --- Pequeña estructura interna para representar funciones ya segmentadas ---
@dataclass
class FuncIR:
    name: str
    quads: List[object] = field(default_factory=list)

class MIPSGenerator:
    def __init__(self):
        self.writer = AsmWriter()

    # ---------------- Helpers de prólogo/epílogo ----------------
    def _emit_prolog(self, frame: Frame, writer=None):
        w = writer or self.writer
        fs = frame.frame_size()
        w.text()
        w.emit(f"addiu $sp,$sp,-{fs}")
        w.emit(f"sw $ra,{fs-8}($sp)")
        w.emit(f"sw $fp,{fs-4}($sp)")
        w.emit(f"addiu $fp,$sp,{fs-4}")

    def _emit_epilog(self, frame: Frame, writer=None):
        w = writer or self.writer
        fs = frame.frame_size()
        w.emit("move $sp,$fp")
        w.emit("lw $fp,4($sp)")
        w.emit("lw $ra,8($sp)")
        w.emit(f"addiu $sp,$sp,{fs}")
        w.emit("jr $ra")

    # -------------- Partir el TAC en funciones por labels --------------
    def _split_functions(self, tac_program) -> List[FuncIR]:
        code: List[object] = getattr(tac_program, "code", [])
        funcs: List[FuncIR] = []
        cur: Optional[FuncIR] = None

        for q in code:
            txt = str(q).strip()
            if txt.endswith(":"):
                lab = txt[:-1]
                if lab.startswith("func_") and lab.endswith("_entry"):
                    func_name = lab[len("func_"):-len("_entry")]
                    cur = FuncIR(func_name)
                    funcs.append(cur)
                    continue
                if lab.startswith("func_") and lab.endswith("_end"):
                    cur = None
                    continue

            if cur is not None:
                cur.quads.append(q)

        if not funcs and code:
            funcs.append(FuncIR("main", code))
        return funcs


    # ----------------- Generar una función -----------------
    def _normalize_quad(self, q):
        """
        Devuelve un dict uniforme con claves:
          - op (str)
          - a1, a2 (str | None)
          - dst (str | None)
          - label (str | None)
        Intenta primero por atributos; si no, parsea str(q).
        """
        # Intento por atributos comunes
        cand = {
            "op": getattr(q, "op", None),
            "a1": getattr(q, "arg1", None),
            "a2": getattr(q, "arg2", None),
            "dst": getattr(q, "res", None),
            "label": None,
        }
        # Algunas IR usan nombres distintos
        for k, alts in {
            "a1": ["x", "src1", "left"],
            "a2": ["y", "src2", "right"],
            "dst": ["result", "target", "dst"],
        }.items():
            if cand[k] is None:
                for alt in alts:
                    if hasattr(q, alt):
                        cand[k] = getattr(q, alt)
                        break

        # fuerza str() para evitar objetos no-string
        for k in ("op", "a1", "a2", "dst"):
            if cand[k] is not None and not isinstance(cand[k], str):
                cand[k] = str(cand[k])

        if isinstance(cand["op"], str) and cand["op"]:
            return cand

        # Si ya tenemos op y algo cuadra, retornamos
        if isinstance(cand["op"], str) and cand["op"]:
            return cand

        # Fallback: parsear str(q)
        txt = str(q).strip()

        # LABEL tipo:  func_xxx_entry:   ó   Lfor_body1:
        if txt.endswith(":"):
            lab = txt[:-1]
            return {"op": "label", "a1": None, "a2": None, "dst": None, "label": lab}

        # ASSIGN:  t0 := 5   ó  x := y
        if ":=" in txt:
            left, right = map(str.strip, txt.split(":=", 1))
            return {"op": "assign", "a1": right, "a2": None, "dst": left, "label": None}

        # LOAD:  load [fp+2] -> t0   ó  load t2 -> t3
        if txt.startswith("load "):
            body = txt[len("load "):]
            src, dst = map(str.strip, body.split("->"))
            return {"op": "load", "a1": src, "a2": None, "dst": dst, "label": None}

        # STORE:  store t1, [fp-1]
        if txt.startswith("store "):
            body = txt[len("store "):]
            src, addr = map(str.strip, body.split(",", 1))
            return {"op": "store", "a1": src, "a2": addr, "dst": None, "label": None}

        # GOTO:   goto L1
        if txt.startswith("goto "):
            lab = txt.split(None, 1)[1]
            return {"op": "goto", "a1": lab, "a2": None, "dst": None, "label": None}

        # IF GOTO:  if t2 goto Lfor_body1
        if txt.startswith("if "):
            rest = txt[len("if "):]
            cond, _, lab = rest.partition(" goto ")
            return {"op": "ifgoto", "a1": cond.strip(), "a2": lab.strip(), "dst": None, "label": None}

        # BINOP:  + x, y -> t0   /   < t0, 3 -> t2   /   * t0, t1 -> t2
        # Formato:  "<op> a1, a2 -> dst"
        for bop in ["+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!="]:
            if txt.startswith(bop + " "):
                body = txt[len(bop) + 1:]
                left, rest = map(str.strip, body.split(",", 1))
                right, _, dst = rest.partition("->")
                return {
                    "op": bop, "a1": left.strip(), "a2": right.strip(),
                    "dst": dst.strip(), "label": None
                }

        # CALL:  call "f", nargs=2 -> t0    ó    call "f", nargs=3
        if txt.startswith("call "):
            body = txt[len("call "):]
            # separar destino si existe
            if "->" in body:
                funpart, dst = map(str.strip, body.split("->", 1))
                dst = dst.strip()
            else:
                funpart, dst = body.strip(), None
            # nombre de función entre comillas
            if funpart.startswith('"'):
                fname = funpart.split('"')[1]
            else:
                fname = funpart.split(",")[0].strip()
            return {"op": "call", "a1": fname, "a2": None, "dst": dst, "label": None}

        # PARAM:  param t0  (o constantes)
        if txt.startswith("param "):
            val = txt[len("param "):].strip()
            return {"op": "param", "a1": val, "a2": None, "dst": None, "label": None}

        # RETURN: ret t2   /  ret null
        if txt.startswith("ret"):
            parts = txt.split(None, 1)
            val = parts[1].strip() if len(parts) > 1 else None
            return {"op": "ret", "a1": val, "a2": None, "dst": None, "label": None}

        # Otros (addr_field, addr_index, print, alloc, alloc_array, etc.)
        head = txt.split(None, 1)[0]
        return {"op": head, "a1": None, "a2": None, "dst": None, "label": None}

    def generate_function(self, func_ir: FuncIR) -> str:
        # usar writer local por función
        local_writer = AsmWriter()
        frame = Frame(func_ir.name)
        ra = RegAllocator(frame)
        sel = InstructionSelector(local_writer, ra, frame)

        local_writer.label(func_ir.name)
        self._emit_prolog(frame, writer=local_writer)

        for q in func_ir.quads:
            nq = self._normalize_quad(q)
            try:
                sel.select_for_quad(nq)
            except NotImplementedError as e:
                local_writer.emit(f"# TODO: instrucción no implementada: {nq['op']}  ({e})")
            except Exception as e:
                local_writer.emit(f"# WARN: fallo al traducir quad {q!r}: {e}")

        self._emit_epilog(frame, writer=local_writer)
        return local_writer.dump()

    # ----------------- Generar programa completo -----------------
    def generate_program(self, tac_program) -> str:
        funcs = self._split_functions(tac_program)
        outs = []
        for f in funcs:
            outs.append(self.generate_function(f))
        return "\n# ----------------\n".join(outs) + "\n"
