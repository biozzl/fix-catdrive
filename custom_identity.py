import struct
import binascii
import os

def create_perfect_firmware_v3():
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_perfect_final.bin'
    
    # --- 你的定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    # 扇区定义
    ENV_OFFSET = 0xD0000
    ENV_SIZE = 0x10000   # 64KB
    DTB_OFFSET = 0xD1000 # DTB 实际位置
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成 V3 完美版固件 (In-Place CRC Fix)...")

    # ==============================
    # 1. Vendor 分区修复 (MAC Checksum + SN)
    # ==============================
    vendor_offset = 0x7EB000
    
    # MAC & Checksum
    mac_bytes = bytes.fromhex(NEW_MAC_STR.replace(':', ''))
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    mac_sum = sum(mac_bytes)
    data[vendor_offset + 6] = mac_sum & 0xFF # 写入 MAC 校验位
    
    # SN & Checksum
    chk_sum = sum(ord(c) for c in NEW_SN_STR)
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    target_idx = vendor_offset + 0x20
    # 清理并写入
    data[target_idx : target_idx + 128] = b'\x00' * 128
    data[target_idx : target_idx + len(vendor_str)] = vendor_str.encode('ascii')
    
    print("  [Identity] MAC、MAC校验位、SN、SN校验位 已全部修正。")

    # ==============================
    # 2. 环境变量 CRC 完美修复
    # ==============================
    # 目标：构建 bootcmd，并将其放入 D0000。
    # 然后计算 D0000-E0000 整个 64KB 的 CRC，包括里面的 DTB(D1000) 和 Kernel(D5000)
    
    boot_cmd_str = (
        'sf probe; '
        'sf read 0x1000000 0x0D5000 0x306000; ' # 读内核
        'lzmadec 0x1000000 0x2000000; '         # 解压
        'sf read 0x3000000 0x3DB000 0x410000; ' # 读 Ramdisk
        'sf read 0x1000000 0xD1000 0x4000; '    # 读 DTB
        'booti 0x2000000 0x3000000 0x1000000'   # 启动
    )
    
    # 注意：这里我们不需要 ethaddr，因为系统会优先读 Vendor 分区的 MAC
    # 如果为了保险，可以加上，但必须确保不超过 D1000 的空间
    env_dict = {
        'bootcmd': boot_cmd_str,
        'bootargs': 'console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
        'ethaddr': NEW_MAC_STR
    }

    # 1. 生成纯净的 Env Payload
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k.encode('ascii') + b'=' + v.encode('ascii') + b'\0'
    env_payload += b'\0' # 结束符
    
    # 检查大小
    print(f"  [Env Size] 环境变量大小: {len(env_payload)} 字节")
    if len(env_payload) > (DTB_OFFSET - ENV_OFFSET - 4):
        print("  [Error] 环境变量太多了，撞到了 DTB！请删减内容。")
        return

    # 2. 提取整个 64KB 扇区数据 (从 D0000 到 E0000)
    # 这里面包含了 DTB 和 Kernel 头部，我们不能丢掉它们！
    sector_data = data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE]
    
    # 3. 在内存中修改这块数据
    # 清空前 4KB (除了 DTB 之外的区域)，防止旧数据干扰
    # 我们只清空 D0000~D1000 这部分
    safe_zone_len = DTB_OFFSET - ENV_OFFSET
    sector_data[4 : safe_zone_len] = b'\x00' * (safe_zone_len - 4)
    
    # 写入我们的新 Env Payload (跳过前4字节 CRC)
    sector_data[4 : 4 + len(env_payload)] = env_payload
    
    # 4. 计算整个 64KB 的 CRC
    # 此时 sector_data 包含了：[预留CRC] [Env变量] [00填充] [DTB数据...] [Kernel数据...]
    # 这就是 U-Boot 启动时实际读取的内容
    calc_crc = binascii.crc32(sector_data[4:]) & 0xFFFFFFFF
    
    print(f"  [CRC Fix] 计算出的全扇区 CRC: {hex(calc_crc)}")
    
    # 5. 填入 CRC
    struct.pack_into('<I', sector_data, 0, calc_crc)
    
    # 6. 写回总数据
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = sector_data
    
    print("  [Env] 已将修正后的 64KB 数据写回。")

    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！生成最终固件: {output_file}")
    print("该固件通过数学方法欺骗了 U-Boot，使其认为 CRC 校验通过，且不破坏 DTB/Kernel。")
    print("注意：即便如此，请勿在 SSH/TTL 中手动执行 saveenv，那会破坏现有结构。")

if __name__ == "__main__":
    create_perfect_firmware_v3()
