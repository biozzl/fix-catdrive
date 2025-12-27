import struct
import binascii
import os

def create_perfect_firmware_v4():
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_perfect_final_v4.bin'
    
    # --- 你的定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    # 关键参数修正：只计算前 4KB 的 CRC
    ENV_OFFSET = 0xD0000
    ENV_CALC_SIZE = 0x1000  # 4KB (U-Boot 实际校验的大小)
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成 V4 终极完美版固件 (4KB CRC Fix)...")

    # ==============================
    # 1. Identity 修复 (MAC/SN)
    # ==============================
    vendor_offset = 0x7EB000
    
    # MAC & Checksum
    mac_bytes = bytes.fromhex(NEW_MAC_STR.replace(':', ''))
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    mac_sum = sum(mac_bytes)
    data[vendor_offset + 6] = mac_sum & 0xFF
    
    # SN & Checksum
    chk_sum = sum(ord(c) for c in NEW_SN_STR)
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    # 写入到 +0x20
    target_idx = vendor_offset + 0x20
    data[target_idx : target_idx + 128] = b'\x00' * 128
    data[target_idx : target_idx + len(vendor_str)] = vendor_str.encode('ascii')
    
    print("  [Identity] 身份信息修正完毕。")

    # ==============================
    # 2. 环境变量 CRC 精确修复
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

    # 构建 Payload
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k.encode('ascii') + b'=' + v.encode('ascii') + b'\0'
    env_payload += b'\0'
    
    # 填充到 4KB (减去4字节CRC头)
    # 注意：这里我们只处理前 4KB 数据
    env_block = env_payload.ljust(ENV_CALC_SIZE - 4, b'\x00')
    
    # 计算 CRC (只针对这 4KB 数据)
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    
    # 写入
    final_env_4k = struct.pack('<I', crc) + env_block
    data[ENV_OFFSET : ENV_OFFSET + ENV_CALC_SIZE] = final_env_4k
    
    print(f"  [CRC Fix] 已修正为 4KB 范围校验 (CRC: {hex(crc)})")
    print("  [Info] DTB 依然位于 0xD1000 (安全避开环境变量区)")

    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！生成最终固件: {output_file}")
    print("这个版本将彻底消除 Warning - bad CRC。")

if __name__ == "__main__":
    create_perfect_firmware_v4()
