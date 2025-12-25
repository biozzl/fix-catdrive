import os
import struct

def find_header(data, magic_bytes, start_offset=0):
    """在二进制数据中搜索特定的头 (比如 d00dfeed)"""
    try:
        # 查找 magic bytes 的位置
        offset = data.index(magic_bytes, start_offset)
        return offset
    except ValueError:
        return -1

def merge_firmware_v2():
    print(">>> [V2] 开始智能固件合成...")
    
    file_uboot = "old.bin"   # 原厂无锁 U-Boot
    file_kernel = "new.bin"  # 猫盘专用全量固件
    file_out = "mixed.bin"

    # 标准 DS120j 内存布局 (我们将把数据强制搬运到这些位置)
    ADDR_DTB     = 0xCC800
    ADDR_KERNEL  = 0xD5000
    ADDR_RAMDISK = 0x3DB000
    TOTAL_SIZE   = 0x800000  # 8MB

    if not (os.path.exists(file_uboot) and os.path.exists(file_kernel)):
        print("错误: 找不到 old.bin 或 new.bin")
        return

    with open(file_uboot, "rb") as f_u, open(file_kernel, "rb") as f_k:
        old_data = f_u.read()
        new_data = f_k.read()

    # 1. 提取无锁 U-Boot (保留 old.bin 头部到 0xCC800)
    print(f"[*] 提取原厂 U-Boot (0 - 0x{ADDR_DTB:X})...")
    uboot_part = old_data[:ADDR_DTB]

    # 2. 自动搜索并提取 DTB (设备树)
    print("[*] 正在扫描 new.bin 寻找设备树 (DTB)...")
    # DTB Magic: d0 0d fe ed
    dtb_magic = b'\xd0\x0d\xfe\xed'
    dtb_offset = find_header(new_data, dtb_magic)
    
    if dtb_offset == -1:
        print("!!! 严重错误: 在 new.bin 里没找到设备树头 (d00dfeed)！")
        return
    
    print(f"    -> 找到了！DTB 位于 new.bin 的 0x{dtb_offset:X}")
    
    # 提取 DTB (假设最大 30KB，足够了)
    dtb_part = new_data[dtb_offset : dtb_offset + 0x8000]

    # 3. 自动搜索并提取 Kernel (uImage)
    print("[*] 正在扫描 new.bin 寻找内核 (Kernel)...")
    # uImage Magic: 27 05 19 56
    uimage_magic = b'\x27\x05\x19\x56'
    
    # 内核通常在 DTB 后面，所以从 DTB 之后开始搜
    kernel_offset = find_header(new_data, uimage_magic, start_offset=dtb_offset + 0x100)
    if kernel_offset == -1:
        # 如果找不到，尝试从头搜 (防止布局不同)
        kernel_offset = find_header(new_data, uimage_magic)

    if kernel_offset == -1:
        print("!!! 严重错误: 没找到内核头 (27051956)！")
        return

    print(f"    -> 找到了！Kernel 位于 new.bin 的 0x{kernel_offset:X}")
    
    # 提取 Kernel (截取到下一个 uImage 也就是 Ramdisk 之前)
    # 我们先搜下一个魔数作为终点
    ramdisk_offset = find_header(new_data, uimage_magic, start_offset=kernel_offset + 0x10000)
    
    if ramdisk_offset == -1:
         print("!!! 警告: 没找到 Ramdisk，可能内核后面就是结尾")
         kernel_part = new_data[kernel_offset : kernel_offset + 0x400000] # 盲取 4MB
         ramdisk_part = b''
    else:
         print(f"    -> 找到了！Ramdisk 位于 new.bin 的 0x{ramdisk_offset:X}")
         kernel_part = new_data[kernel_offset : ramdisk_offset]
         ramdisk_part = new_data[ramdisk_offset:]

    # 4. 组装 Frankenstein (缝合怪)
    print("[*] 正在组装新固件 (重映射到 DS120j 标准地址)...")
    
    with open(file_out, "wb") as f_out:
        # A. 写入 U-Boot (0x0)
        f_out.write(uboot_part)
        
        # B. 填充直到 0xCC800 (如果有空隙)
        if f_out.tell() < ADDR_DTB:
            f_out.write(b'\xff' * (ADDR_DTB - f_out.tell()))
        f_out.seek(ADDR_DTB)
        
        # C. 写入 DTB (0xCC800)
        f_out.write(dtb_part)
        
        # D. 写入 Kernel (0xD5000)
        curr = f_out.tell()
        if curr > ADDR_KERNEL:
            print(f"!!! 警告: DTB 太大，覆盖了内核区域！当前: 0x{curr:X}")
        else:
            f_out.seek(ADDR_KERNEL)
        f_out.write(kernel_part)

        # E. 写入 Ramdisk (0x3DB000)
        curr = f_out.tell()
        if curr > ADDR_RAMDISK:
             print(f"!!! 警告: 内核太大 ({len(kernel_part)/1024/1024:.2f}MB)，覆盖了 Ramdisk 区域！")
             print("    系统可能无法启动，需要调整地址。")
        else:
            f_out.seek(ADDR_RAMDISK)
        f_out.write(ramdisk_part)
        
        # F. 补齐到 8MB
        curr = f_out.tell()
        if curr < TOTAL_SIZE:
            f_out.write(b'\xff' * (TOTAL_SIZE - curr))

    print(f"\n>>> 成功！已生成: {file_out} (大小: {os.path.getsize(file_out)} 字节)")
    print(f">>> 提示: 该固件已将 DTB 强制移回 0xCC800，可以直接启动！")

if __name__ == "__main__":
    merge_firmware_v2()
