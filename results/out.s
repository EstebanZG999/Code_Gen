cuadrado:
.text
  # --- prologo de cuadrado ---
  addiu $sp,$sp,-16
  sw $ra,12($sp)
  sw $fp,8($sp)
  addiu $fp,$sp,4
  # --- fin prologo de cuadrado ---
  lw $t8, 12($fp)
  lw $t3, 12($fp)
  mul $t5, $t8, $t3
  move $v0, $t5
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
  addu $t5, $t8, $t3
  move $v0, $t5
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
  lw $t8, 12($fp)
  lw $t3, 16($fp)
  addi $t5, $t8, 0
  sw $t3, 0($t5)
  lw $t5, 12($fp)
  lw $t6, 20($fp)
  addi $t7, $t5, 0
  sw $t6, 0($t7)
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
  lw $t8, 12($fp)
  lw $t3, 12($fp)
  addi $t5, $t3, 0
  lw $t6, 0($t5)
  addu $t0, $t7, $t6
  move $a0, $t0
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
  li $t8, 0
  sw $t8, -4($fp)
  li $t3, 0
  sw $t3, -8($fp)
Lfor_cond0:
  lw $t5, -8($fp)
  li $t6, 3
  slt $t7, $t5, $t6
  bne $t7, $zero, Lfor_body1
j Lfor_end3
Lfor_body1:
  lw $t7, -4($fp)
  lw $t0, 12($fp)
  lw $t4, -8($fp)
  lw $t2, 12($fp)
  sll $t1, $t4, 2
  addu $t1, $t2, $t1
  lw $t9, 0($t1)
  addu $t8, $t7, $t9
  sw $t8, -4($fp)
Lfor_step2:
  lw $t9, -8($fp)
  li $t3, 1
  addu $t5, $t9, $t3
  sw $t5, -8($fp)
j Lfor_cond0
Lfor_end3:
  lw $t5, -4($fp)
  li $t6, 3
  div $t5, $t6
  mflo $t7
  move $v0, $t7
  # --- epilogo de promedio ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de promedio ---
  
  # ----------------
