import struct
import binascii
import os

def create_perfect_firmware_v5():
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_perfect_final_v5.bin'
    
    # --- 定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    # 关键修正：必须是 64KB，因为 U-Boot 就是读这么多
    ENV_OFFSET = 0xD0000
    ENV_SIZE   = 0x10000  # 64KB
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成 V5 共存版固件 (64KB Full CRC)...")

    # ==============================
    # 1. 身份信息修复 (Vendor)
    # ==============================
    vendor_offset = 0x7EB000
    mac_bytes = bytes.fromhex(NEW_MAC_STR.replace(':', ''))
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    data[vendor_offset + 6] = sum(mac_bytes) & 0xFF # 校验位
    
    chk_sum = sum(ord(c) for c in NEW_SN_STR)
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    target_idx = vendor_offset + 0x20
    data[target_idx : target_idx + 128] = b'\x00' * 128
    data[target_idx : target_idx + len(vendor_str)] = vendor_str.encode('ascii')
    
    print("  [Identity] MAC & SN 已修正。")

    # ==============================
    # 2. 环境变量 CRC 终极修复
    # ==============================
    boot_cmd_str = (
        'sf probe; '
        'sf read 0x1000000 0x0D5000 0x306000; ' 
        'lzmadec 0x1000000 0x2000000; '         
        'sf read 0x3000000 0x3DB000 0x410000; ' 
        'sf read 0x1000000 0xD1000 0x4000; '    
        'booti 0x2000000 0x3000000 0x1000000'   
    )
    
    env_dict = {
        'bootcmd': boot_cmd_str,
        'bootargs': 'console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
        'ethaddr': NEW_MAC_STR
    }

    # 1. 构建新的参数块
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k.encode('ascii') + b'=' + v.encode('ascii') + b'\0'
    env_payload += b'\0' # 结束符
    
    # 2. 读取原始的 64KB 扇区数据 (这是关键！)
    # 我们要把这里的 DTB (0xD1000) 和 Kernel头 (0xD5000) 也读进来一起算 CRC
    sector_data = data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE]
    
    # 3. 覆盖前面的部分 (只覆盖我们参数的长度)
    # 注意：我们必须保证 env_payload 没有长到覆盖 DTB (4KB)
    if len(env_payload) > 4090:
        print("Error: 环境变量太长了，会覆盖 DTB！")
        return
        
    # 把我们的参数写到头部 (跳过前4字节 CRC位)
    # 并把参数后面到 DTB 之间的空隙填 0，确保干净
    gap_size = 0x1000 - 4 # 到 DTB 之前的空间
    sector_data[4 : 4 + gap_size] = b'\x00' * gap_size
    sector_data[4 : 4 + len(env_payload)] = env_payload
    
    # 4. 计算整个 64KB 的 CRC (包含 Payload + 00填充 + DTB + Kernel头)
    calc_crc = binascii.crc32(sector_data[4:]) & 0xFFFFFFFF
    
    print(f"  [CRC Fix] 计算 64KB 全扇区 CRC: {hex(calc_crc)}")
    print("            (包含了 DTB 和 Kernel 头部，U-Boot 读取时将完全匹配)")
    
    # 5. 写入 CRC 并回填
    struct.pack_into('<I', sector_data, 0, calc_crc)
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = sector_data

    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！生成 V5 固件: {output_file}")

if __name__ == "__main__":
    create_perfect_firmware_v5()
