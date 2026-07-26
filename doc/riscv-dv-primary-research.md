# riscv-dv Primary Research for OpenC910

Scope: official `chipsalliance/riscv-dv` sources plus the RISC-V privileged ISA manual. This note is aimed at integrating generated tests into a custom RV64 RTL testbench such as OpenC910.

## Bottom line

- `riscv-dv` is a stimulus generator and co-simulation wrapper. It generates assembly programs, compiles them with a RISC-V GCC toolchain, runs them under a simulator/ISS flow, and compares traces where configured. Inference from that flow: the RTL/testbench side is still your responsibility; `riscv-dv` is not the DUT controller.
- For a custom core, the normal contract is: create a custom target, describe your core features in `riscv_core_setting.sv`, map memory regions, and make the testbench watch the generator’s handshake/signature address.
- OpenC910 can execute `riscv-dv` generated stimulus after a small integration layer is added. It is not directly compatible with the generated ELF/bin files as checked in today.

## Local OpenC910 evidence

The following was verified against OpenC910 commit `b91c90914c19f114d35c8f6b73408eb241ed847c` and the upstream-reference `riscv-dv` checkout at `9e4aab7750ddaeb3071afa5e31add240a57bda21`:

- The OpenC910 build uses `rv64imafdcxtheadc`/`lp64d`; the standard `riscv-dv` RV64IMAFDC instruction subset is therefore a compatible baseline. T-Head custom instructions and the core's vector implementation need separate target work and should be disabled initially.
- OpenC910 resets hart 0 at address `0x0`, while the upstream `riscv-dv` linker script starts at `0x80000000`.
- The smart testbench does not load ELF or raw binary. It reads `inst.pat` and `data.pat`, with instruction data mapped from `0x0` and normal data from `0x40000`.
- The checked-in link script already models those two regions, but its entry point is `__start` and it forces `crt0.o`; a `riscv-dv` image defines its own `_start`. A dedicated linker script is required.
- The existing S-record-to-PAT converter successfully converted a generated image. For the sampled arithmetic test, the adapted image had entry `0x0`, 12,818 bytes of text, and 93,956 bytes total, within the current testbench windows.
- Icarus Verilog 13.0 successfully compiled the complete RTL/testbench into a 404 MiB simulation image.
- A generated `riscv_arithmetic_basic_test` was assembled as RV64IMAFDC, linked at the OpenC910 addresses, converted to PAT, and run on the RTL. After adapting the generated `tohost` completion to the smart testbench PASS magic, simulation printed `simulation finished successfully`, wrote `TEST PASS`, and called `$finish` at simulation time `454850 (100ps)`.

This proves executable compatibility. It does not by itself prove that the current environment provides a strong architectural correctness oracle.

## Compatibility gaps

| Concern | Current OpenC910 behavior | Required integration |
| --- | --- | --- |
| ISA | RV64IMAFDC plus T-Head extensions | Start with RV64IMAFDC; describe unsupported/custom instructions in a C910 target |
| Reset/entry | Reset vector is `0x0`; local entry is `__start` | Link generated `_start` at `0x0` |
| Image format | Reads split `inst.pat`/`data.pat` files | Convert generated ELF sections through S-record and `Srec2vmem`, or add an ELF loader |
| Section map | Text window begins at `0x0`; data begins at `0x40000` | Map all generated data, stack, page-table, and kernel sections explicitly and enforce size limits |
| Completion | Watches two writeback magic values | Prefer monitoring a reserved `signature_addr`/`tohost` store and decoding the protocol |
| Correctness | PASS currently means the program reached its end | Add an architectural retire trace and compare it with Spike/Sail, or use self-checking directed tests |
| Privilege/MMU | C910 has machine/supervisor/user and Sv39-related RTL, but has implementation-specific CSRs and behavior | Use a custom CSR list and begin in machine/bare mode before enabling privileged/MMU tests |
| External events | Smart testbench has fixed peripherals and no riscv-dv handshake driver | Add signature decoding plus explicit interrupt/debug stimulus support for those test families |

The current PASS/FAIL writeback detector also has a typo: its third FAIL comparison checks the PASS magic again. A fail value appearing only on the third observed writeback path would not terminate as FAIL. This should be corrected before relying on regressions.

## Recommended rollout

1. Add a `c910` custom target constrained to one hart, RV64IMAFDC, machine mode, bare address translation, no debug, and conservative interrupt/unaligned settings.
2. Add a C910-specific linker script and image conversion target. Reject images whose executable or initialized-data sections exceed the PAT loader windows.
3. Reserve a signature address outside randomized memory regions, monitor AXI writes to it, and decode completion/status handshakes. Keep the existing magic path for legacy tests.
4. First run arithmetic/control-flow/load-store tests without random exceptions, interrupts, MMU, floating point, or atomics. Add those categories independently after baseline comparison is stable.
5. Export retire PC, instruction, privilege level, register writes, and relevant memory effects in a deterministic order, then adapt the log to a `riscv-dv` trace CSV and compare against an ISS.
6. Preserve seed, generated assembly, ELF, PAT files, RTL log, ISS log, and first mismatch for every failing case.

## Generated artifacts

- Random tests are emitted as assembly under `out/asm_test/*.S`.
- The wrapper then compiles each generated program to ELF and binary (`*.o` and `*.bin`) using `RISCV_GCC` and `RISCV_OBJCOPY`.
- Regressions also produce `seed.yaml` and simulator logs under `*_sim/*.log`.
- Directed assembly/C tests are supported too, and are compiled into the same ELF/bin flow.

## Supported ISA, toolchain, and simulator flow

- The upstream overview states support for RV32IMAFDC and RV64IMAFDC, machine/supervisor/user privilege modes, debug support, page tables, CSR randomization, trap/interrupt handling, and ISS co-simulation.
- `getting_started.rst` says the generator needs a SystemVerilog + UVM 1.2 simulator, and it has been verified with VCS, Incisive/Xcelium, Questa, and Riviera-PRO.
- The same docs list ISS support for Spike, riscv-ovpsim, Whisper, and Sail.
- The `run.py` wrapper selects simulator-specific compile/sim commands from YAML and also supports separate ISS comparison runs.

## Custom target knobs for a custom RV64 core

- `run.py` documents `--custom_target <dir> --isa <isa> --mabi <mabi>` for custom cores. If you use a custom target and run generator/ISS steps, `isa` and `mabi` are required.
- The target template is `target/<name>/riscv_core_setting.sv` and is expected to describe:
  - `XLEN`
  - `SATP_MODE`
  - supported privileged modes
  - unsupported instructions
  - supported ISA groups
  - supported interrupt modes
  - PMP/debug/sfence/unaligned-load-store capability flags
- The checked-in target settings also expose memory-region knobs (`mem_region`, `s_mem_region`, `amo_region`) and per-test control knobs such as `boot_mode_opts`, `mtvec_mode`, and `tvec_alignment`.
- `configuration.rst` explicitly says each memory region becomes a separate section in the generated assembly, and the link script must map those sections to the target memory map.

## Handshake / signature contract

- `require_signature_addr=1` enables the generator to emit handshake code that writes to a configurable `signature_addr`.
- `signature_addr` is a memory-mapped address the testbench should monitor. The docs suggest `0x8ffffffc` as a default example, but it is configurable for the actual SoC memory map.
- `riscv_signature_pkg.sv` defines four handshake encodings:
  - `CORE_STATUS`
  - `TEST_RESULT`
  - `WRITE_GPR`
  - `WRITE_CSR`
- `TEST_RESULT` carries `TEST_PASS` or `TEST_FAIL` and is the generator-level end-of-test contract for self-checking flows.
- `run.py` also exposes `--end_signature_addr` specifically for the CSR test generator, which writes pass/fail at end of test.
- `riscv_asm_program_gen.sv` emits the actual store sequences and expects the testbench to decode them; the package comments explicitly say an RTL simulation environment can import the same package.

## Boot mode and mtvec

- `boot_mode` is a generator plusarg with `m`, `s`, and `u` choices. The docs describe it as machine/supervisor/user boot privilege.
- `riscv_instr_gen_config.sv` has `mtvec_mode`, and the target settings expose `supported_interrupt_mode = {DIRECT, VECTORED}`.
- The RISC-V privileged spec defines `mtvec` as a trap-vector base plus mode register, with `MODE=Direct` sending all traps to `BASE` and `MODE=Vectored` sending interrupts to `BASE + 4*cause`. This is the architectural meaning behind the generator’s `mtvec_mode` knob.

## Practical OpenC910 integration reading

- If OpenC910 is the DUT, `riscv-dv` should be treated as the test program generator and regression harness, not as the DUT controller.
- Your testbench must:
  - boot from the generated program image,
  - provide the memory map expected by the generated sections,
  - observe the signature address,
  - decode `CORE_STATUS` / `WRITE_CSR` / `TEST_RESULT`,
  - and decide pass/fail from the emitted handshake or end signature.
- If you need core-specific behavior beyond the upstream target templates, the intended extension path is to add a custom target and, if necessary, user-extension classes rather than editing upstream classes directly.

## XThead custom-instruction status

- Upstream `riscv-dv` currently advertises only `RV32IMAFDC` and `RV64IMAFDC` as supported instruction sets. That is the standard ISA filtering path, not vendor-specific `XThead` support.
- The documented custom-instruction path is generic and manual: add enum entries in `riscv_custom_instr_enum.sv`, define instructions in `rv32x_instr.sv` / `rv64x_instr.sv`, extend `riscv_custom_instr.sv` to implement `get_instr_name` and `convert2asm`, and add `RV32X` / `RV64X` to `supported_isa` in the target settings.
- The fork initially contained only custom-instruction scaffolding. The `riscv-dv` submodule now implements all 101 RTL-visible C910 private instruction families through the SystemVerilog generator: 19 scalar, 57 private load/store, and 25 cache/synchronization families.
- Private memory instructions are emitted by a directed stream that reloads a generated data-page base before each operation and uses zero offset, scale, step, and pair displacement. Cache instructions with address operands use the same controlled page; cache and synchronization instructions have their own directed stream.
- The Python generator has the same gap: `pygen_src/riscv_instr_pkg.py` still says it needs a way to import custom instructions from `isa/custom/riscv_custom_instr_enum.py`. So enabling `RV64X` in the SV target does not automatically make pygen emit vendor custom opcodes.
- Toolchain and ISS implications: the docs require a RISCV-GCC toolchain and ISS setup, and the flow cross-compares traces with Spike and OVPsim. Inference: if you add XThead instructions, the assembler/toolchain must accept the mnemonics or encodings, and the ISS must decode/execute them, otherwise the co-simulation flow will not be able to validate those tests.

Local toolchain verification:

- The installed vendor compiler is `Xuantie-900 elf newlib gcc Toolchain V2.0.3 B-20210806`, based on GCC 10.2.0.
- Its actual path in this workspace is `/home/u1/projects/coverage_predict/openc910/tools/newlib/bin`; the supplied `/home/u1/coverage_predict/...` path is missing the `projects` component.
- It successfully assembled the complete OpenC910 `ISA_THEAD/isa_thead_smoke.s` with `-march=rv64imafdcxtheadc -mabi=lp64d`. Vendor instructions including `rev` and `ff0` were preserved and recognized by the vendor `objdump`.
- The scalar, private-memory, and cache/synchronization targets were generated with VCS. All 101 custom-instruction families appeared; each generator run reported `TEST PASSED` with zero UVM warnings, errors, and fatals.
- All three generated assemblies were compiled and converted to binary by the Xuantie GCC/objcopy tools. Disassembly confirmed the private mnemonics and that the C910-specific startup selected by the target include path sets `MXSTATUS.THEADISAEE` before executing the generated stream.
- These VCS runs simulate the `riscv-dv` UVM generator, not the OpenC910 RTL DUT. Standard ISS builds do not model these vendor instructions, so the target disables ISS comparison. Cache-state correctness still requires C910 RTL monitors or a cache-aware reference model.
- The three generated groups were also linked to the smart testbench memory map and executed by the OpenC910 RTL under VCS. Scalar seed 13, private-memory seed 12, and cache/synchronization seed 11 all reached the testbench PASS condition. During this validation, the memory test exposed that floating-point state was disabled after machine-mode initialization; adding `+enable_floating_point=1` to that test fixed the eight private floating-point memory operations. This RTL run proves decode/retirement and completion for all 101 generated families, but it still does not provide a reference oracle for cache-state semantics.

Source URLs for this addendum:
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/overview.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/customize_extend_generator.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/end_to_end_simulation.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/extension_support.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/src/isa/custom/riscv_custom_instr_enum.sv
- https://github.com/chipsalliance/riscv-dv/blob/master/src/isa/custom/rv64x_instr.sv
- https://github.com/chipsalliance/riscv-dv/blob/master/src/isa/custom/riscv_custom_instr.sv
- https://github.com/chipsalliance/riscv-dv/blob/master/pygen/pygen_src/riscv_instr_pkg.py

## Source URLs

- https://github.com/chipsalliance/riscv-dv/blob/master/README.md
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/getting_started.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/overview.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/configuration.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/handshake.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/docs/source/end_to_end_simulation.rst
- https://github.com/chipsalliance/riscv-dv/blob/master/run.py
- https://github.com/chipsalliance/riscv-dv/blob/master/src/riscv_instr_gen_config.sv
- https://github.com/chipsalliance/riscv-dv/blob/master/src/riscv_asm_program_gen.sv
- https://github.com/chipsalliance/riscv-dv/blob/master/src/riscv_signature_pkg.sv
- https://github.com/chipsalliance/riscv-dv/blob/master/scripts/gen_csr_test.py
- https://docs.riscv.org/reference/isa/v20260120/priv/machine.html

## Version notes

- Upstream `riscv-dv` docs and `run.py` move over time; this note reflects the current `chipsalliance/riscv-dv` checkout in this workspace and the current upstream `master` URLs above.
- The RISC-V privileged spec URL above is the current machine-level manual page used for the `mtvec` architectural meaning.
