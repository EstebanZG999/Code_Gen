from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Slot:
    name: str
    region: str        # "param" | "local" | "this" | "temp"
    offset: int        # relativo a fp

@dataclass
class ActivationRecord:
    func_name: str
    slots: Dict[str, Slot] = field(default_factory=dict)
    locals_size: int = 0
    params_size: int = 0
    has_this: bool = False

    def add_this(self):
        """
        Coloca 'this' como el primer parámetro lógico.
        Si es un método:
          this -> [fp+2] (arg0)
          param0 -> [fp+3] (arg1)
          param1 -> [fp+4] (arg2)
          ...
        """
        off = self.params_size + 2      # igual que un parámetro normal
        self.slots["this"] = Slot("this", "this", off)
        self.has_this = True
        self.params_size += 1           # cuenta como un "parámetro" más

    def add_param(self, name: str, size: int = 1):
        """
        Params en offsets positivos:
          si no hay this:
              param0 -> [fp+2]
              param1 -> [fp+3]
          si hay this:
              this   -> [fp+2]
              param0 -> [fp+3]
              param1 -> [fp+4]
        """
        off = self.params_size + 2
        self.slots[name] = Slot(name, "param", off)
        self.params_size += size

    def add_local(self, name: str, size: int = 1):
        """
        Locales hacia negativos: fp-1, fp-2, ...
        Eso ya cuadra con el frame:
          [fp-1] -> fp-4 bytes
        """
        self.locals_size += size
        off = -self.locals_size
        self.slots[name] = Slot(name, "local", off)

    def addr_of(self, name: str) -> Optional[Slot]:
        return self.slots.get(name)