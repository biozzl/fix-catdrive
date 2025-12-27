import struct
import binascii
import os

def create_perfect_firmware_v8():
    # ！！！文件名已修改，防止混淆！！！
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_v8_final.bin'
    
    # --- 定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    # 核心逻辑：4KB 标准模式 (这是唯一符合物理定律的解)
    ENV_OFFSET = 0xD0000
    ENV_CALC_SIZE = 0x1000  # 4KB
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成 V8 (4KB Standard)...")

    # 1. 身份信息 (Vendor)
    vendor_offset = 0x7EB000
    mac_bytes = bytes.fromhex(NEW_MAC_STR.replace(':', ''))
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    data[vendor_offset + 6] = sum(mac_bytes) & 0xFF
    
    chk_sum = sum(ord(c) for c in NEW_SN_STR)
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    target_idx = vendor_offset + 0x20
    data[target_idx : target_idx + 128] = b'\x00' * 128
    data[target_idx : target_idx + len(vendor_str)] = vendor_str.encode('ascii')

    # 2. 环境变量 (4KB Payload)
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
        'ethaddr': NEW_MAC_STR,
        'bootdelay': '3' # V8 签名认证
    }

    # 构建 Payload
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k.encode('ascii') + b'=' + v.encode('ascii') + b'\0'
    env_payload += b'\0'
    
    # 填充到 4KB - 4
    env_block = env_payload.ljust(ENV_CALC_SIZE - 4, b'\x00')
    
    # 计算 CRC (仅 4KB)
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    
    # 写入
    final_env = struct.pack('<I', crc) + env_block
    data[ENV_OFFSET : ENV_OFFSET + ENV_CALC_SIZE] = final_env
    
    print(f"  [CRC Fix] 4KB CRC: {hex(crc)}")

    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！{output_file} 已生成。")

if __name__ == "__main__":
    create_perfect_firmware_v8()
