cuadrado:
.text
  addiu $sp,$sp,-16
  sw $ra,8($sp)
  sw $fp,12($sp)
  addiu $fp,$sp,12
  lw t0, 8($fp)
  lw t1, 8($fp)
  mul t2, t0, t1
  move $v0, t2
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
  addu t0, a, b
  move $v0, t0
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
  # WARN: fallo al traducir quad addr_field t0, 0 -> t2: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'
  sw None, 0(None)
  lw t2, 0(None)
  lw t1, 0(None)
  # WARN: fallo al traducir quad addr_field t2, 0 -> t3: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'
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
  # WARN: fallo al traducir quad addr_field t1, 0 -> t2: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'
  lw t3, 0(None)
  addu t2, None, None
  move $a0, None
  li $v0, 1
  syscall
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
  li t0, 0
  sw t0, -4($fp)
  li t0, 0
  sw t0, -8($fp)
None:
  lw t0, -8($fp)
  li t1, 3
  slt t2, t0, t1
  bne t2, $zero, None
  j None
None:
  lw t1, 0(None)
  lw t0, 0(None)
  lw t3, 0(None)
  lw t4, 0(None)
  sll $t9, None, 2
  addu t5, None, $t9
  lw t6, 0(None)
  addu t5, None, None
  sw None, 0(None)
None:
  lw t5, -8($fp)
  li t6, 1
  addu t1, t5, t6
  sw t1, -8($fp)
  j None
None:
  lw t2, -4($fp)
  li t1, 3
  div t2, t1
  mflo t6
  move $v0, t6
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,16
  jr $ra

