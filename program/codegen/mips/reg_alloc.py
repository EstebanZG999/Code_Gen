# program/codegen/mips/reg_alloc.py

from typing import Dict, Optional, Tuple, List, Set

T_REGS = [f"$t{i}" for i in range(10)]  # $t0..$t9
S_REGS = [f"$s{i}" for i in range(8)]   # $s0..$s7
USE_S_REGS = False   

class RegAllocator:
    """
    Asignador simple:
      - Preferir $t* para temporales.
      - Si vive a través de call, permitir $s* (y marcar para salvar/restaurar en prolog/epilog).
      - Si no hay registros, hacer spill: devolver (None, spill_slot_offset) para forzar lw/sw.
    """

    def __init__(self, frame, liveness=None):
        self.frame = frame
        self.liveness = liveness or {}
        self.loc: Dict[str, Tuple[Optional[str], Optional[int]]] = {}  # name -> (reg or None, spill_off or None)
        self.free_t = set(T_REGS)
        self.free_s = set(S_REGS)

    def _spill_victim(self) -> Optional[str]:
        # Política mínima: víctima = algún $t* ocupado con next-use lejano o None
        for r in T_REGS:
            if r not in self.free_t:
                return r
        return None

    def _spill(self, reg: str):
        # Encuentra quién tenía 'reg', le asigna spill slot y lo libera
        for name, (r, off) in self.loc.items():
            if r == reg:
                if off is None:
                    off = self.frame.alloc_spill()
                    self.loc[name] = (None, off)
                self.free_t.add(reg)
                return name, off
        return None, None

    def get_reg(self, name: str, across_call: bool = False) -> Tuple[Optional[str], Optional[int], Optional[Tuple[str,int]]]:
        """
        Devuelve:
         - reg asignado (o None si debe usarse memoria),
         - spill_slot propio si no cabe en registros,
         - (victim_reg, victim_spill_off) si hubo que hacer spill de una víctima (para que el caller emita sw).
        """
        # Ya asignado
        if name in self.loc and self.loc[name][0] is not None:
            return self.loc[name][0], None, None

        # Intentar $t* si no cruza call
        if not across_call and self.free_t:
            r = self.free_t.pop()
            self.loc[name] = (r, None)
            return r, None, None

        # Intentar $s* si cruza call (o no quedan $t)
        if self.free_s:
            r = self.free_s.pop()
            self.loc[name] = (r, None)
            return r, None, None

        # Spill víctima de $t*
        victim = self._spill_victim()
        if victim:
            vname, voff = self._spill(victim)
            # El actual no obtiene reg, forzar uso de memoria
            my_off = self.frame.alloc_spill()
            self.loc[name] = (None, my_off)
            return None, my_off, (victim, voff)

        # No hay nada que hacer: memoria
        my_off = self.frame.alloc_spill()
        self.loc[name] = (None, my_off)
        return None, my_off, None

    def free_if_dead(self, name: str):
        reg, off = self.loc.get(name, (None, None))
        if reg and reg in T_REGS:
            self.free_t.add(reg)
        if reg and reg in S_REGS:
            self.free_s.add(reg)
        # dejamos mapeo por si reusamos spill; en un alloc más avanzado podríamos limpiar
