# Rutinas auxiliares opcionales (por ejemplo, imprimir enteros/strings si tu lenguaje lo requiere).
# Ejemplo mínimo de etiqueta vacía para enlazar si lo necesitas:
# .text
# print_int:
#   # Asume entero en $a0 y usa syscall si tu simulador lo permite (MARS/QtSPIM).
#   li $v0, 1
#   syscall
#   jr $ra
