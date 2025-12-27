import struct
import binascii
import os

def create_perfect_firmware_v7():
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_perfect_final.bin' # 保持文件名不变方便Action
    
    # --- 定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    # 逆向结论：ENV_SIZE = 64KB (0x10000)
    ENV_OFFSET = 0xD0000
    ENV_SIZE   = 0x10000 
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成 V7 (64KB Redundant Mode)...")

    # 1. 身份信息 (Vendor) - 保持不变
    vendor_offset = 0x7EB000
    mac_bytes = bytes.fromhex(NEW_MAC_STR.replace(':', ''))
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    data[vendor_offset + 6] = sum(mac_bytes) & 0xFF
    
    chk_sum = sum(ord(c) for c in NEW_SN_STR)
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    target_idx = vendor_offset + 0x20
    data[target_idx : target_idx + 128] = b'\x00' * 128
    data[target_idx : target_idx + len(vendor_str)] = vendor_str.encode('ascii')
    
    print("  [Identity] 身份信息已修正。")

    # 2. 环境变量 (Redundant 格式修复)
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

    # 构建 Payload
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k.encode('ascii') + b'=' + v.encode('ascii') + b'\0'
    env_payload += b'\0'
    
    # 提取 64KB 扇区数据
    # 注意：我们必须包含 DTB 和 KernelHead
    sector_data = data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE]
    
    # --- 关键修正：Redundant 格式 ---
    # Byte 0-3: CRC
    # Byte 4  : Flag (0x01 = Active)
    # Byte 5+ : Env Data
    
    # 1. 写入 Flag
    sector_data[4] = 0x01 
    
    # 2. 写入数据 (从 Byte 5 开始)
    # 计算可用空间：到 DTB (0x1000) 之前
    # 0x1000 - 5 = 4091 bytes
    if len(env_payload) > 4091:
        print("Error: Env too large!")
        return
        
    gap_size = 0x1000 - 5
    # 清空 Flag 到 DTB 之间的区域
    sector_data[5 : 5 + gap_size] = b'\x00' * gap_size
    # 写入 Payload
    sector_data[5 : 5 + len(env_payload)] = env_payload
    
    # 3. 计算 CRC
    # 范围：从 Flag (Byte 4) 开始到结束 (包括 DTB/KernelHead)
    # 长度：64KB - 4
    calc_crc = binascii.crc32(sector_data[4:]) & 0xFFFFFFFF
    
    # 4. 写入 CRC
    struct.pack_into('<I', sector_data, 0, calc_crc)
    
    # 5. 回写
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = sector_data
    
    print(f"  [CRC Fix] Redundant Mode (Flag=0x01). CRC: {hex(calc_crc)}")
    print("  [Info] 包含了 Flag + Data + DTB + KernelHead 的总校验。")

    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！{output_file} 已生成。")

if __name__ == "__main__":
    create_perfect_firmware_v7()
