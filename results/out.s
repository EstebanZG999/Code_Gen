.text
.globl main
main:
.text
  # --- prologo de main ---
  addiu $sp,$sp,-128
  sw $ra,124($sp)
  sw $fp,120($sp)
  addiu $fp,$sp,116
  # --- fin prologo de main ---
  li $t2, 7
  move $t0, $t2
  li $t2, 10
  addi $sp, $sp, -4
  sw $t2, 0($sp)
  sw $t2, -4($fp)
  sw $t0, -8($fp)
  jal inc
  addi $sp, $sp, 4
  move $t2, $v0
  move $t0, $t2
  li $a0, 4
  li $v0, 9
  syscall
  move $t2, $v0
  lw $t8, -8($fp)
  addi $sp, $sp, -4
  sw $t8, 0($sp)
  addi $sp, $sp, -4
  sw $t2, 0($sp)
  sw $t8, -12($fp)
  sw $t2, -16($fp)
  sw $t0, -20($fp)
  jal Box.constructor
  addi $sp, $sp, 8
  lw $t2, -16($fp)
  move $t0, $t2
  addi $sp, $sp, -4
  sw $t0, 0($sp)
  sw $t2, -24($fp)
  sw $t0, -28($fp)
  jal Box.get
  addi $sp, $sp, 4
  move $t2, $v0
  move $t0, $t2
  li $t2, 1
  li $t8, 2
  li $t6, 3
  li $t7, 3
  sll $a0, $t7, 2
  li $v0, 9
  syscall
  move $t4, $v0
  li $t1, 0
  sll $t5, $t1, 2
  addu $t5, $t4, $t5
  sw $t2, 0($t5)
  li $t5, 1
  sll $t2, $t5, 2
  addu $t2, $t4, $t2
  sw $t8, 0($t2)
  li $t2, 2
  sll $t8, $t2, 2
  addu $t8, $t4, $t8
  sw $t6, 0($t8)
  move $t3, $t4
  addi $sp, $sp, -4
  sw $t3, 0($sp)
  sw $t2, -24($fp)
  sw $t0, -32($fp)
  sw $t8, -36($fp)
  sw $t6, -40($fp)
  sw $t4, -44($fp)
  sw $t1, -48($fp)
  sw $t5, -52($fp)
  sw $t3, -56($fp)
  jal headPlus
  addi $sp, $sp, 4
  move $t2, $v0
  move $t0, $t2
  lw $t8, -20($fp)
  move $t2, $t8
.data
_str_D845:
  .asciiz "r1="
.text
  la $a0, _str_D845
  li $v0, 4
  syscall
  move $a0, $t2
  li $v0, 1
  syscall
  lw $t6, -32($fp)
  move $t2, $t6
.data
_str_5998:
  .asciiz "r2="
.text
  la $a0, _str_5998
  li $v0, 4
  syscall
  move $a0, $t2
  li $v0, 1
  syscall
  move $t2, $t0
.data
_str_5E21:
  .asciiz "r3="
.text
  la $a0, _str_5E21
  li $v0, 4
  syscall
  move $a0, $t2
  li $v0, 1
  syscall
  li $v0, 10
  syscall
  
  # ----------------
inc:
.text
  # --- prologo de inc ---
  addiu $sp,$sp,-128
  sw $ra,124($sp)
  sw $fp,120($sp)
  addiu $fp,$sp,116
  # --- fin prologo de inc ---
  lw $t2, 12($fp)
  li $t0, 1
  addu $t8, $t2, $t0
  sw $t8, -4($fp)
  lw $t8, -4($fp)
  move $v0, $t8
  # --- epilogo de inc ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de inc ---
  
  # ----------------
Box.constructor:
.text
  # --- prologo de Box.constructor ---
  addiu $sp,$sp,-128
  sw $ra,124($sp)
  sw $fp,120($sp)
  addiu $fp,$sp,116
  # --- fin prologo de Box.constructor ---
  lw $t2, 12($fp)
  lw $t0, 16($fp)
  addi $t8, $t2, 0
  sw $t0, 0($t8)
  # --- epilogo de Box.constructor ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de Box.constructor ---
  
  # ----------------
Box.get:
.text
  # --- prologo de Box.get ---
  addiu $sp,$sp,-128
  sw $ra,124($sp)
  sw $fp,120($sp)
  addiu $fp,$sp,116
  # --- fin prologo de Box.get ---
  lw $t2, 12($fp)
  lw $t0, 12($fp)
  addi $t8, $t0, 0
  lw $t6, 0($t8)
  move $v0, $t6
  # --- epilogo de Box.get ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de Box.get ---
  
  # ----------------
headPlus:
.text
  # --- prologo de headPlus ---
  addiu $sp,$sp,-128
  sw $ra,124($sp)
  sw $fp,120($sp)
  addiu $fp,$sp,116
  # --- fin prologo de headPlus ---
  li $t2, 0
  sw $t2, -4($fp)
  lw $t2, 12($fp)
  lw $t0, -4($fp)
  lw $t8, 12($fp)
  sll $t6, $t0, 2
  addu $t6, $t8, $t6
  lw $t4, 0($t6)
  li $t6, 5
  addu $t0, $t4, $t6
  sw $t0, -8($fp)
  lw $t0, -8($fp)
  move $v0, $t0
  # --- epilogo de headPlus ---
  move $sp,$fp
  lw $fp,4($sp)
  lw $ra,8($sp)
  addiu $sp,$sp,12
  jr $ra
  nop  # delay slot
  # --- fin epilogo de headPlus ---
  
  # ----------------

            .data
        _str_MISALIGNED:
            .asciiz "MISALIGNED!\n"

            .text
            __misaligned_store:
            la $a0, _str_MISALIGNED
            li $v0, 4
            syscall

            li $v0, 10
            syscall
        