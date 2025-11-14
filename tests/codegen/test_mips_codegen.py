import re
import textwrap
import pytest

# Ajusta el import a tu árbol real:
from program.codegen.mips.mips_gen import MIPSGenerator

class TACProg:
    """Contenedor mínimo con .code (lista de strings TAC) para el generador."""
    def __init__(self, code):
        self.code = code

def gen_asm(lines):
    """Helper: ejecuta el generador y devuelve el ensamblador como string."""
    gen = MIPSGenerator()
    prog = TACProg([ln for ln in lines if ln.strip()])
    asm = gen.generate(prog)
    # Normaliza espacios por si el writer varia en blank lines
    return "\n".join(l.rstrip() for l in asm.splitlines())

def assert_in_order(haystack, needles):
    """Verifica que varias subcadenas aparezcan en orden (no necesariamente contiguas)."""
    pos = 0
    for n in needles:
        i = haystack.find(n, pos)
        assert i >= 0, f"No se encontró en orden: {n!r}\nASM:\n{haystack}"
        pos = i + len(n)

def assert_regex(pattern, text):
    assert re.search(pattern, text), f"No hizo match regex {pattern!r}\nASM:\n{text}"

# ---------- Tests ----------

def test_binops_and_ret():
    asm = gen_asm([
        "func_main_entry:",
        "t0 := 5",
        "t1 := 7",
        "+ t0, t1 -> t2",
        "ret t2",
        "func_main_end:",
    ])
    # Prolog/epilog genérico (sin fijar tamaño exacto)
    assert_regex(r"addiu \$sp,\$sp,-\d+", asm)
    assert_in_order(asm, [
        "li ",             # li (alguno) , 5
        "li ",             # li (alguno) , 7
        "addu ",           # suma
        "move $v0",        # retorno
        "jr $ra"
    ])

def test_load_store_frame_addressing():
    asm = gen_asm([
        "func_ls_entry:",
        "t0 := 42",
        "store t0, [fp-1]",
        "load [fp-1] -> t1",
        "ret t1",
        "func_ls_end:",
    ])
    # Debe traducir [fp-1] a offset en BYTES: -4($fp)
    assert "sw " in asm and "($fp)" in asm
    assert "lw " in asm and "($fp)" in asm
    assert_in_order(asm, ["li ", "sw ", "lw ", "move $v0", "jr $ra"])

def test_if_goto_and_goto():
    asm = gen_asm([
        "func_if_entry:",
        "if t0 goto L1",
        "goto L2",
        "L1:",
        "ret t1",
        "L2:",
        "ret t0",
        "func_if_end:",
    ])
    # Debe salir un branch condicional y un salto incondicional
    assert "bne " in asm
    assert "\nj L2" in asm or "\nj  L2" in asm
    # Y ambas etiquetas
    assert "\nL1:\n" in asm
    assert "\nL2:\n" in asm

def test_call_param_ret_caller_saved():
    asm = gen_asm([
        "func_caller_entry:",
        "param t0",
        "param t1",
        "call suma, nargs=2 -> t2",
        "ret t2",
        "func_caller_end:",
        "func_suma_entry:",
        "+ t0, t1 -> t2",
        "ret t2",
        "func_suma_end:",
    ])
    # Debe empujar 2 params y luego limpiar stack con 8
    assert_in_order(asm, [
        "addi $sp, $sp, -4",
        "sw ",                         # primer param
        "addi $sp, $sp, -4",
        "sw ",                         # segundo param
        "jal suma",
        "addi $sp, $sp, 8",            # pop de params
    ])
    # Retorno propagado
    assert "move $v0" in asm

def test_relops_basic_eq_lt():
    asm = gen_asm([
        "func_rel_entry:",
        "t0 := 3",
        "t1 := 5",
        "< t0, t1 -> t2",
        "== t0, t1 -> t3",
        "ret t2",
        "func_rel_end:",
    ])
    # slt debe aparecer y el patrón == (subu + sltiu)
    assert "slt " in asm
    assert "subu " in asm and "sltiu " in asm

def test_spilling_basic():
    # Fuerza más de 10 valores vivos para inducir spills.
    body = ["func_spill_entry:"] + [f"t{i} := {i}" for i in range(12)] + [
        "+ t10, t11 -> t12",
        "ret t12",
        "func_spill_end:",
    ]
    asm = gen_asm(body)
    # Debe verse algún sw ... ($fp) que no sea el prologo/epilogo de $ra/$fp,
    # i.e., stores de spill de temporales:
    # Usamos una heurística: buscar 'sw $t' hacia ($fp) en el cuerpo.
    spill_like = re.findall(r"sw \$t\d,\s*-?\d+\(\$fp\)", asm)
    assert spill_like, f"Esperaba ver spills de $t* a frame; ASM:\n{asm}"

def test_print_string_and_int_smoke():
    # Solo humo: que no truene y emita syscalls
    asm = gen_asm([
        'func_pr_entry:',
        'print "Hola Mundo"',
        "t0 := 99",
        "print t0",
        "ret t0",
        "func_pr_end:",
    ])
    # Debe haber syscalls de 4 (string) y 1 (int) en algún sitio
    assert "li $v0, 4" in asm
    assert "li $v0, 1" in asm
    assert "syscall" in asm
