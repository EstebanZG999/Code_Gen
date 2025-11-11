cuadrado:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  lw t0, 0(None)
  lw t1, 0(None)
  mul t2, None, None
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

# ----------------
externo:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

# ----------------
externo.interno:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  addu t0, None, None
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

# ----------------
Persona.constructor:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  lw t0, 0(None)
  lw t1, 0(None)
  # TODO: instrucción no implementada: addr_field  (addr_field)
  sw None, 0(None)
  lw t2, 0(None)
  lw t1, 0(None)
  # TODO: instrucción no implementada: addr_field  (addr_field)
  sw None, 0(None)
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

# ----------------
Persona.saludar:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  lw t0, 0(None)
  lw t1, 0(None)
  # TODO: instrucción no implementada: addr_field  (addr_field)
  lw t3, 0(None)
  addu t2, None, None
  # TODO: instrucción no implementada: print  (print)
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

# ----------------
promedio:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  # TODO: instrucción no implementada: :=  (:=)
  sw None, 0(None)
  # TODO: instrucción no implementada: :=  (:=)
  sw None, 0(None)
None:
  lw t0, 0(None)
  # TODO: instrucción no implementada: :=  (:=)
  slt t2, None, None
  bne None, $zero, None
  j None
None:
  lw t1, 0(None)
  lw t0, 0(None)
  lw t3, 0(None)
  lw t4, 0(None)
  # TODO: instrucción no implementada: addr_index  (addr_index)
  lw t6, 0(None)
  addu t5, None, None
  sw None, 0(None)
None:
  lw t5, 0(None)
  # TODO: instrucción no implementada: :=  (:=)
  addu t1, None, None
  sw None, 0(None)
  j None
None:
  lw t2, 0(None)
  # TODO: instrucción no implementada: :=  (:=)
  div None, None
  mflo t6
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

