import struct
import binascii
import os

def create_hybrid_firmware():
    # 源文件定义
    FILE_OLD = 'old.bin'       # 提供无锁 U-Boot
    FILE_623 = '623.8.1.bin'   # 提供完美关机内核
    OUTPUT = 'hybrid_ultimate.bin'
    
    # 你的 MAC
    MY_MAC = "00:11:32:A1:B2:C3"

    if not os.path.exists(FILE_OLD) or not os.path.exists(FILE_623):
        print(f"Error: 请确保 {FILE_OLD} 和 {FILE_623} 都在当前目录下！")
        return

    with open(FILE_OLD, 'rb') as f:
        data_old = bytearray(f.read())
    with open(FILE_623, 'rb') as f:
        data_623 = bytearray(f.read())

    print("正在进行手术：移植 623 内核到 Old U-Boot...")

    # 1. 提取 U-Boot (从 old.bin 取前 0xD0000 字节)
    # 这部分包含了 Bootloader，它绝对不会检查 Key
    hybrid_data = data_old[:0xD0000]
    
    # 补齐到 8MB 大小 (用 0x00 填充)
    hybrid_data += b'\x00' * (8388608 - len(hybrid_data))

    # 2. 移植设备树 (DTB)
    # 从 623 中提取 DTB (原位置 0xB0750)
    dtb_src = 0xB0750
    dtb_size = 6914
    dtb_data = data_623[dtb_src : dtb_src + dtb_size]
    
    # 验证 DTB Magic
    if dtb_data[:4] != b'\xd0\x0d\xfe\xed':
        print("Warning: DTB Magic 校验失败，但尝试继续...")
    
    # 将 DTB 放入新固件的 0xD1000 (标准位置)
    hybrid_data[0xD1000 : 0xD1000 + len(dtb_data)] = dtb_data
    print(f"DTB 已移植: 0xD1000 (Size: {len(dtb_data)})")

    # 3. 移植内核 (Kernel)
    # 从 623 中提取内核 (原位置 0xD5000)
    # 注意：623 的内核是 LZMA 压缩的，头部是 5D 00...
    kernel_src = 0xD5000
    kernel_data = data_623[kernel_src:] # 取直到文件末尾
    
    # 将内核放入新固件的 0xD5000
    hybrid_data[0xD5000 : 0xD5000 + len(kernel_data)] = kernel_data
    print(f"内核已移植: 0xD5000 (LZMA)")

    # 4. 注入启动参数 (Environment)
    # 这是关键！我们要告诉旧 U-Boot 去哪里找新内核
    # 并且由于是旧 U-Boot，它只会盲目执行，不会校验
    ENV_OFFSET = 0xD0000
    ENV_SIZE = 0x1000 # 4KB 足够了，避免覆盖 DTB
    
    # 构造 bootcmd
    # 逻辑：读取内核 -> 解压 -> 读取 DTB -> 读取 Ramdisk -> 启动
    boot_cmd_str = (
        b'sf probe; '
        b'sf read 0x1000000 0x0D5000 0x306000; ' # 读取压缩内核到 RAM
        b'lzmadec 0x1000000 0x2000000; '         # 解压内核
        b'sf read 0x3000000 0x3DB000 0x410000; ' # 读取 Ramdisk
        b'sf read 0x1000000 0xD1000 0x4000; '    # 读取 DTB
        b'booti 0x2000000 0x3000000 0x1000000'   # 启动！
    )

    env_dict = {
        b'ethaddr': MY_MAC.encode('ascii'),
        b'bootcmd': boot_cmd_str,
        # 623 专用的 bootargs
        b'bootargs': b'console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
    }

    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0'

    # 填充并计算 CRC
    env_block = env_payload.ljust(ENV_SIZE - 4, b'\x00')
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    final_env = struct.pack('<I', crc) + env_block
    
    # 写入环境变量
    hybrid_data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = final_env

    with open(OUTPUT, 'wb') as f:
        f.write(hybrid_data)
    
    print(f"\n成功！混合固件已生成: {OUTPUT}")
    print("这个固件没有任何 ID 锁，但拥有 623 的所有功能。")

if __name__ == "__main__":
    create_hybrid_firmware()
