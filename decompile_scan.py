import sys
import struct

# 尝试导入 capstone，如果 Action 环境里安装成功的话
try:
    from capstone import *
    from capstone.arm64 import *
    HAS_CAPSTONE = True
except ImportError:
    print("CRITICAL: Capstone library not found. Please install it.")
    HAS_CAPSTONE = False

def scan_firmware():
    filename = '623.8.1.bin'
    
    with open(filename, 'rb') as f:
        code = f.read()

    # 1. 定位错误字符串
    # 這是 "SF: key fail..." 的 hex 模式
    error_str = b'SF: key fail'
    str_offset = code.find(error_str)
    
    if str_offset == -1:
        print("Error: 找不到错误字符串")
        return

    print(f"[*] 目标字符串 'SF: key fail...' 位于文件偏移: {hex(str_offset)}")

    if not HAS_CAPSTONE:
        return

    # 2. 初始化反汇编引擎 (ARM64 Little Endian)
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.detail = True # 需要详细操作数信息

    print("[*] 正在全文件扫描引用该字符串的代码...")
    
    # 我们扫描代码段 (假设前 1MB 包含代码)
    # 为了速度，我们只解析指令流
    # ARM64 指令是 4 字节对齐
    
    found_refs = []

    # 这里的 0x0 是基地址。U-Boot 通常重定位，但 ADR 指令是相对的，所以我们假设 Base=0 分析相对偏移即可
    # 扫描范围：0 到 字符串出现的位置
    scan_limit = min(len(code), str_offset)
    
    # 这是一个比较耗时的操作，我们以 4KB 为块进行反汇编
    for chunk_start in range(0, scan_limit, 0x1000):
        chunk_end = min(chunk_start + 0x1000, scan_limit)
        chunk_data = code[chunk_start:chunk_end]
        
        for insn in md.disasm(chunk_data, chunk_start):
            # 检查指令是否是 ADR 或 ADRP
            # 我们寻找加载 str_offset 地址的指令
            
            # 逻辑 1: ADR Xd, #offset
            if insn.id == ARM64_INS_ADR:
                # 计算目标地址
                op = insn.operands[1] # 第二个操作数是立即数偏移
                target_addr = op.imm
                
                # 如果指向了我们的字符串 (允许 32 字节误差，可能指向字符串中间或头部)
                if abs(target_addr - str_offset) < 32:
                    print(f"\n[!] 发现直接引用 (ADR) 在偏移: {hex(insn.address)}")
                    print(f"    指令: {insn.mnemonic} {insn.op_str}")
                    found_refs.append(insn.address)

            # 逻辑 2: ADRP + ADD 组合 (这是大范围寻址常用的)
            # 这是一个简化的扫描，因为 ADRP 和 ADD 可能不相邻。
            # 但通常编译器会把它们放在一起。
            elif insn.id == ARM64_INS_ADRP:
                op = insn.operands[1]
                page_base = op.imm
                # 检查这个 Page 是否包含我们的字符串
                if (page_base <= str_offset) and (str_offset < page_base + 0x1000):
                    # 这是一个潜在的引用，记录下来，看后面有没有 ADD
                    pass

    # 3. 深度分析引用点周围的代码
    if found_refs:
        for ref_addr in found_refs:
            analyze_context(code, md, ref_addr)
    else:
        print("[-] 未发现直接 ADR 引用。尝试暴力搜索 BL (调用) 模式...")
        # 如果找不到 ADR，可能是因为代码先把偏移加载到寄存器再跳转
        # 或者我们直接找 "B.NE" (不相等则跳转) 或 "TBZ" (测试位为0跳转) 
        # 这些指令通常在报错代码的前面

def analyze_context(code, md, hit_addr):
    print(f"\n[+] 分析偏移 {hex(hit_addr)} 周围的逻辑 (关键！):")
    
    # 提取命中点前后 128 字节的代码
    start = max(0, hit_addr - 64)
    end = min(len(code), hit_addr + 64)
    snippet = code[start:end]
    
    print("-" * 60)
    print(f"{'Offset':<10} {'Bytes':<20} {'Instruction':<30}")
    print("-" * 60)
    
    for insn in md.disasm(snippet, start):
        bytes_str = ' '.join([f'{b:02x}' for b in insn.bytes])
        marker = "<-- 引用点" if insn.address == hit_addr else ""
        print(f"{hex(insn.address):<10} {bytes_str:<20} {insn.mnemonic:<10} {insn.op_str:<20} {marker}")
    print("-" * 60)
    print("请把上面这段 Log 发给我，重点是引用点上面的 B.NE, B.EQ, CBZ, CBNZ 指令。")

if __name__ == "__main__":
    scan_firmware()
