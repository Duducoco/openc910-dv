/* OpenC910 Smart testbench memory map for riscv-dv generated programs. */
OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
  IMEM (rx)  : ORIGIN = 0x00000000, LENGTH = 0x00040000
  DMEM (rwx) : ORIGIN = 0x00040000, LENGTH = 0x00040000
}

SECTIONS
{
  .text :
  {
    *(.text)
    *(.text.*)
  } > IMEM

  .rodata :
  {
    *(.rodata)
    *(.rodata.*)
    *(.srodata)
    *(.srodata.*)
  } > IMEM

  .data :
  {
    *(.data)
    *(.data.*)
    *(.sdata)
    *(.sdata.*)
  } > DMEM

  .test_data :
  {
    *(.region_*)
    *(.user_stack*)
    *(.kernel_data*)
    *(.kernel_stack*)
    *(.h*_data*)
    *(.h*_user_stack*)
    *(.h*_kernel_data*)
    *(.h*_kernel_stack*)
    *(.page_table*)
    *(.tohost*)
  } > DMEM

  .bss (NOLOAD) :
  {
    *(.bss)
    *(.bss.*)
    *(.sbss)
    *(.sbss.*)
    *(COMMON)
  } > DMEM

  _end = .;

  ASSERT(ADDR(.text) == ORIGIN(IMEM), "riscv-dv entry must be at 0x0")
  ASSERT(SIZEOF(.text) + SIZEOF(.rodata) <= LENGTH(IMEM),
         "riscv-dv instruction image exceeds OpenC910 IMEM")
  ASSERT(_end <= ORIGIN(DMEM) + LENGTH(DMEM),
         "riscv-dv data image exceeds OpenC910 DMEM")
}
