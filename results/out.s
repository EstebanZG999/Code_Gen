cuadrado:
.text
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  lw t0, 8($fp)
  lw t1, 8($fp)
  mul $t0, $t7, $t5
  move $v0, $t0
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  
  # ----------------
externo:
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  
  # ----------------
externo.interno:
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  addu $t0, $t7, $t5
  move $v0, $t0
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  
  # ----------------
Persona.constructor:
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  lw t0, 4($fp)
  lw t1, 8($fp)
  addi $t5, $t7, 0
  move $t5, $t0
  lw t2, 4($fp)
  lw t1, 12($fp)
  addi $t3, $t2, 0
  move $t3, $t9
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  
  # ----------------
Persona.saludar:
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  lw t0, 4($fp)
  lw t1, 4($fp)
  addi $t5, $t7, 0
  move $t0, $t5
  addu $t3, $t2, $t0
  move $a0, $t3
  li $v0, 1
  syscall
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  
  # ----------------
promedio:
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  li $t7, 0
  sw $t7, -4($fp)
  li $t5, 0
  sw $t5, -8($fp)
Lfor_cond0:
  lw t0, -8($fp)
  li $t0, 3
  slt $t3, $t2, $t0
  bne $t3, $zero, None
j None
Lfor_body1:
  lw t1, -4($fp)
  lw t0, 8($fp)
  lw t3, -8($fp)
  lw t4, 8($fp)
  sll $t9, $t4, 2
  addu $t6, $t9, $t9
  move $t8, $t6
  addu $t7, $t1, $t8
  sw $t7, -4($fp)
Lfor_step2:
  lw t5, -8($fp)
  li $t5, 1
  addu $t2, $t0, $t5
  sw $t2, -8($fp)
j None
Lfor_end3:
  lw t2, -4($fp)
  li $t2, 3
  div $t3, $t2
  mflo $t9
  move $v0, $t9
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  
  # ----------------
