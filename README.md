#  Proyecto de Compiladores — Code Generation (Compiscript)

Este repositorio implementa la última etapa del compilador de **Compiscript**: la **generación de código MIPS** a partir de código intermedio en **Three Address Code (TAC)**.  
Las fases anteriores (análisis léxico/sintáctico, análisis semántico y construcción de TAC) ya vienen provistas; en este proyecto se completa el *backend* y se integra todo el *pipeline* de compilación.

Al final, a partir de un archivo `.cps` se obtiene un archivo ensamblador `.s` ejecutable en simuladores como **MARS** o **QtSPIM**.


## Flujo de compilación

El punto de entrada principal es `program/Driver.py`, que orquesta todo el proceso:

1. **Análisis léxico y sintáctico**  
   - Gramática: `program/Compiscript.g4`  
   - Se usa ANTLR4 para generar el parser de Compiscript.

2. **Análisis semántico**  
   - Módulos en `program/semantic/` (`table.py`, `typesys.py`, `type_checker.py`, …).  
   - Construye la tabla de símbolos, valida tipos, *scopes* y reporta errores.

3. **Generación de TAC (Three Address Code)**  
   - IR y construcción de TAC documentados en `README_IR.md`.  
   - Se genera una representación de nivel medio independiente de la arquitectura.

4. **Generación de código MIPS**  
   - Implementada en `program/codegen/mips/`.  
   - Usa un generador de alto nivel, un *frame* de activación por función y un asignador de registros con *spilling*.  
   - Emite el ensamblador final en `results/out.s` (o la ruta indicada por el usuario).


## Arquitectura del backend MIPS

Los módulos principales de esta fase son:

- `program/codegen/mips/mips_gen.py`  
  Generador MIPS de alto nivel:
  - Parte el programa TAC en funciones usando labels `func_<name>_entry:` y `func_<name>_end:`.
  - Normaliza cada quad a un diccionario `{op, a1, a2, dst, label}`.
  - Calcula **liveness** por instrucción para cada función.
  - Crea un `Frame` por función, lo conecta con el `RegAllocator` y emite prólogo/epílogo.
  - Invoca al `InstructionSelector` para bajar cada quad a instrucciones MIPS concretas.

- `program/codegen/mips/frame.py`  
  Define la clase `Frame`, que modela el **registro de activación** de cada función:
  - Reserva offsets negativos para **locales** y **spill slots**.
  - Expone `alloc_local`, `alloc_spill`, `offset_of_local` y `offset_of_param(i)`.
  - Calcula `frame_size()` alineado a 8 bytes para mantener un stack limpio.

- `program/codegen/mips/reg_alloc.py`  
  Implementa el **asignador de registros**:
  - Mapea temporales lógicos (`t0`, `t1`, …) y variables a registros reales `$t0–$t9` (y opcionalmente `$s0–$s7`).
  - Usa información de **liveness** y *next-use* para decidir qué valores mantener en registros.
  - Implementa *spilling*: elige víctimas, escribe a slots del frame y recarga cuando es necesario.
  - Expone la API:
    - `get_reg(name, across_call=False)`
    - `free_if_dead(name, pc)`
    - `on_call()` para manejar registros caller‑saved alrededor de llamadas.

- `program/codegen/mips/instr_sel.py`  
  Selector de instrucciones:
  - Traduce operaciones TAC a instrucciones MIPS:
    - Aritmética: `+`, `-`, `*`, `/`, `%`
    - Relacionales: `<`, `<=`, `>`, `>=`, `==`, `!=`
    - Asignaciones, `load`, `store`, `goto`, `ifgoto`
    - `ret`, `param`, `call`
    - `print` (enteros y cadenas)
    - Operaciones de dirección: `addr_field`, `addr_index`
    - Memoria dinámica: `alloc`, `alloc_array`
  - Interactúa con el `RegAllocator` para decidir cuándo usar registros y cuándo acceder a memoria.

- `program/codegen/mips/runtime.s`  
  Rutinas de soporte en MIPS:
  - Envuelve *syscalls* de impresión para enteros y cadenas.
  - Provee primitivas básicas para trabajar con memoria dinámica (por ejemplo, vía `sbrk`).


## Convención de llamada y layout del frame

Se adoptó una convención de llamada coherente con un MIPS clásico (MARS/QtSPIM), con palabra de **4 bytes** y un registro de marco `$fp`.

Tras ejecutar el prólogo de una función, el layout relativo a `$fp` es:

```txt
    fp + 12  → arg0
    fp + 16  → arg1
    fp + 20  → arg2
    ...      → ...

    fp + 8   → saved $ra
    fp + 4   → old $fp
    fp + 0   → (padding / no usado)

    fp - 4   → local / spill 0
    fp - 8   → local / spill 1
    fp - 12  → ...
```

### Prólogo

Sea `fs = frame.frame_size()` (tamaño total del frame de la función, **sin** incluir parámetros):

```asm
addiu $sp, $sp, -fs     # reserva espacio para old $fp, $ra y locales/spills
sw   $ra, fs-4($sp)     # futuro fp+8
sw   $fp, fs-8($sp)     # futuro fp+4
addiu $fp, $sp, fs-12   # fija $fp para respetar el layout anterior
```

### Epílogo

El epílogo es el inverso del prólogo:

```asm
move $sp, $fp
lw   $fp, 4($sp)        # old $fp
lw   $ra, 8($sp)        # saved $ra
addiu $sp, $sp, 12      # restaura stack al estado de entrada
jr   $ra
nop                     # delay slot
```

### Pasaje de parámetros y retorno

- El **caller** empuja los argumentos en la pila de derecha a izquierda, de 4 bytes cada uno:

  ```asm
  # param x
  addi $sp, $sp, -4
  sw   <valor_x>, 0($sp)
  ```

- Para llamar a `f` con `n` argumentos:

  ```asm
  # ... param arg_n; ...; param arg_1
  jal f
  addi $sp, $sp, n*4     # limpia los parámetros después del retorno
  ```

- Dentro de la función llamada, los parámetros se ven como:

  ```txt
  arg0 → 12($fp)
  arg1 → 16($fp)
  ...
  ```

- El valor de retorno siempre se coloca en `$v0` antes de ejecutar el epílogo.

### Uso de registros

- `$t0–$t9`: registros **caller‑saved**, usados por el asignador como temporales generales.  
- `$s0–$s7`: registros **callee‑saved**; la infraestructura de `Frame` y `RegAllocator` permite salvarlos/restaurarlos si se decide usarlos.  
- El diseño favorece el uso de `$t*` y recurre a *spilling* en el frame cuando no hay registros libres.


## Trabajo por etapa

El desarrollo del backend se organizó en tres etapas, cada una con objetivos claros pero acoplados a un mismo contrato de frame y convención de llamada.

### Etapa 1 — Asignación de registros

**Archivos:** `program/codegen/mips/reg_alloc.py`, integración en `instr_sel.py`.

Objetivos principales:

- Implementar un asignador de registros real:
  - Asigna temporales lógicos (`t0`, `t1`, …) y variables a registros `$t0–$t9` (y potencialmente `$s0–$s7`).
  - Usa información de **liveness** y de **uso futuro** para escoger buenas víctimas de spilling.
- Implementar *spilling*:
  - Cuando no hay registros libres, elige un valor para “tirar” al frame.
  - Emite `sw` hacia un slot del `Frame` y recarga con `lw` cuando es necesario reutilizarlo.
- Diseñar la API:
  - `get_reg(name, across_call=False)` — devuelve `(reg, offset, victim)` según la estrategia de asignación.
  - `free_if_dead(name, pc)` — libera registros cuando una variable deja de estar viva.
  - `on_call()` — avisa del punto de llamada para preservar cualquier registro caller‑saved que lo requiera.
- Integrar con el `InstructionSelector` para que:
  - Las operaciones TAC trabajen casi siempre sobre registros.
  - Cuando no hay registro disponible, se opere a través de memoria (spill slots).

### Etapa 2 — Llamadas, parámetros, runtime y direcciones

**Archivos:** `program/codegen/mips/instr_sel.py` (secciones de `param`, `call`, `ret`, `print`, `addr_field`, `addr_index`, `alloc`, `alloc_array`) y `program/codegen/mips/runtime.s`.

Objetivos principales:

- **Llamadas y parámetros**:
  - Implementar `param` empujando argumentos en la pila (4 bytes, derecha → izquierda).
  - Implementar `call`:
    - Guardar los registros necesarios (caller‑saved) usando `RegAllocator.on_call()`.
    - Emitir `jal f`.
    - Limpiar los parámetros (`addi $sp, $sp, n*4`) después del retorno.
    - Copiar el resultado de `$v0` al temporal TAC correspondiente.
- **Retornos (`ret`)**:
  - Mover el valor de retorno a `$v0` cuando corresponde.
  - Delegar el resto al epílogo del generador.
- **Print y runtime**:
  - Implementar `print` para enteros y cadenas:
    - Cadenas literales: colocar en `.data` con etiquetas `_str_*` y usar syscall 4.
    - Enteros: mover a `$a0` y usar syscall 1.
  - Documentar y utilizar las rutinas auxiliares del `runtime.s`.
- **Direcciones y memoria**:
  - `addr_field`: calcular `base + offset*4` para acceder a campos de objetos.
  - `addr_index`: calcular `base + (i << 2)` para indexar arreglos.
  - `alloc` / `alloc_array`: reservar memoria vía syscall 9 (`sbrk`), almacenando el puntero devuelto en el destino TAC.

### Etapa 3 — Frames, prólogos y epílogos

**Archivos:** `program/codegen/mips/frame.py`, `program/codegen/mips/mips_gen.py`.

Objetivos principales:

- Definir la estructura del **frame**:
  - Implementar `alloc_local` y `alloc_spill` para reservar offsets negativos en múltiplos de 4.
  - Implementar `offset_of_param(i)` según el layout `12($fp)`, `16($fp)`, etc.
  - Garantizar que `frame_size()` incluya:
    - 8 bytes para `old $fp` y `$ra`.
    - 4 bytes por cada local y spill.
    - Alineación final a múltiplos de 8.
- Implementar el **prólogo y epílogo** en `MIPSGenerator`:
  - Guardar `$fp` y `$ra` respetando el contrato de offsets.
  - Ajustar `$sp` según el tamaño del frame.
  - Restaurar `$fp` y `$ra` en el epílogo y volver con `jr $ra`.
- Integrar todo en el generador:
  - Para cada función:
    - Crear un `Frame` nuevo.
    - Conectarlo con el `RegAllocator` (`attach_frame`).
    - Calcular liveness y pasarlo al asignador.
    - Emitir la etiqueta de la función, el prólogo, el cuerpo (vía `InstructionSelector`) y el epílogo.


## Cómo ejecutar el compilador

### 1. Ejecución directa con Python

Requisitos mínimos:

- Python 3.10+
- Dependencias listadas en `requirements.txt`
- ANTLR4 instalado si se quieren regenerar los archivos del parser

Pasos recomendados:

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual 
source .venv/bin/activate      # Linux/macOS (recomendado)
.venv\Scripts\activate.bat     # Windows

pip install -r requirements.txt
```

### 2. Ejecución con Docker

El repositorio incluye un `Makefile` con *targets* para trabajar dentro de un contenedor Docker:

```bash
# Construir la imagen
make docker-build

# Generar archivos de ANTLR dentro del contenedor
make gen

# Ejecutar el driver con el programa por defecto (program/program.cps)
make run
```

Esto monta el repositorio en `/workspace` dentro del contenedor y ejecuta `program/Driver.py` con la configuración adecuada.

## 3. Ejecutar el driver sobre un programa de ejemplo
```
python -m program.Driver program/program_ok.cps --mips results/out.s
```
> Esto lo puedes correr sin el Docker también, pero para más pruebas lo puedes levantar todo.

Esto generará el archivo `results/out.s` con el ensamblador MIPS equivalente al programa de ejemplo, incluyendo:

- Funciones simples (`cuadrado`)
- Funciones anidadas (`externo` / `interno`)
- Clases y métodos (`Persona`, `constructor`, `saludar`)
- Arreglos, bucles `for` y cálculos (`promedio`)

El archivo resultante se puede cargar en **MARS** o **QtSPIM** para inspeccionar y ejecutar el código.


## Pruebas automatizadas

Las pruebas se encuentran en el directorio `tests/` y cubren:

- Generación de TAC (`tests/ir/`)
- Semántica (`tests/semantic/`)
- Backend MIPS (`tests/codegen/`)

Para ejecutarlas (recomendado hacerlo vía Docker):

```bash
# Dentro del contenedor (via Makefile)
make test
```

o, si se desea correr directamente con Python:

```bash
pip install pytest
pytest -q
```

Las pruebas de `tests/codegen/` verifican tanto la normalización de quads como la correcta emisión de MIPS (prólogos, epílogos, llamadas, operaciones aritméticas, etc.).


## Ejemplo rápido de uso

```bash
# 1. Compilar un programa de ejemplo a MIPS
python -m program.Driver program/program_ok.cps --mips results/out.s

# 2. Abrir results/out.s en MARS / QtSPIM
#    - Cargar el archivo .s
#    - Verificar el layout del stack y el flujo de ejecución paso a paso
```

Este ejemplo recorre:

- Definición de constantes y variables globales.
- Funciones (simples y anidadas).
- Definición de clases y métodos.
- Creación de objeto `Persona` y llamada a `saludar()`.
- Construcción de un arreglo de enteros y cálculo de su promedio.
