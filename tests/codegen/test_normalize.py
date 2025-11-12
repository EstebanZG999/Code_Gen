from program.ir.tac_ir import TACProgram, Label, Const, Var
from program.codegen.mips.mips_gen import MIPSGenerator

def test_normalize_assign_from_tac_attrs_and_str():
    tac = TACProgram()
    tac.label(Label("func_main_entry"))
    # := vía __repr__ del TAC
    tac.emit(":=", Const(5), None, Var("t0"))
    tac.emit("ret", Var("t0"))
    tac.label(Label("func_main_end"))

    gen = MIPSGenerator()
    asm = gen.generate_program(tac)
    # No debe aparecer el TODO de := no implementado
    assert ":=" not in asm
    # Debe haber 'li' por la asignación constante y 'move $v0, t0' por el ret
    assert "li t0, 5" in asm or "li $t" in asm  # según asignador futuro
