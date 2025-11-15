cuadrado:
.text
  # --- prologo de cuadrado ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de cuadrado ---
  lw t0, 12($fp)
  lw t1, 12($fp)
  mul $t7, $t3, $t2
  move $v0, $t7
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
  addu $t7, $t3, $t2
  move $v0, $t7
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
  lw t0, 8($fp)
  lw t1, 12($fp)
  addi $t2, $t3, 0
  move $t2, $t7
  lw t2, 8($fp)
  lw t1, 16($fp)
  addi $t5, $t9, 0
  move $t5, $t1
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
  lw t0, 8($fp)
  lw t1, 8($fp)
  addi $t2, $t3, 0
  move $t7, $t2
  addu $t5, $t9, $t7
  move $a0, $t5
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
  li $t3, 0
  sw $t3, -4($fp)
  li $t2, 0
  sw $t2, -8($fp)
Lfor_cond0:
  lw t0, -8($fp)
  li $t7, 3
  slt $t5, $t9, $t7
  bne $t5, $zero, None
j None
Lfor_body1:
  lw t1, -4($fp)
  lw t0, 12($fp)
  lw t3, -8($fp)
  lw t4, 12($fp)
  sll $t9, $t0, 2
  addu $t6, $t1, $t9
  move $t4, $t6
  addu $t3, $t8, $t4
  sw $t3, -4($fp)
Lfor_step2:
  lw t5, -8($fp)
  li $t2, 1
  addu $t9, $t7, $t2
  sw $t9, -8($fp)
j None
Lfor_end3:
  lw t2, -4($fp)
  li $t5, 3
  div $t1, $t5
  mflo $t0
  move $v0, $t0
  # --- epilogo de promedio ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de promedio ---
  
  # ----------------
