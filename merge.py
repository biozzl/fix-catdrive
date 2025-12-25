import os

def find_header(data, magic_bytes, start_offset=0):
    try:
        return data.index(magic_bytes, start_offset)
    except ValueError:
        return -1

def merge_firmware_v3():
    print(">>> [V3] 修复内核溢出问题 - 开始合成...")
    
    file_uboot = "old.bin"
    file_kernel = "new.bin"
    file_out = "mixed.bin"

    # --- 调整后的布局 ---
    ADDR_DTB      = 0xCC800   # 设备树位置
    ADDR_KERNEL   = 0xD5000   # 内核起始
    # 【重要修改】由于内核有 4MB，我们将 Ramdisk 的起始地址往后移动
    # 0xD5000 + 4.1MB (给内核留够空间) = 0x4F0000
    ADDR_RAMDISK  = 0x500000  
    TOTAL_SIZE    = 0x800000

    with open(file_uboot, "rb") as f_u, open(file_kernel, "rb") as f_k:
        old_data = f_u.read()
        new_data = f_k.read()

    print(f"[*] 提取 U-Boot 区域...")
    uboot_part = old_data[:ADDR_DTB]

    # 提取 DTB
    dtb_offset = find_header(new_data, b'\xd0\x0d\xfe\xed')
    dtb_part = new_data[dtb_offset : dtb_offset + 0x8000]

    # 提取 Kernel 和 Ramdisk
    uimage_magic = b'\x27\x05\x19\x56'
    k_offset = find_header(new_data, uimage_magic, dtb_offset)
    r_offset = find_header(new_data, uimage_magic, k_offset + 0x10000)
    
    kernel_part = new_data[k_offset : r_offset]
    ramdisk_part = new_data[r_offset:]

    print(f"[*] 写入 mixed.bin...")
    with open(file_out, "wb") as f_out:
        f_out.write(uboot_part)
        f_out.seek(ADDR_DTB)
        f_out.write(dtb_part)
        f_out.seek(ADDR_KERNEL)
        f_out.write(kernel_part)
        f_out.seek(ADDR_RAMDISK) # 写入到新的安全位置
        f_out.write(ramdisk_part)
        
        # 补齐 8MB
        curr = f_out.tell()
        if curr < TOTAL_SIZE:
            f_out.write(b'\xff' * (TOTAL_SIZE - curr))

    print(f"\n>>> 成功！内核和 Ramdisk 已完全分离，不再重叠。")

if __name__ == "__main__":
    merge_firmware_v3()
