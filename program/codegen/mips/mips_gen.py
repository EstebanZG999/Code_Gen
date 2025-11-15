# program/codegen/mips/mips_gen.py
#
# Generador MIPS “de alto nivel”:
# - Parte el TAC (lista de quads) por funciones, usando labels func_*_entry / func_*_end.
# - Normaliza cada quad a un dict uniforme {op, a1, a2, dst, label}.
# - Emite prólogo/epílogo de acuerdo al contrato de frame ($fp).
# - Invoca al InstructionSelector quad a quad, y usa un RegAllocator compartido
#   que se re-ancla por función (attach_frame).
#
# Contrato de frame que seguimos:
#   fp+4  = old $fp
#   fp+8  = $ra
#   fp+12 = arg0, fp+16 = arg1, ...
#   fp-4, fp-8, ... = locales y spill slots
#
# Prólogo (con fs = frame.frame_size()):
#   addiu $sp,$sp,-fs
#   sw   $ra, fs-4($sp)     ; esto pasa a ser (fp+8)
#   sw   $fp, fs-8($sp)     ; esto pasa a ser (fp+4)
#   addiu $fp,$sp, fs-12    ; por lo tanto: 4($fp)=old fp, 8($fp)=$ra
#
# Epílogo:
#   move $sp,$fp
#   lw   $fp,4($sp)
#   lw   $ra,8($sp)
#   addiu $sp,$sp,12
#   jr   $ra

from dataclasses import dataclass, field
from typing import List, Optional, Iterable, Any, Dict, Set

from .asm_writer import AsmWriter
from .frame import Frame
from .reg_alloc import RegAllocator
from .instr_sel import InstructionSelector


# Estructura interna: una función ya segmentada con su lista de quads normalizados
@dataclass
class FuncIR:
    name: str
    quads: List[Any] = field(default_factory=list)


class MIPSGenerator:
    def __init__(self):
        # Un único writer para todo el archivo ASM de salida
        self.writer = AsmWriter()
        # Un único RegAllocator (estado global), re-anclado por función con attach_frame(frame)
        self.ra = RegAllocator()

    # ---------- Emisión de prólogo/epílogo con el contrato descrito ----------
    def _emit_prolog(self, frame: Frame) -> None:
        """
        Emite el prólogo usando frame_size() del Frame.

        Objetivo: que tras el prólogo se cumpla el layout relativo a $fp:

            fp + 12 : arg0
            fp + 16 : arg1
            fp + 20 : arg2
            ...
            fp + 8  : saved $ra
            fp + 4  : old $fp
            fp - 4  : local / spill 0
            fp - 8  : local / spill 1
            ...

        Elegimos un $fp tal que old $fp y $ra queden accesibles justo en
        4($fp) y 8($fp), independientemente de frame_size().
        """
        w = self.writer
        fs = frame.frame_size()

        if fs < 64:
            fs = 64

        w.text()
        w.emit(f"# --- prologo de {frame.func_name} ---")

        # Reservar todo el frame: locales + spills + espacio para guardar fp/ra
        w.emit(f"addiu $sp,$sp,-{fs}")

        # Guardar $ra y old $fp en la parte alta del bloque reservado.
        # Con este patrón, después de fijar $fp, quedarán como:
        #   old $fp -> 4($fp)
        #   $ra     -> 8($fp)
        w.emit(f"sw $ra,{fs-4}($sp)")   # esto termina siendo 8($fp)
        w.emit(f"sw $fp,{fs-8}($sp)")   # esto termina siendo 4($fp)

        # Fijamos $fp de modo que 4($fp) y 8($fp) apunten a old $fp / $ra,
        # y los argumentos queden a partir de 12($fp).
        w.emit(f"addiu $fp,$sp,{fs-12}")

        w.emit(f"# --- fin prologo de {frame.func_name} ---")

    def _emit_epilog(self, frame: Frame) -> None:
        """
        Epílogo inverso del prólogo.

        Aquí asumimos el mismo layout:

            fp + 4 : old $fp
            fp + 8 : saved $ra

        y devolvemos $sp al valor que tenía la función al entrar
        """
        # El caller se encarga de limpiar sus argumentos
        w = self.writer
        w.emit(f"# --- epilogo de {frame.func_name} ---")

        # Volvemos a usar $fp como base para leer old $fp y $ra
        w.emit("move $sp,$fp")
        w.emit("lw $fp,4($sp)")   # old $fp
        w.emit("lw $ra,8($sp)")   # saved $ra

        # Saltamos por encima del bloque [old $fp, $ra, args-header]
        # para dejar $sp exactamente como al entrar a la función
        w.emit("addiu $sp,$sp,12")

        w.emit("jr $ra")
        w.emit("nop  # delay slot")
        w.emit(f"# --- fin epilogo de {frame.func_name} ---")

    # ---------- Normalizador de quads ----------
    def _normalize_quad(self, q: Any) -> dict:
        """
        Retorna un dict con claves:
          - op (str)
          - a1, a2 (str | None)
          - dst (str | None)
          - label (str | None)
        Prioriza leer atributos (q.op, q.arg1, etc.). Si falla, hace fallback a parsear str(q).
        """
        # Intento por atributos comunes
        cand = {
            "op": getattr(q, "op", None),
            "a1": getattr(q, "arg1", None),
            "a2": getattr(q, "arg2", None),
            "dst": getattr(q, "res", None),
            "label": getattr(q, "label", None),
        }
        # Alias frecuentes en otras IR
        for k, alts in {
            "a1": ["x", "src1", "left", "a"],
            "a2": ["y", "src2", "right", "b"],
            "dst": ["result", "target", "dst"],
            "label": ["name"],
        }.items():
            if cand.get(k) is None:
                for alt in alts:
                    if hasattr(q, alt):
                        cand[k] = getattr(q, alt)
                        break

        # Forzar a str (evita objetos no-string colándose)
        for k in ("op", "a1", "a2", "dst", "label"):
            if cand[k] is not None and not isinstance(cand[k], str):
                cand[k] = str(cand[k])

        # Normaliza ":=" a "assign"
        if cand["op"] == ":=":
            cand["op"] = "assign"

        # Si dice ser 'label' pero no trae nombre, intenta derivarlo del texto
        if cand["op"] == "label" and not cand["label"]:
            txt_label = str(q).strip()
            if txt_label.endswith(":"):
                cand["label"] = txt_label[:-1]

        # Si ya tenemos 'op' y al menos un operando/label, úsalo
        have_op = isinstance(cand["op"], str) and cand["op"]
        have_any = any(cand[k] is not None for k in ("a1", "a2", "dst", "label"))
        if have_op and have_any:
            return cand

        # Fallback: parseo por string del quad
        txt = str(q).strip()

        # Label simple: "Lx:" o "func_foo_entry:"
        if txt.endswith(":"):
            return {"op": "label", "a1": None, "a2": None, "dst": None, "label": txt[:-1]}

        # Asignación: "x := y"
        if ":=" in txt:
            left, right = map(str.strip, txt.split(":=", 1))
            return {"op": "assign", "a1": right, "a2": None, "dst": left, "label": None}

        # Cargas: "load [fp+2] -> t0" o "load t2 -> t3"
        if txt.startswith("load "):
            body = txt[len("load "):]
            src, dst = map(str.strip, body.split("->"))
            return {"op": "load", "a1": src, "a2": None, "dst": dst, "label": None}

        # Stores: "store t1, [fp-1]"
        if txt.startswith("store "):
            body = txt[len("store "):]
            src, addr = map(str.strip, body.split(",", 1))
            return {"op": "store", "a1": src, "a2": addr, "dst": None, "label": None}

        # Saltos: "goto L1"
        if txt.startswith("goto "):
            lab = txt.split(None, 1)[1]
            return {"op": "goto", "a1": lab, "a2": None, "dst": None, "label": None}

        # Condicionales: "if t2 goto Lfor_body1"
        if txt.startswith("if "):
            rest = txt[len("if "):]
            cond, _, lab = rest.partition(" goto ")
            return {"op": "ifgoto", "a1": cond.strip(), "a2": lab.strip(), "dst": None, "label": None}

        # Binarias: "<= x, y -> t", "+ x, y -> t", etc.
        for bop in ["<=", ">=", "==", "!=", "+", "-", "*", "/", "%", "<", ">"]:
            if txt.startswith(bop + " "):
                body = txt[len(bop) + 1:]
                left, rest = map(str.strip, body.split(",", 1))
                right, _, dst = rest.partition("->")
                return {
                    "op": bop, "a1": left.strip(), "a2": right.strip(),
                    "dst": dst.strip(), "label": None
                }

        # Llamadas: 'call f, nargs=2 -> t0' o 'call "f", nargs=3'
        if txt.startswith("call "):
            body = txt[len("call "):].strip()
            if "->" in body:
                left, dst = map(str.strip, body.split("->", 1)); dst = dst.strip()
            else:
                left, dst = body, None
            parts = [p.strip() for p in left.split(",")]
            fname = parts[0].strip('"'); nargs = None
            for p in parts[1:]:
                if p.startswith("nargs"):
                    _, _, n = p.partition("="); nargs = n.strip(); break
            return {"op": "call", "a1": fname, "a2": nargs, "dst": dst, "label": None}

        # Parámetros: "param t0"
        if txt.startswith("param "):
            val = txt[len("param "):].strip()
            return {"op": "param", "a1": val, "a2": None, "dst": None, "label": None}

        # Retorno: "ret x" o "ret"
        if txt.startswith("ret"):
            parts = txt.split(None, 1)
            val = parts[1].strip() if len(parts) > 1 else None
            return {"op": "ret", "a1": val, "a2": None, "dst": None, "label": None}
        
        # PRINT: "print <arg>"
        if txt.startswith("print "):
            arg = txt[len("print "):].strip()
            return {"op": "print", "a1": arg, "a2": None, "dst": None, "label": None}

        # Cualquier otra cabecera (addr_field, print, alloc, etc.)
        head = txt.split(None, 1)[0]
        return {"op": head, "a1": None, "a2": None, "dst": None, "label": None}

    # ---------- Partir el TAC en funciones ----------
    def _split_functions(self, tac_program) -> List[FuncIR]:
        """
        Recorre tac_program.code (lista de quads/labels).
        Crea FuncIRs cuando detecta 'func_<name>_entry:' y cierra al ver 'func_<name>_end:'.
        Si no hay marcas de función, asume todo como 'main'.
        """
        code: List[Any] = getattr(tac_program, "code", [])
        funcs: List[FuncIR] = []
        cur: Optional[FuncIR] = None

        for q in code:
            txt = str(q).strip()
            if txt.endswith(":"):
                lab = txt[:-1]
                # Abrir función
                if lab.startswith("func_") and lab.endswith("_entry"):
                    func_name = lab[len("func_"):-len("_entry")]
                    cur = FuncIR(func_name)
                    funcs.append(cur)
                    continue
                # Cerrar función
                if lab.startswith("func_") and lab.endswith("_end"):
                    cur = None
                    continue

            # Acumular quads de la función abierta
            if cur is not None:
                cur.quads.append(self._normalize_quad(q))

        # Caso sin etiquetas de función: todo es 'main'
        if not funcs and code:
            funcs.append(FuncIR("main", [self._normalize_quad(q) for q in code]))

        return funcs

    # ---------- Análisis de liveness ----------

    def _is_var_like(self, name: Optional[str]) -> bool:
        """
        Heurística para decidir si un string 'name' se comporta como variable de la IR.
        Evitamos:
          - None
          - números (enteros)
          - literales entre comillas
          - direcciones tipo "[fp+2]"
          - constantes especiales simples
        """
        if name is None:
            return False
        s = name.strip()
        if not s:
            return False
        # números (con signo opcional)
        if s.lstrip("-").isdigit():
            return False
        # literales de cadena
        if s.startswith('"') and s.endswith('"'):
            return False
        # direcciones tipo [fp+2]
        if s.startswith("[") and s.endswith("]"):
            return False
        # constantes simbólicas típicas
        if s in ("null", "true", "false"):
            return False
        return True

    def _compute_liveness(self, quads: List[dict]) -> List[Set[str]]:
        """
        Computa liveness clásico a nivel de instrucción para una función.
        Devuelve una lista live_out[i] con las variables vivas DESPUÉS de la instrucción i.
        Tiene en cuenta gotos, ifgoto y ret para construir un CFG sencillo.
        """
        n = len(quads)
        if n == 0:
            return []

        # Mapa label -> índice
        label_pos: Dict[str, int] = {}
        for i, q in enumerate(quads):
            if q["op"] == "label" and q["label"]:
                label_pos[q["label"]] = i

        # Def y Use por instrucción
        defs: List[Set[str]] = [set() for _ in range(n)]
        uses: List[Set[str]] = [set() for _ in range(n)]

        bin_ops = {"+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!="}

        for i, q in enumerate(quads):
            op = q["op"]
            a1, a2, dst = q["a1"], q["a2"], q["dst"]

            # Definiciones (dst)
            if dst is not None:
                if op in {"assign", "load", "addr_field", "addr_index",
                          "alloc", "alloc_array"} or op in bin_ops or op == "call":
                    if self._is_var_like(dst):
                        defs[i].add(dst)

            # Usos (a1, a2) según la operación
            if op == "assign":
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op == "load":
                # load [fp+2] -> dst   (a1 es dirección)  -> no var
                # load x -> dst        (a1 var)           -> uso
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op == "store":
                # store src, [addr]   -> src var, addr puede ser dirección
                if self._is_var_like(a1):
                    uses[i].add(a1)
                # a2 solo es var si no es dirección
                if self._is_var_like(a2):
                    uses[i].add(a2)
            elif op in bin_ops:
                if self._is_var_like(a1):
                    uses[i].add(a1)
                if self._is_var_like(a2):
                    uses[i].add(a2)
            elif op in {"ifgoto", "if_goto"}:
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op == "param":
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op == "ret":
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op == "print":
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op in {"addr_field", "addr_index"}:
                if self._is_var_like(a1):
                    uses[i].add(a1)
                if self._is_var_like(a2):
                    uses[i].add(a2)
            elif op in {"alloc", "alloc_array"}:
                if self._is_var_like(a1):
                    uses[i].add(a1)
            elif op == "call":
                # a1 es nombre de función -> NO lo tratamos como variable
                # a2 = nargs (número) -> tampoco
                pass
            # label, goto: sin uses (salvo que gates extiendan IR con cosas raras)

        # Sucesores (CFG sencillo)
        succ: List[Set[int]] = [set() for _ in range(n)]
        for i, q in enumerate(quads):
            op = q["op"]
            if op == "goto":
                lab = q["a1"]
                if lab in label_pos:
                    succ[i].add(label_pos[lab])
            elif op in {"ifgoto", "if_goto"}:
                lab = q["a2"]
                # salto si condición verdadera
                if lab in label_pos:
                    succ[i].add(label_pos[lab])
                # y el siguiente como caída
                if i + 1 < n:
                    succ[i].add(i + 1)
            elif op == "ret":
                # no tiene sucesores
                continue
            else:
                if i + 1 < n:
                    succ[i].add(i + 1)

        # Iteración hasta punto fijo
        live_in: List[Set[str]] = [set() for _ in range(n)]
        live_out: List[Set[str]] = [set() for _ in range(n)]

        changed = True
        while changed:
            changed = False
            for i in range(n - 1, -1, -1):
                new_out: Set[str] = set()
                for j in succ[i]:
                    new_out |= live_in[j]
                new_in = uses[i] | (new_out - defs[i])
                if new_out != live_out[i] or new_in != live_in[i]:
                    live_out[i] = new_out
                    live_in[i] = new_in
                    changed = True

        # Nos interesa live_out (vivas DESPUÉS de la instrucción i)
        return live_out

    # ---------- Generación completa ----------
    def generate(self, tac_program) -> str:
        """
        Punto de entrada: recibe el TAC “plano”, lo parte en funciones,
        y emite ASM para cada una con prólogo/epílogo y selección de instrucciones.
        """
        functions = self._split_functions(tac_program)

        for f in functions:
            # Preparar frame y re-anclar el RA a esta función
            frame = Frame(func_name=f.name)
            self.ra.attach_frame(frame)

            # Calcular liveness para la función y pasarlo al RA
            func_liveness = self._compute_liveness(f.quads)
            self.ra.attach_liveness(func_liveness)

            # Etiqueta de función + prólogo
            self.writer.label(f.name)
            self._emit_prolog(frame)

            # Cuerpo: instrucción por instrucción (con índice)
            sel = InstructionSelector(self.writer, self.ra, frame)
            for idx, nq in enumerate(f.quads):
                sel.select_for_quad(nq, idx)

            # Epílogo
            self._emit_epilog(frame)

            # Separador visual
            self.writer.emit("")
            self.writer.emit("# ----------------")

        # Devuelve todo el texto ensamblado
        return self.writer.dump()

    # --- Alias para compatibilidad con tests ---
    def generate_program(self, tac_program) -> str:
        return self.generate(tac_program)
