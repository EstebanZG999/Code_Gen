# program/codegen/mips/reg_alloc.py

from typing import Dict, Optional, Tuple, List, Set

T_REGS = [f"$t{i}" for i in range(10)]  # $t0..$t9
S_REGS = [f"$s{i}" for i in range(8)]   # $s0..$s7
USE_S_REGS = False   

class RegAllocator:
    """
    Asignador simple con spill.
    API:
      - attach_frame(frame)          # por función
      - attach_liveness(liveness)    # liveness por instrucción (lista de conjuntos)
      - get_reg(name, across_call=False)
           -> (reg|None, my_spill_off|None, victim|(reg,off)|None)
      - mark_loaded(name)            # llama después de hacer lw reg, off($fp)
      - free_if_dead(name, pc=None)  # libera registro si la variable ya no está viva
      - on_call()                    # cumple convención caller-saved para $t*
    Notas:
      * Si devuelve victim=(reg,off), debes emitir `sw reg, off($fp)` antes de usar el nuevo reg.
      * Si devuelve (None, my_off, _), usa memoria: carga a scratch o almacena desde scratch.
    """

    def __init__(self, liveness: Optional[List[Set[str]]] = None):
        self.frame = None
        # liveness[i] = conjunto de variables vivas DESPUÉS de la instrucción i
        self.liveness: Optional[List[Set[str]]] = liveness
        # name -> (reg|None, spill_off|None). Si spill_off!=None, el valor vive en memoria.
        self.loc: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
        self.free_t = set()
        self.free_s = set()
        self.used_s = set()

    # ------- ciclo de vida por función -------

    def attach_frame(self, frame):
        self.frame = frame
        self.loc.clear()
        self.free_t = set(T_REGS)
        self.free_s = set(S_REGS) if USE_S_REGS else set()
        self.used_s = set()

    def attach_liveness(self, liveness: Optional[List[Set[str]]]):
        """
        Asigna la tabla de liveness de la función actual.
        liveness[i] = conjunto de variables vivas DESPUÉS de la instrucción i.
        """
        self.liveness = liveness

    # ------- utilitarios internos -------

    def _spill_victim(self) -> Optional[str]:
        """
        Política mínima: escoge el primer $t* ocupado en orden T_REGS.
        """
        for r in T_REGS:
            if r not in self.free_t:
                return r
        return None

    def _spill(self, reg: str):
        """
        Mapea reg -> name y asigna spill si no tenía.
        Devuelve (nombre_variable, off_spill).
        """
        for name, (r, off) in self.loc.items():
            if r == reg:
                if off is None:
                    off = self.frame.alloc_spill()
                self.loc[name] = (None, off)
                self.free_t.add(reg)
                return name, off
        return None, None

    # ------- API principal -------

    def get_reg(
        self,
        name: str,
        across_call: bool = False
    ) -> Tuple[Optional[str], Optional[int], Optional[Tuple[str, int]]]:
        """
        Devuelve:
          reg   = registro físico donde vivirá 'name', o None si se trabajará desde memoria.
          off   = offset de spill (si el valor está en memoria y hay que hacer lw/sw).
          victim= (reg_víctima, off_víctima) si hubo que hacer spill de algún registro.
        """

        # Ya en registro
        if name in self.loc and self.loc[name][0] is not None:
            return self.loc[name][0], None, None

        # Estaba derramado -> asigna reg y devuelve offset para que hagas lw
        if name in self.loc and self.loc[name][0] is None and self.loc[name][1] is not None:
            off = self.loc[name][1]
            # intenta $t* primero (si no across_call)
            if not across_call and self.free_t:
                r = self.free_t.pop()
                self.loc[name] = (r, off)   # pendiente de cargar
                return r, off, None
            # usa $s* si está habilitado
            if self.free_s:
                r = self.free_s.pop()
                self.used_s.add(r)
                self.loc[name] = (r, off)
                return r, off, None
            # sin registros: sigue en memoria
            return None, off, None

        # Nuevo símbolo: intenta $t* / $s*
        if not across_call and self.free_t:
            r = self.free_t.pop()
            self.loc[name] = (r, None)
            return r, None, None

        if self.free_s:
            r = self.free_s.pop()
            self.used_s.add(r)
            self.loc[name] = (r, None)
            return r, None, None

        # Spill víctima de $t*
        victim = self._spill_victim()
        if victim:
            vname, voff = self._spill(victim)
            # Slot propio para 'name'
            my_off = self.frame.alloc_spill()
            self.loc[name] = (None, my_off)
            return None, my_off, (victim, voff)

        # Todo lleno: trabaja en memoria
        my_off = self.frame.alloc_spill()
        self.loc[name] = (None, my_off)
        return None, my_off, None

    def mark_loaded(self, name: str):
        reg, off = self.loc.get(name, (None, None))
        if reg is not None:
            # ya se hizo lw reg,off($fp), así que ya no necesitamos el offset
            self.loc[name] = (reg, None)

    def free_if_dead(self, name: str, pc: Optional[int] = None):
        """
        (Temporalmente) no liberamos registros en base a liveness.
        Esto evita que se pierdan valores que luego se necesitan (como r3).
        """
        return

    def on_call(self):
        """
        Convención caller-saved: devolver lista de (reg, off) para guardar antes del jal.
        Luego marca esos temporales como derramados y libera $t*.
        """
        saves = []
        for name, (r, off) in list(self.loc.items()):
            if r in T_REGS:
                if off is None:
                    off = self.frame.alloc_spill()
                # pedir al caller: sw r, off($fp)
                saves.append((r, off))
                # marcar como derramado
                self.loc[name] = (None, off)
        self.free_t = set(T_REGS)
        return saves
