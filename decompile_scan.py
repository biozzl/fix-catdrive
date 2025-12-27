import sys
import struct

try:
    from capstone import *
    from capstone.arm64 import *
    HAS_CAPSTONE = True
except ImportError:
    print("CRITICAL: Capstone not installed.")
    HAS_CAPSTONE = False

def scan_firmware_v2():
    filename = '623.8.1.bin'
    
    with open(filename, 'rb') as f:
        code = f.read()

    # 1. 寻找标准锚点字符串 "SF: Detected"
    # 这是 U-Boot 原生代码，编译器通常会生成标准的引用指令，比较好抓
    anchor_str = b'SF: Detected'
    anchor_offset = code.find(anchor_str)
    
    if anchor_offset == -1:
        print("Error: 找不到标准字符串 anchor")
        return

    print(f"[*] 锚点字符串 'SF: Detected...' 位于: {hex(anchor_offset)}")

    if not HAS_CAPSTONE:
        return

    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.detail = True

    print("[*] 正在扫描引用锚点的代码 (反向追踪)...")
    
    # 扫描整个代码段 (前 1MB)
    found_refs = []
    
    # 优化扫描：同时寻找 ADR (相对) 和 LDR (加载文字池)
    # 遍历所有 4 字节对齐的地址
    limit = min(len(code), 0xC0000) # 只扫前 768KB
    
    for addr in range(0, limit, 4):
        # 读 4 字节指令
        raw = code[addr:addr+4]
        insn_val = struct.unpack('<I', raw)[0]
        
        # --- 检查 1: ADR 指令 ---
        # 100xxxxx ...
        if (insn_val & 0x1F000000) == 0x10000000:
            # 手动解码 ADR 偏移
            immlo = (insn_val >> 29) & 0x3
            immhi = (insn_val >> 5) & 0x7FFFF
            imm = (immhi << 2) | immlo
            if imm & 0x100000: imm -= 0x200000 # Sign extend
            
            target = addr + imm
            # 如果指向了锚点附近 (允许 64 字节误差)
            if abs(target - anchor_offset) < 64:
                print(f"[!] 发现 ADR 引用在: {hex(addr)} -> 指向 {hex(target)}")
                found_refs.append(addr)

        # --- 检查 2: LDR (Literal) 指令 ---
        # 00011000 ... (LDR Xd, label)
        elif (insn_val & 0xFF000000) == 0x58000000:
            imm19 = (insn_val >> 5) & 0x7FFFF
            offset = imm19 << 2
            # Sign extend
            if offset & 0x100000: offset -= 0x200000
            
            target = addr + offset
            # 检查目标地址内存里存放的是不是 anchor_offset
            # LDR 加载的是一个地址值，这个地址值指向字符串
            if 0 <= target < len(code) - 8:
                # 读取内存里的值
                ptr_val = struct.unpack('<Q', code[target:target+8])[0]
                # U-Boot 会重定位，但在静态文件里，它可能是一个相对小的偏移，或者绝对地址
                # 这是一个难点，如果 Base 不为 0。
                # 但我们可以试着检查 ptr_val 是否等于 anchor_offset (假设 Base=0)
                if abs(ptr_val - anchor_offset) < 64:
                    print(f"[!] 发现 LDR 引用在: {hex(addr)} -> 加载值 {hex(ptr_val)}")
                    found_refs.append(addr)

    # 3. 打印关键代码段
    if found_refs:
        print("\n" + "="*80)
        print("!!! 捕捉到关键嫌疑代码 !!!")
        print("请把下面这些指令完整发给我！我们要找的破解点就在这里面！")
        print("="*80)
        
        # 我们取第一个发现的引用点，往上倒推 200 字节
        # 因为 Key Check 肯定在 Detect 之前执行
        ref = found_refs[0]
        start = max(0, ref - 256)
        end = min(len(code), ref + 64)
        
        snippet = code[start:end]
        
        print(f"{'Addr':<10} {'Machine Code':<24} {'Assembly'}")
        print("-" * 60)
        
        for insn in md.disasm(snippet, start):
            # 标记引用点
            marker = " <=== 标准检测逻辑" if insn.address == ref else ""
            
            # 简单着色: 这里的 B.NE, TBZ 等跳转指令是重点
            if insn.mnemonic.startswith('b') or insn.mnemonic.startswith('c') or insn.mnemonic.startswith('t'):
                 marker += " [Check?]"
            
            bytes_str = ' '.join([f'{b:02x}' for b in insn.bytes])
            print(f"{hex(insn.address):<10} {bytes_str:<24} {insn.mnemonic:<10} {insn.op_str:<20}{marker}")
    else:
        print("[-] 依然没找到直接引用... 厂家可能用了非常复杂的代码混淆。")

if __name__ == "__main__":
    scan_firmware_v2()
