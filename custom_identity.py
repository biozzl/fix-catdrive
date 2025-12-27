import struct
import binascii
import os

def create_perfect_firmware_v6():
    # 必须用回这个名字，配合你的 Action
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_perfect_final.bin'
    
    # --- 定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    # 核心修正：回到 4KB 校验
    # U-Boot 读取 Env 时只校验这 4KB
    # 但擦除时会擦 64KB (这就是为什么不能 saveenv)
    ENV_OFFSET = 0xD0000
    ENV_CALC_SIZE = 0x1000  # 4KB
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成 V6 最终版 (4KB CRC Fix + 正确文件名)...")

    # ==============================
    # 1. 身份信息 (Vendor)
    # ==============================
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

    # ==============================
    # 2. 环境变量 CRC (4KB 模式)
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
    
    # 关键：只填充到 4KB 边界 (减去4字节CRC)
    # 这样绝对不会覆盖 0xD1000 处的 DTB
    env_block = env_payload.ljust(ENV_CALC_SIZE - 4, b'\x00')
    
    # 计算 CRC (只针对这 4KB)
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    
    # 写入 Flash 对应位置
    final_env = struct.pack('<I', crc) + env_block
    data[ENV_OFFSET : ENV_OFFSET + ENV_CALC_SIZE] = final_env
    
    print(f"  [CRC Fix] 已应用 4KB 范围校验 (CRC: {hex(crc)})")
    print("  [Safety]  DTB 区域未被触碰，结构安全。")

    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！{output_file} 已生成。")
    print("请直接运行 Action 并刷入此文件。")

if __name__ == "__main__":
    create_perfect_firmware_v6()
