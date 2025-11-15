# program/codegen/mips/frame.py

from dataclasses import dataclass, field
from typing import Dict

# Convención de offsets relativos a $fp:
# 
#   fp + 12 -> arg0
#   fp + 16 -> arg1
#   fp + 20 -> arg2
#
#   fp + 8  -> $ra
#   fp + 4  -> old $fp
#   fp + 0  -> (sin uso / padding)
#
#   fp - 4  -> locales / spills
#   fp - 8  -> locales / spills
#   fp - 12 -> ...
#
# El tamaño del frame (frame_size) solo incluye:
#   - 8 bytes para old $fp y $ra
#   - 4 bytes por cada local/spill
# y se alinea a múltiplos de 8.

@dataclass
class Frame:
    func_name: str
    num_params: int = 0
    num_locals: int = 0
    spill_slots: int = 0
    local_offsets: Dict[str, int] = field(default_factory=dict)

    # Offsets fijos para el prólogo/epílogo (relativos a $fp)
    SAVED_FP_OFFSET: int = 4            # fp + 4  -> old $fp
    SAVED_RA_OFFSET: int = 8            # fp + 8  -> $ra

    # Siguiente offset negativo disponible para locals/spills
    _next_neg_offset: int = field(default=-4, init=False)

    # Asignación de locales
    def alloc_local(self, name: str) -> int:
        """
        Reserva un slot de 4 bytes para una variable local con nombre.
        Devuelve el offset relativo a $fp (negativo).
        Ejemplo: -4, -8, -12, ...
        """
        off = self._next_neg_offset
        self._next_neg_offset -= 4
        self.num_locals += 1
        self.local_offsets[name] = off
        return off

    def alloc_spill(self) -> int:
        """
        Reserva un slot de 4 bytes para un spill del asignador de registros.
        Comparte el mismo espacio negativo que las variables locales.
        """
        off = self._next_neg_offset
        self._next_neg_offset -= 4
        self.spill_slots += 1
        return off

    # Acceso a locales
    def offset_of_local(self, name: str) -> int:
        """
        Devuelve el offset relativo a $fp para una variable local ya registrada.
        """
        return self.local_offsets[name]

    # Parámetros
    def offset_of_param(self, i: int) -> int:
        """
        Devuelve el offset relativo a $fp del parámetro i.

            arg0 -> fp + 12
            arg1 -> fp + 16
            arg2 -> fp + 20
            ...
            arg_i -> fp + 12 + 4*i
        """
        if i < 0:
            raise IndexError(f"Parámetro fuera de rango: {i}")
        return 12 + 4 * i

    # Tamaño del frame
    def _locals_spills_size(self) -> int:
        """
        Bytes usados por locales + spills (cada uno 4 bytes).
        """
        return 4 * (self.num_locals + self.spill_slots)

    def frame_size(self) -> int:
        """
        Tamaño total del frame en bytes, alineado a 8.

        Incluye:
            - 12 bytes de cabecera (old $fp, $ra y padding)
            - 4 * (num_locals + spill_slots)
        NO incluye parámetros (son parte del caller).
        """
        base = 12
        extra = self._locals_spills_size()
        total = base + extra
        # redondeo hacia arriba a múltiplo de 8
        if total % 8 != 0:
            total += 8 - (total % 8)
        return total
