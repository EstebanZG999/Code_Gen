cuadrado:
.text
  # --- prologo de cuadrado ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de cuadrado ---
  lw t0, 8($fp)
  lw t1, 8($fp)
  mul $t1, $t2, $t8
  move $v0, $t1
  # --- epilogo de cuadrado ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de cuadrado ---
  
  # ----------------
externo:
  # --- prologo de externo ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de externo ---
  # --- epilogo de externo ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de externo ---
  
  # ----------------
externo.interno:
  # --- prologo de externo.interno ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de externo.interno ---
  addu $t1, $t2, $t8
  move $v0, $t1
  # --- epilogo de externo.interno ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de externo.interno ---
  
  # ----------------
Persona.constructor:
  # --- prologo de Persona.constructor ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de Persona.constructor ---
  lw t0, 4($fp)
  lw t1, 8($fp)
  addi $t8, $t2, 0
  move $t8, $t1
  lw t2, 4($fp)
  lw t1, 12($fp)
  addi $t4, $t0, 0
  move $t4, $t7
  # --- epilogo de Persona.constructor ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de Persona.constructor ---
  
  # ----------------
Persona.saludar:
  # --- prologo de Persona.saludar ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de Persona.saludar ---
  lw t0, 4($fp)
  lw t1, 4($fp)
  addi $t8, $t2, 0
  move $t1, $t8
  addu $t4, $t0, $t1
  move $a0, $t4
  li $v0, 1
  syscall
  # --- epilogo de Persona.saludar ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de Persona.saludar ---
  
  # ----------------
promedio:
  # --- prologo de promedio ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de promedio ---
  li $t2, 0
  sw $t2, -4($fp)
  li $t8, 0
  sw $t8, -8($fp)
Lfor_cond0:
  lw t0, -8($fp)
  li $t1, 3
  slt $t4, $t0, $t1
  bne $t4, $zero, None
j None
Lfor_body1:
  lw t1, -4($fp)
  lw t0, 8($fp)
  lw t3, -8($fp)
  lw t4, 8($fp)
  sll $t9, $t4, 2
  addu $t5, $t7, $t9
  move $t9, $t5
  addu $t3, $t6, $t9
  sw $t3, -4($fp)
Lfor_step2:
  lw t5, -8($fp)
  li $t2, 1
  addu $t1, $t8, $t2
  sw $t1, -8($fp)
j None
Lfor_end3:
  lw t2, -4($fp)
  li $t0, 3
  div $t8, $t0
  mflo $t4
  move $v0, $t4
  # --- epilogo de promedio ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de promedio ---
  
  # ----------------
